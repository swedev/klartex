# Plan: Issue #40 — Change marking — `{+added+}` / `{-removed-}` inline markers and `klartex-changes.sty`

## Goal

Documents (canonical case: stadgeändringar) can show what changed between two versions inside one PDF: added text renders green, removed text renders red with strikethrough. The producer decides what counts as added/removed; klartex only renders the marking. Deliverables:

- A new `klartex/cls/klartex-changes.sty` owning the visual contract via two semantic macros, `\kxadded{…}` and `\kxremoved{…}`.
- Inline markers `{+added text+}` / `{-removed text-}` in `klartex/inline_markup.py`, active in every field that already passes through the `| inline` / `| inline_cell` / `| inline_flat` filters (text, clause, list, table cells, callout, quote, agenda, description_list, …).
- A block-level `revision: "added" | "removed"` attribute on the `text` block, for whole paragraphs that were added or struck (the form the issue calls "likely the more important one" for stadgeändringar).
- A realistic stadgeändring fixture as the canonical example, with the fragility cases (tabular cells, page breaks) exercised early.

Out of scope, per the issue: generic strikethrough markup (`~~text~~`), author/comment metadata, accept/reject workflows. Block-level `revision` on `clause` and `list` is deferred to a follow-up (see Approach).

## Approach

### 1. `klartex-changes.sty` — own the ~15 lines instead of the `changes` package

New `klartex/cls/klartex-changes.sty`, following the repo convention of one `klartex-<component>.sty` per concern:

- `\RequirePackage[normalem]{ulem}` — **correction to the issue premise:** `ulem` is not currently loaded anywhere (only `xcolor` is, in `klartex-base.cls` line 24), so this sty must pull it in itself. The `[normalem]` option is mandatory: without it ulem redefines `\emph`/`\em` to underline document-wide, which would silently change the rendering of every existing document.
- Two colors: `\definecolor{kxaddedcolor}{HTML}{...}` (dark green, e.g. `1A7A3C`) and `\definecolor{kxremovedcolor}{HTML}{...}` (dark red, e.g. `B00020`). Dark enough to stay readable in grayscale print.
- Style hooks + semantic macros:
  - `\newcommand{\kxadded}[1]{\textcolor{kxaddedcolor}{#1}}`
  - `\newcommand{\kxremoved}[1]{\textcolor{kxremovedcolor}{\sout{#1}}}`

  (Exact bodies via redefinable `\kxaddedstyle`/`\kxremovedstyle` hooks so a page template can restyle without touching call sites.) ulem's `\sout` breaks at spaces and explicitly tolerates `\\` inside its argument — which matters because `render_inline` turns literal `\n` into `\\` (or `\newline`) *inside* the marker content.
- **Highlight experiment, time-boxed and conditional:** the issue allows either soul-based green highlight or green text for `\kxadded`, and blesses colored text as the fallback. Implement colored text first as the robust baseline. The `soul` experiment is *conditional on package availability*: `soul.sty` is not part of every minimal TeX installation (and is not guaranteed by `texlive-xetex` alone), so adopting it would add a runtime dependency for every deployment. Only try `\hl` behind the `\kxaddedstyle` hook if `soul` is present in the CI TeX collection, and keep it only if the fragility fixtures (markers in `tabularx` X-cells, an added passage crossing a page break) pass *and* a visual inspection of the rendered pages looks right — "the PDF compiled" is not an acceptance criterion for a visual feature. Otherwise ship colored text and note the decision in the PR body. Baseline-first means the experiment can be dropped at any point without leaving the feature broken.
- **Dependency note:** `ulem.sty` becomes a hard runtime dependency of every render (it ships in all mainstream TeX Live installs, including `texlive-xetex`-based CI images, but verify once in CI before merging; extend the README/CLAUDE.md TeX-install guidance only if verification shows it is not covered).

