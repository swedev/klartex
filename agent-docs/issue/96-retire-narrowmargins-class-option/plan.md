# Plan: Issue #96 — Re-express the invoice recipes' margins through the margins surface and retire the narrowmargins class option

## Goal

faktura and kvitto keep their tighter geometry — 2cm side margins and a 1.7cm text top when the header is reclaimed — but get it from the same place every other margin value comes from: a `page_template.margins` object, declared as the recipe's default in `recipe.yaml` and merged key by key under whatever the payload's own `page_template.margins` sets. The `narrowmargins` documentclass option and the `document.class_options` plumbing that carries it (recipe schema key, `RecipeDocument` field, context key, the `\documentclass[...]` arm in `_recipe_base.tex.jinja`) are removed. One margins mechanism, not two.

The rendered faktura and kvitto PDFs must not move in the geometry the option actually shaped: with no payload `margins` and the header reclaimed (the recipe default, the fixtures, the examples), the body text lands where it lands today. The one configuration the option never shaped — a faktura/kvitto whose page-chrome header *renders* — changes; see Design Decision 3.

## Approach

### State verified before planning

- `klartex/cls/klartex-base.cls` lines 10–25: `\newcommand{\kxsidemargin}{3cm}`, `\newcommand{\kxreclaimtop}{2cm}`, then `\DeclareOption{narrowmargins}{\renewcommand{\kxsidemargin}{2cm}\renewcommand{\kxreclaimtop}{1.7cm}}` and `\ProcessOptions\relax`. The geometry block reads `left=\kxsidemargin, right=\kxsidemargin, top=0.9cm, headheight=1.2cm, headsep=1.3cm`. `\kxreclaimtop` is used only by the reclaim (`\geometry{top=\kxreclaimtop, headheight=0pt, headsep=0pt, includehead=false}`); `\kxsidemargin` only by the class geometry.
- `klartex/recipe.py`: `RecipeDocument.class_options: str = ""` (line 63), read from `doc_raw.get("class_options", "")` in `load_recipe` (line 237), passed through as `"class_options"` in the context dict `prepare_recipe_context` returns (line 382). `RecipeDocument.page_template` is `{**RECIPE_DEFAULT_SLOTS, **page_template}` and is handed to `load_page_template(data.get("page_template"), defaults=recipe.document.page_template, ...)` (line 368–375). `_pop_fields_from` edits only the footer slot object, so a `margins` key on the recipe's `page_template` passes through untouched.
- `klartex/page_templates.py::load_page_template` (line 928): `defaults` is documented as "Slot values" and is read only for `defaults["header"]` / `defaults["footer"]`. `margins` comes from `_check_margins(overrides.get("margins"))` alone (line 987), so a recipe-default `margins` is silently ignored today. `_check_margin_top(template)` runs on the resolved template and rejects `top <= 2.1cm` only when the header is predefined and carries content (`header_macros` non-empty). `PageTemplate.margin_setup` emits, for a set `top`, both `\renewcommand{\kxreclaimtop}{top}` and `headsep=\dimexpr top-2.1cm\relax`; for `left`/`right` also `\setlength{\headwidth}{\textwidth}`.
- `klartex/schemas/recipe.schema.json`: `document` is `additionalProperties: false` with `class_options` (string, line 97–100) and `page_template` (loosely typed object, description says "as a slot object", line 49–52).
- `klartex/templates/_recipe_base.tex.jinja` lines 3–7: `\BLOCK{if class_options}\documentclass[\VAR{class_options}]{klartex-base}\BLOCK{else}\documentclass{klartex-base}\BLOCK{endif}`.
- `klartex/templates/faktura/recipe.yaml` and `kvitto/recipe.yaml` line 9: `class_options: narrowmargins`. Their `page_template` carries only a `footer` slot object (`columns` + `fields_from`); the header slot falls back to `RECIPE_DEFAULT_SLOTS["header"] == "letterhead"` — the bare variant, no fields — so `\orgname` is empty and the reclaim fires. Today's default faktura/kvitto text block is therefore: left/right 2cm, top 1.7cm (reclaimed), bottom from the class/footer band.
- `tests/fixtures/faktura.json` and `kvitto.json` carry no `page_template`; `tests/fixtures/golden/page_template_faktura.tex` line 1 is `\documentclass[narrowmargins]{klartex-base}` and is compared line-for-line (sorted, blanks dropped) by `test_faktura_preamble_unchanged_from_golden` via `golden_preamble`.
- Tests that pin the current state: `tests/test_renderer.py::test_class_default_chrome` (asserts both the `\newcommand` defaults and the two `\renewcommand` lines of the option), `::test_narrowmargins_class_option_scoped_to_faktura_and_kvitto` (reads the four recipe.yamls' `class_options` and the meta template's `\documentclass[\VAR{class_options}]` line), `::test_faktura_margins_override_the_narrowmargins_defaults` (asserts `\documentclass[narrowmargins]` precedes `\geometry{left=4cm, headsep=\dimexpr 5cm-2.1cm\relax}`), `::test_faktura_margins_reach_the_footer_slot_geometry`, `::test_header_band_constant_matches_the_class_geometry` (sum test on the cls `top` + `headheight`, untouched by this change), `tests/test_page_templates.py::TestMarginTopMinimum::test_reclaimed_header_takes_any_positive_top` (docstring cites narrowmargins; behaviour stays). `tests/test_recipe.py::test_recipe_document_section` asserts protokoll's `page_template == RECIPE_DEFAULT_SLOTS` (unaffected: protokoll declares no margins). `tests/test_schemas.py::test_injected_page_template_describes_the_recipes_own_default` checks the `describe_recipe_defaults` sentence by substring.
- `tests/test_pdf_text_layer.py` has `_word_box(pdf, word) -> (x, y)` over `pdftotext -bbox` and `_PT_PER_CM`; its margin tests run on the block engine only. Nothing measures faktura/kvitto text positions today.
- `README.md` documents `margins` (section "Marginaler") and recipe defaults for slots (line 155) but never mentions `narrowmargins` or `class_options`; `CHANGELOG.md` 0.18.0 records the option's introduction (#86, #88). No other code, docs or workflows reference `class_options`/`narrowmargins`.
- The whole-page source mode and the per-slot custom sources already receive `margin_setup` before the source (`_page_template.tex.jinja` step 1), so a recipe-default `margins` follows the same "the source's own `\geometry` wins" rule the README states.

