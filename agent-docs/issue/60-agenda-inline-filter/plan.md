# Plan: Issue #60 — `agenda` renders item text without the inline filter

## Goal

Make `agenda` treat its text like every other text-bearing block: `item.title`, `item.discussion`, `item.decision` and the `subItems[]` strings must go through the inline-markup filter so `**bold**`, `*italic*`, backticks, locale-aware smart quotes, and the change markers `{+…+}` / `[-…-]` render instead of appearing as literal characters in the PDF. Verified before planning (tex-level, no xelatex): today `**justerare**` lands verbatim inside `\textbf{…}`, `[-a-] {+b+}` comes out as `[-a-] \{+b+\}`, and a `\n` in `decision` passes through as a raw newline — on the block engine and on the protokoll recipe alike.

The fix covers both surfaces at once because the rendering lives in one shared macro, exactly like #47 (`description_list`, PR #58).

## Approach

Follow the #47 pattern. `render_agenda` in `klartex/templates/_block_macros.tex.jinja` (line 46 onward) is the only place agenda text is emitted; `_block_engine.tex.jinja:320` (block `agenda`) and `_recipe_base.tex.jinja:82` (recipe component `agenda`, used by protokoll with `numberingStyle: decimal`) both call it. Applying the filters inside the macro fixes both callers.

The `with context` import that #47 added to both templates is already in place, so the `pass_context` filters see the document `lang` inside the macro — nothing to do there, and the existing `TestRecipeLanguageReachesInlineFilters` / `test_english_lang_reaches_the_imported_macro` tests keep locking it.

**Filter choice per field.** Unlike `description_list`, no agenda field sits in a tabular cell: every one is emitted in paragraph mode (`\item \textbf{…}` inside the `dagordning` enumerate for `section` style; hanging-indent `\noindent … \par` groups for `decimal` style), where `\\` is a legal line break. So the plain `| inline` filter (newline → `\\`) is the right choice for all four fields, consistent with `render_heading` (`\VAR{text | inline}`) and the `text` block. Concretely:

| Field | Emitted as | Filter | Newline behaviour |
|---|---|---|---|
| `item.title` (section) | `\punkt{…}` → `\item \textbf{#1}` | `inline` | `\\` inside the item's bold first line |
| `item.title` (decimal) | `\textbf{\VAR{…}}\par` in a hangindent paragraph | `inline` | `\\` — continuation lines get the hanging indent |
| `item.discussion` | `\noindent \VAR{…}` / `…\par` | `inline` | `\\` paragraph line break |
| `item.decision` | `\noindent \textbf{decLabel} \VAR{…}` | `inline` | `\\` paragraph line break |
| `subItems[]` (decimal only) | `\makebox[…]{…}\VAR{sub}\par` | `inline` | `\\` with hanging indent |

*Provenance: agent judgment* — the issue leaves "how newlines should behave" open per field; `inline` everywhere is my pick because it matches the heading/text precedent and every emission site is paragraph mode. An `inline_flat` title (newline → space) would be the alternative if single-line titles are wanted; flag in the PR body as open to challenge.