**Loading:** add `\RequirePackage{klartex-changes}` to `klartex-base.cls`, in the existing component-package loading block (the `\RequirePackage{klartex-…}` run near the end of the class). *Provenance note — agent judgment, open to question:* the issue says "loaded via the component registry", but inline markers are not tied to any block type (they fire in every prose field), and registry-driven sty loading only exists on the recipe path (`recipe.py::prepare_recipe_context` collects `sty_packages`); the block engine gets every sty unconditionally from `klartex-base.cls` anyway. Loading from `klartex-base.cls` covers both paths with one mechanism and has precedent in the registry-less `klartex-numformat.sty` and `klartex-footer.sty`. No `ComponentSpec` entry is added — there is no block schema, so `KNOWN_BLOCK_TYPES` and `klartex blocks` are unaffected either way.

### 2. Inline markers in `inline_markup.py` — match the *escaped* forms

`render_inline` runs **after** `escape_data()`, and `{` / `}` are LaTeX specials: `{+ny lydelse+}` reaches the function as `\{+ny lydelse+\}`. The regexes therefore match the escaped marker shapes:

```python
_ADDED_RE   = re.compile(r"\\\{\+(.+?)\+\\\}", re.DOTALL)   # \{+…+\}  → \kxadded{…}
_REMOVED_RE = re.compile(r"\\\{-(.+?)-\\\}", re.DOTALL)     # \{-…-\}  → \kxremoved{…}
```

The replacement content is already-escaped text, so substituting straight into `\kxadded{\1}` is safe (no unescaped braces can appear inside).

**Pass ordering** in `render_inline` (current order: code-stash → bold → italic → quotes → code-restore → newlines):

1. Code spans are stashed first, as today — a marker inside backticks stays literal.
2. **Change markers run right after the code stash, before bold/italic.** Two reasons: (a) markup *inside* marker content should still render (`{+**viktigt** tillägg+}` → `\kxadded{\textbf{viktigt} tillägg}`), which works because the later bold/italic passes are global and reach inside the substituted `\kxadded{…}`; (b) running bold first would turn `**+x+**` into `\textbf{+x+}` whose `f{+…+}` could not then be recognized (and must not be — the change regex requires the escaped `\{`, which `\textbf{` does not contain, so ordering keeps both directions unambiguous).
3. Quotes and newline handling stay last, unchanged.

**Explicit marker semantics** (documented in the module docstring and locked by unit tests):