### Where each change lives

**The margins default (recipe side).** `faktura/recipe.yaml` and `kvitto/recipe.yaml` drop `class_options` and gain, under `document.page_template`:

```yaml
    margins:
      left: 2cm
      right: 2cm
      top: 1.7cm
```

`load_recipe` already deep-copies `document.page_template` and merges it over `RECIPE_DEFAULT_SLOTS`, so the `margins` key rides along into `RecipeDocument.page_template` and on to `load_page_template(defaults=...)`. Validate it at load time the way slots are: `load_recipe` runs `_check_margins(page_template.get("margins"))` (import from `page_templates`) so a malformed recipe value fails at discovery (the registry loads every recipe at startup, per 0.19.0), not at first render. The recipe schema's `document.page_template` description is updated to say the object may also carry `margins`, merged key by key under the payload's.

**The merge (page-template side).** `load_page_template` reads `defaults.get("margins")` and merges the payload's `margins` over it per key:

```python
margins = {**_check_margins(defaults.get("margins")), **_check_margins(overrides.get("margins"))}
```

(`_check_margins(None)` returns `{}`, verified at `page_templates.py:407`.) `BLOCK_DEFAULT_SLOTS` and `RECIPE_DEFAULT_SLOTS` carry no `margins`, so the block engine and every other recipe are unchanged. Everything downstream — `margin_setup`, `_check_margin_top`, the `margins` attribute the tests read — sees one merged dict and needs no change. The `defaults` docstring becomes "slot values and, optionally, a `margins` object, in payload syntax, for what `spec` leaves out", and the module docstring's sentence about recipes declaring their own slots gets the same addition.

**Retiring the option (class side).** `klartex-base.cls` drops the `\DeclareOption{narrowmargins}` block and `\ProcessOptions\relax` (no options remain to process; `\LoadClass[10pt,a4paper]{article}` is unaffected). The `\kxsidemargin` / `\kxreclaimtop` `\newcommand`s stay with their 3cm / 2cm values, and the comment above them describes them as the class defaults a page template's `margins` renews — written in now-state, no mention of the retired option.