**`decLabel`.** The decision label (`decisionLabel`, default `"Beslut:"`) is also emitted raw. Give it `| inline_flat` for parity with `description_list` labels (#47): single-line, newline → space. Its provenance differs per surface, and that matters for what the filter sees: on the block engine `decisionLabel` is user data that `render()` has already escaped, so the filter behaves exactly as for item text; on the recipe path it comes from `comp.options` in `recipe.yaml` (`_recipe_base.tex.jinja:82`) — trusted, repo-authored configuration that is *not* escaped, so an added marker written there would arrive with raw braces and stay literal (the `\{+…+\}` regex expects escaped braces). The shipped `"Beslut:"` is inert either way. *Provenance: agent judgment* — one token, removes the last unfiltered text path in the macro; flag in the PR body.

**Item text is pre-escaped on both paths**: `render()` escapes before Jinja, and `prepare_recipe_context` receives `escape_data(data)`, so `agenda_items` reach the filter the same way block items do. Marker macros are safe in these contexts: `\kxremoved` (ulem `\sout` inside `\textcolor`) and `\kxadded` sit in non-moving arguments (`\textbf` inside `\item`, plain paragraphs), and a title starting with `[-…-]` cannot be mistaken for an `\item` optional argument because `\punkt` places `\textbf` before it. `agenda` nests no blocks and has no raw-LaTeX field, so `_restore_block_types` is untouched.

**Tex-level assertion shape.** `_render_tex` / `_render_recipe_tex` return Jinja output, not expanded LaTeX. The decimal branch writes `\textbf{\VAR{item.title}}` itself, so a bold title renders as `\textbf{\textbf{justerare}}` there; the section branch writes `\punkt{…}` and the outer `\textbf` lives inside `\punkt`'s definition in `klartex-agenda.sty:30`, so the tex shows `\punkt{\textbf{justerare}}`. Tests assert the branch-specific form (a bare `\textbf{justerare}` substring would pass in the decimal branch even without the fix — the #47 lesson).

**Not changed, noted for the PR body:**
- The `section` branch ignores `subItems` entirely — pre-existing and by design per the block schema ("Only meaningful with `numberingStyle: "decimal"`").
- `klartex/templates/protokoll/schema.json` does not set `additionalProperties: false` on `agenda_items[]`, so a `subItems` array passes validation and, because protokoll renders `decimal`, would actually render — but the recipe schema does not advertise it. Whether protokoll should document or reject `subItems` is a product question outside this fix; leave as is and mention it in the PR body as a follow-up candidate.
- Other unfiltered text sites in `_block_engine.tex.jinja` remain (`name_roster`'s `title`, `name`, `role`, `note` at line 324; title-page and signatures header fields; `latex.source` is raw by contract). Separate blocks, candidates for their own issue.

## Steps

Red first: the tests go in before the macro changes, so each new assertion is seen failing against the current output.

1. **`tests/test_block_engine.py`** — new class `TestAgendaInlineMarkup` next to `TestDescriptionListInlineMarkup` (line 1563), using the module-level `_render_tex` helper (line 1067), no xelatex needed:
   - one test parametrized over `numberingStyle in ("section", "decimal")` that builds a single agenda item carrying markup in every field and checks each emission site of that branch: `**bold**` title → `\punkt{\textbf{justerare}}` (section) / `\textbf{\textbf{justerare}}` (decimal) and no literal `**`; change markers in `discussion` → `\kxremoved{…}` / `\kxadded{…}` with no `\{+` / `[-` left; `*italic*` and backticks in `decision` → `\textit{…}` / `\texttt{…}`; `\n` in `discussion` → `Rad 1 \\ Rad 2` (paragraph-break semantics, like `test_text_block_newline_still_paragraph_break`); `decisionLabel: "Beslut\nfattat:"` → `Beslut fattat:` inside `\textbf{…}`;
   - a decimal-only test for markers/bold in a `subItems` entry → the macro appears after the `\makebox[1.0cm][l]{\textbf{1.1.}}` prefix;
   - `lang: "en"` + `"quoted"` in `title` and `discussion` → `“…”` and not `”…”` — locks that the agenda sites use the `pass_context` filters through the `with context` import — plus a Swedish-default control (`”…”`);
   - one `@pytest.mark.skipif(not HAS_XELATEX)` compile test with a markup-heavy agenda in each numbering style (bold/marker title, marker discussion, multi-line decision, code sub-item) → `%PDF-`.
   Add one focused assertion to `TestChangeMarking` (`test_markers_work_in_agenda`, in the style of `test_markers_work_in_description_list`) so the change-marking suite lists the block; the parametrized test carries the comprehensive coverage.
2. **`tests/test_renderer.py`** — recipe path via the existing `_render_recipe_tex("protokoll", data)` helper (line 414), next to `test_recipe_metadata_passes_through_inline_markup`: set `agenda_items[0].title = "Mötets **öppnande**"`, `agenda_items[0].discussion = "[-Kort-] {+Lång+} diskussion"`, `agenda_items[1].decision = 'Valdes "enhälligt"'` and assert `\textbf{\textbf{öppnande}}` (protokoll is decimal), `\kxremoved{Kort}`, `\kxadded{Lång}`, `”enhälligt”` (sv recipe), no `**` — proves the protokoll surface gets the filter.
3. Run the new tests by node ID and confirm they fail (`pytest tests/test_block_engine.py::TestAgendaInlineMarkup tests/test_block_engine.py::TestChangeMarking::test_markers_work_in_agenda tests/test_renderer.py -k agenda`).
4. **`klartex/templates/_block_macros.tex.jinja`** — in `render_agenda`, apply the filters at every emission site in both branches:
   - section: `\punkt{\VAR{item.title | inline}}`, `\noindent \VAR{item.discussion | inline}`, `\noindent \textbf{\VAR{decLabel | inline_flat}} \VAR{item.decision | inline}`
   - decimal: `\textbf{\VAR{item.title | inline}}\par`, `\noindent \VAR{item.discussion | inline}\par`, `\noindent \textbf{\VAR{decLabel | inline_flat}} \VAR{item.decision | inline}\par`, `\makebox[1.0cm][l]{…}\VAR{sub | inline}\par`
   Update the macro's header comment (`_block_macros.tex.jinja:43-45`) to say the fields pass through inline markup — technical fact, no rationale. Re-run step 3's node IDs: green.
5. **`klartex/schemas/blocks/agenda.schema.json`** — document inline-markup support for agent introspection (`klartex schema _block`), mirroring `description_list.schema.json`: append a sentence to the top-level `description` ("Item text passes through inline markup."), and give `title`, `discussion`, `decision` and `subItems.items` Swedish field descriptions in the same wording as `description_list`'s `value` ("Inline-markup gäller: **fet**, *kursiv*, `kod`, "citat", samt ändringsmarkering {+tillagd text+} / [-struken text-]. Radbrytning blir radbrytning."), and `decisionLabel` the label wording ("Radbrytning blir mellanslag"). No `$id` bump — no structural change, same call as #47. Keep the existing English sentences in the fields that have them (`"Agenda item title"`) and append, matching the file's mixed style.
6. **`klartex/templates/protokoll/schema.json`** — the recipe surface's public contract: add the same Swedish inline-markup `description` to `agenda_items[].title`, `discussion` and `decision` (they have none today). Do not add `subItems` and do not tighten `additionalProperties` — see the open question above.
7. **`tests/fixtures/block_dagordning.json`** — put inline markup into the canonical agenda fixture so it demonstrates and compile-tests the behaviour, e.g. `"discussion": "Kassören presenterade den ekonomiska rapporten för perioden januari--februari 2026. Resultatet var **positivt**."` and a change-marked decision such as `"Styrelsen godkände rapporten [-med reservation-] {+utan anmärkning+}."`. Leave `tests/fixtures/protokoll.json` untouched as a scope choice — it is the baseline for several escaping tests and the recipe-path coverage comes from step 2.
8. Full `pytest` with xelatex on PATH — `test_agenda_fixture`, `test_render_pdf[protokoll]` and the kallelse/spacing fixtures exercise the compiled output alongside the new compile test.

## Risks

- **Behaviour change for existing payloads.** Producers already sending literal `**`, `*`, backticks, straight `"` or `{+…+}` / `[-…-]` in agenda item text — block engine or protokoll `agenda_items` — will see them interpreted; straight quotes become typographic quotes in every title/discussion/decision. This is the intended alignment (the issue calls it out explicitly), but it belongs in the next release's CHANGELOG `Fixes` entry, written at release time per the repo's release flow, not in this branch.
- **Italic false positives in titles.** `_ITALIC_RE` converts a single `*…*` pair; agenda titles rarely contain asterisks, and the `text`/`heading` blocks already carry the same grammar. Accepted, same as everywhere else.
- **Newlines in titles.** With `inline`, a `\n` in a title becomes `\\` inside `\textbf` in an `\item` or hangindent paragraph — valid LaTeX, continuation lines take the list/hanging indent. If a single-line title is preferred, swap to `inline_flat` for `title` only (see the open judgment above). Covered by the compile test.
- **`decLabel` filtering** is a small widening beyond the issue's four fields; it is inert for the shipped recipe (`"Beslut:"`) and for the default. If challenged, drop the token — the rest of the plan does not depend on it.
- **Fixture change** to `block_dagordning.json` alters the canonical example output; `test_agenda_fixture` only asserts `%PDF-`, and no text-layer test reads this fixture (`tests/test_pdf_text_layer.py` builds its own payloads).

## Test Plan

- New tex-level assertions in `tests/test_block_engine.py` (`TestAgendaInlineMarkup` parametrized over both numbering styles, plus `TestChangeMarking::test_markers_work_in_agenda`): branch-specific bold-title form (`\punkt{\textbf{…}}` / `\textbf{\textbf{…}}`), italic/code in decision, markers in discussion and sub-items, `\n` → `\\` in discussion, `decisionLabel` newline → space, `lang: "en"` English quotes and `sv` default quotes — pure source-level, runnable without xelatex by node ID (note `-k "not xelatex"` filters names, not `skipif` markers; select node IDs for the fast pass).
- New recipe-path test in `tests/test_renderer.py` through `_render_recipe_tex("protokoll", …)` asserting bold/markers/quotes in `agenda_items` title, discussion and decision.
- Each new test seen failing at step 3 and passing after step 4 (red-first, as the issue requests).
- xelatex compile tests: the new markup-heavy agenda compile test (both styles), the updated `tests/fixtures/block_dagordning.json` via `test_agenda_fixture`, and `test_render_pdf[protokoll]`.
- Full `pytest` green locally with xelatex on PATH (baseline after PR #59: 0 skipped); CI fails if any xelatex test is skipped, so no `pytest.skip` shortcuts.