- *Mixed nesting* (`{-old {+new+} old-}`) renders nested — the passes are global regexes, so the inner marker converts inside the outer macro's argument. This is incidental but stable; lock it with a test rather than leaving it undefined.
- *Same-type nesting* is unsupported/undefined: the non-greedy match closes at the first closer. Documented, not tested-for.
- *Adjacent markers* (`{+a+}{-b-}`, `{+a+} {+b+}`) produce separate macros (non-greedy), mirroring the existing adjacent-bold rule.
- *Empty markers* (`{++}`, `{--}`) stay literal — `.+?` requires at least one character.
- An *unmatched or lone* marker stays literal and renders as visible `{+` text (consistent with issue #25's "no escape hatches" stance).
- Markers may span literal `\n` (DOTALL) — the newline pass afterwards converts those to `\\`/`\newline` inside the macro argument, which both `\textcolor` groups and ulem's `\sout` accept.
- Marker content containing already-escaped specials (`\&`, `\%`, `\_`, `\{`, `\}`) and stashed code spans passes through unchanged — the change pass runs on escaped text after the code stash, so `{+use `foo` & bar+}` ends as `\kxadded{use \texttt{foo} \& bar}`.

Because every `| inline` / `| inline_cell` / `| inline_flat` call site gets the markers for free, they are in scope by construction for all prose fields on **both** rendering paths — block engine and recipes (recipe templates use the same filters and `klartex-base.cls` loads the sty unconditionally). No per-block opt-in exists, matching how bold/italic already behave.

**False-positive check:** plain-text braces only convert when *both* the `\{+`/`\{-` opener and the matching `+\}`/`-\}` closer are present. E.g. `"intervallet {-5, 5}"` does not match (no `-` before the closing brace). `"{-1-}"` *would* match — acceptable residual risk for a deliberately narrow marker syntax; called out in the docstring.

**Docstring update** (explicitly requested by the issue): add the two markers to the scope list, and reword the out-of-scope list so *generic* strikethrough (`~~text~~`) remains out of scope while semantic change marking is in.

### 3. Block-level `revision` on the `text` block

- `klartex/schemas/blocks/text.schema.json`: new optional property `"revision": { "enum": ["added", "removed"] }` with a Swedish description ("Markera hela stycket som tillagt (grönt) eller struket (rött genomstruket) i en ändringsmarkering …"), keeping `additionalProperties: false` intact.
- `_block_engine.tex.jinja`, `text` arm (~line 197): wrap the paragraph —
  `\BLOCK{if block.get('revision') == 'added'}\kxadded{...}\BLOCK{elif ...}` around `\VAR{block.text | inline}`. A `text` block is a single paragraph by contract ("For separate paragraphs, use separate text blocks"), so a macro-argument wrap is safe; ulem handles the intra-paragraph `\\` breaks.
- **Escape/restore:** `"added"`/`"removed"` contain no LaTeX specials, so `escape_data()` passes them through unchanged — no `_restore_block_types` change needed. No new block type, no nesting → `_restore_block_types`, `components.py`, and `KNOWN_BLOCK_TYPES` untouched.

*Provenance — scope decision, agent judgment, open to question:* the issue marks the block-level attribute "optional, possibly a follow-up" but also notes it is "likely the more important one" for stadgeändringar. Including it only on `text` captures the important case cheaply — a struck/added whole paragraph inside a clause works today because `clause.content[]` nests `text` blocks. Extending `revision` to `clause`/`list` is deferred to a follow-up issue: striking arbitrary nested content (tables, lists, sub-clauses) inside a macro argument is genuinely fragile in LaTeX and needs an environment-based design; bundling that here would put the robust core at risk.

### 4. Agent-facing documentation surface

- `klartex/schemas/block_engine.example.json`: extend the canonical example's markup demo sentence (which today shows `**fet stil**`, `*kursiv*`, `` `kod` ``, smart quotes) with `{+tillagd text+}` / `{-struken text-}` so `klartex example _block` teaches the markers.
- Per-block schema descriptions that say "Inline markup applies" remain accurate and need no edits; `text.schema.json` gets the `revision` description from step 3.
- README has no inline-markup section today — nothing to update there. CHANGELOG is written at release time per repo process, not in this PR.

## Steps

1. **`klartex/cls/klartex-changes.sty`** — colors, `\RequirePackage[normalem]{ulem}`, `\kxaddedstyle`/`\kxremovedstyle` hooks, `\kxadded`/`\kxremoved` macros (colored-text baseline). Add `\RequirePackage{klartex-changes}` to the component-package loading block in `klartex/cls/klartex-base.cls`.
2. **`klartex/inline_markup.py`** — add `_ADDED_RE`/`_REMOVED_RE` matching the escaped forms; insert the substitution pass between the code stash and the bold pass; update the module docstring (markers in scope, generic `~~…~~` still out, marker-semantics list from the Approach section: mixed nesting, adjacent/empty/unmatched markers, `{-1-}` caveat).
3. **Unit tests, `tests/test_inline_markup.py`** — added marker, removed marker, both in one string, bold/italic inside marker content, code span inside marker content, marker inside a code span stays literal, mixed nesting (`{-a {+b+} c-}` both directions), adjacent markers stay separate, empty marker stays literal, unmatched opener stays literal, `"intervallet \{-5, 5\}"` not matched, escaped specials (`\&`, `\%`, `\_`) inside marker content pass through, marker content spanning `\n` (per `newlines` mode). All inputs written in escaped form (`\{+…+\}`), since that is the function's real input contract.
4. **`revision` on `text`** — schema property in `klartex/schemas/blocks/text.schema.json`; conditional wrap in the `text` arm of `klartex/templates/_block_engine.tex.jinja`. Extend the `text` field's schema description to name the marker syntax (`{+…+}` / `{-…-}`) so agents discover it from `klartex schema _block`, not only from the example.
5. **Fixture `tests/fixtures/block_stadgeandring.json`** — realistic stadgeändring: heading + intro, clauses with nuvarande/föreslagen lydelse using inline `{+…+}`/`{-…-}`, one whole paragraph with `revision: "removed"` and one with `revision: "added"` (at least one of them nested inside `clause.content[]`), a `table` (or `description_list`) with markers inside cells, and a long marked passage sized to deterministically cross a page break. This single fixture doubles as the fragility probe from the issue's Notes.
6. **Rendered-source + compilation tests** — in `tests/test_block_engine.py`: (a) tex-source assertions via the existing rendered-LaTeX helper — `\kxadded{`/`\kxremoved{` present, no residual `\{+`/`-\}` marker delimiters for valid markers, `revision`-wrapped text produces the right macro including when nested in `clause.content[]`; (b) schema validation — the fixture passes `_block` validation, and an invalid `revision` value is rejected; (c) xelatex compilation — the fixture renders to a valid PDF (explicit test; fixtures are not globbed), plus a targeted compile of a `text` block per `revision` value.
7. **Highlight experiment (time-boxed, conditional)** — only if `soul` is available in the CI TeX collection: swap `\kxaddedstyle` to an `\hl` variant, run steps 5–6's tests, and visually inspect the table cells and the page boundary in the rendered PDF; keep it only if everything passes unmodified, otherwise revert to colored text and record the outcome in the PR body.
8. **`klartex/schemas/block_engine.example.json`** — add the change-marking demo to the example text; `tests/test_agent_cli.py` should stay green (verify `klartex example _block` output still validates).
9. Full `pytest` run (xelatex required); confirm no test in `test_schemas.py` needs changes (no new block type, so oneOf coverage is untouched). Verify in CI that `ulem.sty` resolves in the workflow's TeX install; extend install docs only if it does not.

## Risks

- **Regex false positives on brace-and-sign prose** — `"{-1-}"`-shaped literal text converts. Mitigation: both delimiters required, caveat documented; the marker grammar is the one specified by the issue.
- **`\sout`/highlight fragility in tabular cells and across page breaks** — the issue's known weak spots. Mitigation: the canonical fixture exercises both from day one; colored-text baseline is the blessed fallback, and the soul experiment is additive behind a style hook. Note: `inline_flat` cells collapse `\n` to spaces, so only `\\`-in-argument (supported by ulem) and plain grouping are ever required inside cells.
- **ulem side effects and availability** — loading ulem without `normalem` would restyle `\emph` everywhere; ulem also becomes a hard runtime dependency of every render. Mitigation: `[normalem]` from the start, an existing-fixture regression run (full test suite compiles every current fixture), and a one-time CI verification that ulem resolves in the workflow's TeX install. `soul` stays experiment-only and is never a shipped dependency unless the experiment is adopted.
- **Marker content interaction with smart quotes/newline passes** — substitution order is specified exactly (after code stash, before bold); unit tests lock it.
- **Scope creep toward clause/list-level revision** — explicitly deferred; the plan states why (macro-argument striking of arbitrary nested blocks is fragile). If review disagrees, that is a design conversation for the follow-up issue, not silent scope growth here.
- **Plan-conflict surface** — `_block_engine.tex.jinja` and `_block_macros.tex.jinja` accumulate spacing fixes with documented rationale (see CLAUDE.md); the `text`-arm edit must not disturb the surrounding `\kxneedspace`/penalty structure. The edit is a pure content wrap inside the existing arm, no spacing lines touched.

## Test Plan

- `pytest tests/test_inline_markup.py` — new marker unit tests plus all existing ones (regression on pass ordering).
- `pytest tests/test_block_engine.py` — rendered-source assertions (`\kxadded`/`\kxremoved` emitted, marker delimiters consumed, clause-nested `revision` correct); invalid `revision` rejected by schema validation; new stadgeändring fixture compiles via xelatex; `revision`-wrapped text blocks compile; all existing fixtures still compile (guards the ulem/`normalem` and base.cls changes).
- `pytest tests/test_schemas.py` — `text.schema.json` remains valid JSON Schema; oneOf coverage unchanged.
- `pytest tests/test_agent_cli.py` — `klartex example _block` output (with the new demo sentence) still validates against the `_block` schema.
- Full `pytest` locally with xelatex (CI enforces that no xelatex test is skipped).
- Manual eyeball: `klartex -d tests/fixtures/block_stadgeandring.json -o /tmp/stadgeandring.pdf` — verify green added text, red struck removed text, correct rendering inside the table and across the page break, in both the inline and block-level forms.