**Retiring the plumbing (recipe side).** `RecipeDocument.class_options`, the `doc_raw.get("class_options", "")` read, and the `"class_options"` context key go; `recipe.schema.json` drops the `class_options` property (`additionalProperties: false` then rejects any recipe still carrying it — the desired failure mode); `_recipe_base.tex.jinja` lines 3–7 collapse to `\documentclass{klartex-base}`.

**Golden and tests.** The faktura golden's first line becomes `\documentclass{klartex-base}` and the preamble gains the three `margin_setup` lines the recipe default now emits:

```latex
\renewcommand{\kxreclaimtop}{1.7cm}
\geometry{left=2cm, right=2cm, headsep=\dimexpr 1.7cm-2.1cm\relax}
\setlength{\headwidth}{\textwidth}
```

(Exact lines to be taken from the actual render output; `golden_preamble` sorts, so position is irrelevant but every line must match verbatim.) The negative `headsep` is inert in the default configuration: the reclaim that follows sets `headsep=0pt`, and the loader rejects a rendering predefined header at this top (see Design Decision 3).

### Position invariance check

Before touching anything, render `tests/fixtures/faktura.json` and `kvitto.json` with the repo code (not the stale PATH shim — `python -m klartex` or `PYTHONPATH`) and record, with `pdftotext -bbox` via `_word_box`, the `(x, y)` of one word per fixture that occurs only in the body (not in the header or footer — pick it from the fixture text at implementation time, e.g. the first word of the recipient block or the first line description; "leftmost word on the page" is not a body-margin proxy since footer text can be leftmost). After the change the same renders must give the same boxes within ±0.5pt. Those recorded `(x, y)` pairs are then committed as the expected values of a permanent test in `tests/test_pdf_text_layer.py` (Test Plan item 4), so the recipe default cannot drift from the retired class values silently — the x must also equal `2 * _PT_PER_CM` from the paper edge, which is what ties the number to the design rather than to a snapshot.

### Custom and rendering headers on faktura/kvitto

Three shapes exist beside the default; the plan settles each (Design Decision 3):

- **Predefined header with content** (`letterhead` with `org_name`, or `logo` with a file): rejected by `_check_margin_top` unless the payload also sets `margins.top > 2.1cm`. `tests/test_renderer.py::test_header_slot_settings_reach_the_recipe_path` (line 1337) renders exactly this shape without a top and would now raise; it gets `"margins": {"top": "3.4cm"}` added to its payload (3.4cm is the class's rendering-header text top, so the assertion on `\renewcommand{\orgname}` is unchanged in meaning), and a sibling test locks the rejection without the top.
- **`header_source` / `page_template_source` that sets its own `\geometry`**: wins, as the README already states for margins; a test asserts the recipe's `\geometry{left=2cm, right=2cm, headsep=…}` precedes the source text so the source's geometry is what stands.
- **`header_source` / `page_template_source` without geometry**: receives the recipe default (`headsep` −0.4cm). Not rejected — the loader cannot see inside a source. Documented in the schema description of the recipe default and in the PR body; a test asserts the emitted lines so the behaviour is deliberate, not accidental.

### `null` and `{}` in the payload

`margins: null`, `margins: {}` and an absent `margins` all mean "nothing overridden" today (`TestMargins::test_absent_null_and_empty_all_mean_no_margins`); with recipe defaults all three inherit the recipe's margins. There is no reset syntax — a producer that wants the class geometry back on faktura sends the values (`{"left": "3cm", "right": "3cm", "top": "2cm"}`). Design Decision 6.

## Steps

1. Baseline: render faktura and kvitto fixtures with the current code; record the `(x, y)` of one body-only word per fixture (scratch notes, not committed yet — they become the expected values in step 9).
2. `klartex/page_templates.py`: merge `defaults.get("margins")` under the payload's margins in `load_page_template`; update the `defaults` docstring and the module docstring sentence about recipe-declared defaults.
3. `klartex/recipe.py`: remove `RecipeDocument.class_options`, its read in `load_recipe`, and the `"class_options"` context key; validate `page_template.margins` in `load_recipe` via `_check_margins`, re-raising as `ValueError` with the recipe path (mirroring how `_pop_fields_from` reports); rewrite the `page_template` field comment (line 64) from "Slot object" to "slots and, optionally, `margins`, in payload syntax"; extend `describe_recipe_defaults` with the margins clause (Design Decision 5).
4. `klartex/schemas/recipe.schema.json`: delete the `class_options` property; extend the `document.page_template` description with the `margins` default, its per-key merge, and that a custom header source without its own geometry receives it.
5. `klartex/templates/_recipe_base.tex.jinja`: collapse the `\documentclass` arm to the single unconditional line.
6. `klartex/templates/faktura/recipe.yaml`, `kvitto/recipe.yaml`: drop `class_options`; add `page_template.margins` `{left: 2cm, right: 2cm, top: 1.7cm}` with a one-line comment stating it is the recipe's default and the payload's `margins` wins per key.
7. `klartex/cls/klartex-base.cls`: remove `\DeclareOption{narrowmargins}` and `\ProcessOptions\relax`; rewrite the margin-profile comment in now-state.
8. Render the faktura fixture with the changed code; diff its preamble against `tests/fixtures/golden/page_template_faktura.tex` by hand and confirm exactly the `\documentclass` line and the three margin lines differ; update the golden from that output. Fix the golden test's docstring (`test_faktura_preamble_unchanged_from_golden`, line 1288), which still says "page-number footer" — the default footer has been `columns` since #99.
9. Tests:
   - `tests/test_renderer.py::test_class_default_chrome`: drop the two `\renewcommand` assertions; add `assert "narrowmargins" not in cls`.
   - Replace `test_narrowmargins_class_option_scoped_to_faktura_and_kvitto` with `test_narrow_margins_are_recipe_defaults_for_faktura_and_kvitto`: load the four recipe.yamls, assert faktura/kvitto `document.page_template.margins == {"left": "2cm", "right": "2cm", "top": "1.7cm"}`, protokoll/resultatrakning have no `margins` and no `class_options`; assert the meta template contains `\documentclass{klartex-base}` and not `class_options`.
   - Rewrite `test_faktura_margins_override_the_narrowmargins_defaults` as `test_faktura_payload_margins_override_the_recipe_defaults_per_key`: payload `{"margins": {"left": "4cm", "top": "5cm"}}` yields `\geometry{left=4cm, right=2cm, headsep=\dimexpr 5cm-2.1cm\relax}` and `\renewcommand{\kxreclaimtop}{5cm}` — `right` keeps the recipe default. Add a default-payload variant asserting `\geometry{left=2cm, right=2cm, headsep=\dimexpr 1.7cm-2.1cm\relax}` and `\documentclass{klartex-base}`.
   - `test_header_slot_settings_reach_the_recipe_path`: add `"margins": {"top": "3.4cm"}` to the payload. New sibling: the same header without a top raises `ValueError` matching "margins.top must be greater". New: `header_source="% custom"` on faktura emits the recipe `\geometry{left=2cm, right=2cm, …}` before `% custom`; `page_template_source` likewise (one occurrence of the source, geometry before it).
   - `tests/test_page_templates.py`: add `TestDefaultsMargins` — `load_page_template(None, defaults={**BLOCK_DEFAULT_SLOTS, "margins": {"left": "2cm"}}).margins == {"left": "2cm"}`; payload overrides one key and keeps the rest; `{"margins": None}` and `{"margins": {}}` both inherit the defaults; a malformed default is rejected with the `margins.<key>` message; `load_page_template()` without defaults still gives `margins == {}`. Update the `test_reclaimed_header_takes_any_positive_top` docstring to refer to the recipes' 1.7cm default instead of the option.
   - `tests/test_recipe.py`: assert faktura's `recipe.document.page_template["margins"]` equals the dict above; assert a recipe.yaml with `class_options` fails schema validation (copy budgetrapport into `tmp_path`, inject the key, expect `jsonschema.ValidationError`); assert a recipe.yaml with `margins: {left: "2"}` raises `ValueError` at load.
   - `tests/test_schemas.py`: assert the recipe schema's `document` properties no longer include `class_options`; extend the parametrised description test so faktura/kvitto's description also contains the margins clause.
   - `tests/test_pdf_text_layer.py` (`@requires_tools`): for faktura and kvitto fixtures, the chosen body-only word sits at the step-1 `(x, y)` (±0.5pt) and its x equals `2 * _PT_PER_CM`.
10. `README.md` (line 155) and `README.en.md` (line 155): in the paragraph about recipe-declared defaults, add one sentence that a recipe may also declare default `margins` (faktura and kvitto: 2cm sides, 1.7cm top) which the payload's `margins` overrides per key. `CLAUDE.md` "Page templates" paragraph: one clause that `defaults` may carry `margins`.
11. Run `pytest -n auto`; smoke renders with the repo code (`python -m klartex -d tests/fixtures/faktura.json -o <scratch>/faktura.pdf`, same for kvitto and protokoll); `klartex templates` and `klartex schema faktura`.
12. PR body: `Closes #96`; the breaking-change text for the user to lift into `CHANGELOG.md` at release time (the changelog is written at release, CLAUDE.md "Releases" — no `Unreleased` entry in this PR): option and `class_options` gone; recipe-default `page_template.margins` 2cm/2cm/1.7cm merged per key under the payload's; the three header shapes from "Custom and rendering headers" and what a payload must send for each; the agent-judgment decisions below.

## Design Decisions

### 1. Recipe-default margins merge under the payload's margins key by key, in `load_page_template`

- **Options:** (a) merge in `load_page_template` via the existing `defaults` parameter; (b) merge in `recipe.py::prepare_recipe_context` before calling the loader; (c) a separate `default_margins=` keyword.
- **Decision:** (a).
- **Provenance:** user decision on semantics (issue text: "recipe-default `page_template.margins` values"; "explicit payloads already use to override the option per key") — the per-key merge is what the payload override already does today. The location is agent judgment.
- **If wrong:** bounded — moving the merge between two functions is a mechanical refactor with the same tests.
- **Rationale:** `defaults` is already the recipe's `page_template` dict in payload syntax, and it already flows into the loader; extending its meaning from "slots" to "slots and margins" keeps one entry point, so `_check_margin_top` and `margin_setup` see the merged value without a second code path. (b) would make `recipe.py` reach into the page-template model's validation; (c) is a new surface for one recipe-only need.

### 2. Only `margins` is taken from `defaults`; other document-level settings are not

- **Options:** (a) merge `margins` only; (b) generalise so a recipe can default any `DOCUMENT_SETTINGS` key (`font`, `diff_style`, …).
- **Decision:** (a).
- **Provenance:** agent judgment.
- **If wrong:** bounded — (b) is additive later and changes no behaviour of (a).
- **Rationale:** the issue is scoped to margins; no recipe needs a default font today, and the scalar settings would need a different merge rule (whole value, not per key). What would make (b) right: a second recipe-level default appearing.

### 3. The recipe default carries `top: 1.7cm`, with plain `margins` semantics — no special "reclaim-only" top

- **Options:** (a) `{left, right, top}` with the loader's ordinary rules; (b) `{left, right}` only, letting the reclaimed top fall back to the class's 2cm; (c) a new "reclaim-only" flavour of `top` that skips the `headsep` adjustment and the minimum check when the value comes from the recipe.
- **Decision:** (a).
- **Provenance:** agent judgment. The issue settles the mechanism ("recipe-default `page_template.margins` values … one margins mechanism, not two") and requires geometry parity; it does not address the header-renders case.
- **If wrong:** bounded, but with a visible edge: a faktura/kvitto payload that adds a *rendering* predefined header (letterhead with `org_name`, or `logo` with a file) is now rejected by `_check_margin_top` ("margins.top must be greater than 2.1cm …") unless it also sends `margins.top`. Today that payload renders with the class's 3.4cm text top. Likewise a custom `header_source` / `page_template_source` on faktura/kvitto that does not set its own `\geometry` receives `headsep=\dimexpr 1.7cm-2.1cm\relax` (−0.4cm) instead of the class's 1.3cm; a source that sets geometry wins as documented. Both are repaired by the payload sending `margins.top` (e.g. `3.4cm`), and the loader's message says so. Nothing is destroyed and nothing is published: the failure is a validation error or a visibly wrong PDF in a shape no fixture, example or test uses, and the only consumer is the user's klartex.se, checked before release (Risks). Reversal is a follow-up PR implementing (c). This is the one behavioural change beyond the issue's wording, and the reason the risk is Medium rather than Low.
- **Rationale:** (b) moves the default text top from 1.7cm to 2cm — the issue's "for no user-visible gain" premise means the PDFs must not change, so (b) is out. (c) is a second margins semantics, which the issue explicitly rejects. (a) states the truth about these two documents: the text top *is* 1.7cm, and a header that renders at that top is geometrically invalid — rejecting it with the existing message is the honest behaviour. The invoice/receipt recipes have their own in-body header (`invoice_header` / `receipt_header`) and no fixture, example or test puts a page-chrome header on them.

### 4. `\ProcessOptions\relax` goes with the option

- **Options:** (a) remove `\DeclareOption` and `\ProcessOptions`; (b) remove only `\DeclareOption`.
- **Decision:** (a).
- **Provenance:** agent judgment.
- **If wrong:** bounded — one line in the cls, no rendered change either way.
- **Rationale:** with no declared options there is nothing to process; a leftover `\ProcessOptions` invites the next option back. What would make (b) right: another class option arriving.

### 5. `describe_recipe_defaults` gains a margins clause only if it fits the sentence

- **Options:** (a) extend the injected `page_template` schema description with "…; margins default to 2cm left/right and a 1.7cm top" for recipes that declare margins; (b) leave the description to slots and document the default in README/CHANGELOG only.
- **Decision:** (a), as a trailing clause appended after the footer text — the substring the tests in `tests/test_schemas.py` check ("the columns footer, with fields derived from sender") stays intact.
- **Provenance:** agent judgment; existing convention that `klartex schema <name>` is the agent's discovery surface and states the recipe's own default (CLAUDE.md, #99).
- **If wrong:** bounded — a sentence in a generated description.
- **Rationale:** an agent composing a faktura payload should learn the margin defaults where it learns the footer defaults.

### 6. `margins: null` / `{}` in the payload inherit the recipe defaults; no reset syntax

- **Options:** (a) `null`, `{}` and absent all mean "override nothing" and inherit the defaults; (b) `null` clears the recipe defaults back to the class geometry.
- **Decision:** (a).
- **Provenance:** existing convention — `TestMargins::test_absent_null_and_empty_all_mean_no_margins` establishes the three as equivalent, and `header: null` / `footer: null` mean "empty slot", not "surface default", so `null` already has a meaning per key that is not "reset".
- **If wrong:** bounded — (b) is additive.
- **Rationale:** the class values are three literals a producer can send; a reset keyword is a second way to say them. What would make (b) right: a producer that needs the class geometry on faktura without knowing the numbers.

### 7. Recipe-level `margins` are validated at load, not first render

- **Options:** (a) `_check_margins` in `load_recipe`; (b) rely on `load_page_template` raising at render time.
- **Decision:** (a).
- **Provenance:** existing convention — `_pop_fields_from` validates recipe syntax at load, and 0.19.0 made the registry load every recipe at startup "so an invalid recipe.yaml fails at discovery instead of at first rendering".
- **If wrong:** bounded.
- **Rationale:** a recipe is authored once and rendered many times; the failure belongs to the author's run.

## Risks

- **Golden drift masking a regression.** The faktura golden must change in this PR; the discipline is to diff it by hand and confirm only the `\documentclass` line and the three margin lines differ. Any other diff is a bug in the merge.
- **Rendering-header payloads on faktura/kvitto (Design Decision 3).** Now rejected (predefined) or given a negative `headsep` (custom source without geometry) unless the payload sets `margins.top`. Called out in CHANGELOG and PR body so klartex.se can be checked.
- **klartex.se payload shapes (Design Decision 3).** If klartex.se ever sends faktura/kvitto with a rendering letterhead/logo header or a geometry-less custom header source, it needs `margins.top` before the release that ships this. The PR body lists the three shapes so the user can grep klartex.se before releasing; that check is the release-time gate, not a blocker for implementation.
- **Concurrent plans touching the same files.** `agent-docs/issue/99-faktura-kvitto-sender-footer/` (shipped in 0.19.0, closed) already named #96 as a same-file neighbour; #98 and #104 (letterhead/footer break opportunities) are merged. No open plan edits `recipe.py`, `recipe.schema.json`, the two recipe.yamls or the golden at the time of planning.
- **Stale CLI shim.** Smoke renders must use the repo code, not the pyenv `klartex` on PATH (memory: `klartex-cli-shim-stale.md`).

## Test Plan

1. `pytest -n auto` green, with the CI skip guard in mind — no new `pytest.skip`.
2. Unit: `tests/test_page_templates.py::TestDefaultsMargins` (defaults merge, per-key override, malformed default rejected, no defaults → `{}`); `tests/test_recipe.py` (faktura/kvitto expose the margins default; `class_options` in a recipe.yaml is a schema error; a malformed recipe `margins` is a `ValueError` at load); `tests/test_schemas.py` (`class_options` absent from the recipe schema; `klartex schema faktura` description still contains the footer sentence and now the margins clause).
3. Source-level: `tests/test_renderer.py` — cls has no `narrowmargins`; the four recipe.yamls' margins/absence; `\documentclass{klartex-base}` in the meta template; default faktura emits `\geometry{left=2cm, right=2cm, headsep=\dimexpr 1.7cm-2.1cm\relax}` + `\renewcommand{\kxreclaimtop}{1.7cm}` + `\setlength{\headwidth}{\textwidth}`; payload `{left: 4cm, top: 5cm}` yields `left=4cm, right=2cm` (per-key); `test_faktura_margins_reach_the_footer_slot_geometry` still passes; the updated golden matches.
4. PDF text layer (`@requires_tools`): for faktura and kvitto fixtures, one body-only word per fixture sits at the pre-change `(x, y)` recorded in step 1 (±0.5pt), and its x equals `2 * _PT_PER_CM` — committed expected values, so CI holds the invariance, not just the implementation session.
5. Edge behaviour locked: a faktura payload with `header: {variant: letterhead, fields: {org_name: "X"}}` and no `margins` raises `ValueError` matching "margins.top must be greater"; the same payload with `margins: {top: "3.4cm"}` renders (`test_header_slot_settings_reach_the_recipe_path`); `header_source` and `page_template_source` on faktura get the recipe geometry emitted before the source, once.
5b. `{"margins": None}` and `{"margins": {}}` in a faktura payload still produce the recipe's `\geometry{left=2cm, right=2cm, …}`.
6. Smoke with repo code: `python -m klartex -d tests/fixtures/faktura.json -o <scratch>/faktura.pdf`, same for kvitto and protokoll; `klartex templates` and `klartex schema faktura` run without error.

## Files Summary

- `klartex/cls/klartex-base.cls` — drop `\DeclareOption{narrowmargins}` + `\ProcessOptions\relax`; rewrite the margin-profile comment.
- `klartex/page_templates.py` — `load_page_template`: merge `defaults["margins"]` under the payload's; docstrings.
- `klartex/recipe.py` — remove `class_options` (dataclass field, load, context key); validate recipe `margins` at load; extend `describe_recipe_defaults` with the margins clause.
- `klartex/schemas/recipe.schema.json` — remove `class_options`; extend the `page_template` description.
- `klartex/templates/_recipe_base.tex.jinja` — unconditional `\documentclass{klartex-base}`.
- `klartex/templates/faktura/recipe.yaml`, `klartex/templates/kvitto/recipe.yaml` — `class_options` → `page_template.margins`.
- `tests/fixtures/golden/page_template_faktura.tex` — new first line and three margin lines.
- `tests/test_renderer.py`, `tests/test_page_templates.py`, `tests/test_recipe.py`, `tests/test_schemas.py`, `tests/test_pdf_text_layer.py` — as in steps 8–9.
- `README.md`, `README.en.md`, `CLAUDE.md` — one sentence each on recipe-default margins. No `CHANGELOG.md` change in the PR; the entry is written at release from the PR body.
