# Plan: Issue #79 — faktura and kvitto: use the regular footer slot instead of their own top-level `footer`

## Goal

`faktura` and `kvitto` stop carrying a top-level `footer` field. The only footer surface on the two recipes is the page template's footer slot (`page_template.footer`, variant `columns` with `fields`), so contact and payment details have exactly one home, `footer_has_payment` reads exactly one source, and #99 (columns footer always rendered, derived from `sender`) can build its derivation into the slot alone.

Breaking change, no compatibility shim (repo convention: no aliases or shims, the only consumer is klartex.se). The breaking-change note goes into the release's CHANGELOG entry when the user cuts the release; the PR body carries the text for it.

## Approach

Remove the three places the top-level `footer` is wired, then repoint everything that described or tested it at the slot form:

1. **Template layer.** `_recipe_base.tex.jinja` emits `emit_kxfooter(data.footer, …)` after the page-template composition (lines 13–18) and reads `data.footer` again in the `payment_info` branch (`data_footer`, line 190–191). `_page_template.tex.jinja` has a guard that skips the `columns` fragment when `data.footer` is set (line 41–42). All three go. `footer_has_payment` (`klartex/page_templates.py:662`) already reads the slot's fields and stays as the sole suppression signal.
2. **Schema layer.** Drop the `footer` property from `klartex/templates/faktura/schema.json` and `klartex/templates/kvitto/schema.json`, and rewrite the descriptions that point producers at "the invoice's footer field" (faktura `bankgiro`/`plusgiro`/`iban`/`bic` fallback descriptions, the `sender` descriptions) so they point at `page_template.footer.fields`.
3. **Examples.** Both `example.json` files move their `footer` object to `page_template: {"footer": {"variant": "columns", "fields": {…}}}` so `klartex example faktura` / `kvitto` show the slot form.
4. **Tests.** The tests that lock the old precedence are deleted or rewritten to assert the slot form; the whole-page-source and margins tests that used the top-level footer as their vehicle are re-expressed through the slot.
5. **Consumer audit, first.** `~/repos/klartex.se` was searched during planning. Its runtime sends no top-level `footer` for faktura or kvitto (`backend/src/klartex_se/render.py` only touches `page_template.footer`; the landing-page curl example has no footer), but its public agent guidance does: `llms.txt` line 101 tells agents that `faktura` and `kvitto` take a top-level `footer` as "the canonical place for payment details, taking precedence over the page template's footer", and `backend/README.md` mentions the field. klartex is also a public PyPI package, so klartex.se is the only *known first-party* consumer, not the only consumer. Both facts drive decision 1 (reject rather than silently ignore) and the klartex.se follow-up in step 1.

Nothing in `klartex-footer.sty`, `footer_keyvals`, the `columns` variant or the block engine changes — the slot already renders the invoice footer (company, contact, payment columns, page numbers).

## Steps

0. **Consumer audit and klartex.se follow-up.** Re-run `rg -n -i 'footer' ~/repos/klartex.se --glob '!node_modules' --glob '!agent-docs' -t py -t ts -t html -t txt -t md -t json -t yaml` and confirm the runtime still sends nothing. Then ask the user for an OK to open a klartex.se issue (issue creation needs explicit approval) that updates `llms.txt` line 101 and `backend/README.md` to the slot form before the release that ships this; the PR body links it. The release note is the coordination point: the klartex.se text must change in the same release window.
1. **`klartex/templates/_recipe_base.tex.jinja`**
   - Remove the `emit_kxfooter` import (line 3) and the "Template-level footer from the data" block (lines 13–18).
   - In the `payment_info` arm (line ~186–191): drop `data_footer`, set `footer_payment = page_template.footer_has_payment` (or inline it in the `if`), and rewrite the comment so it describes the now-state: the block is suppressed when the footer slot carries payment details, and renders nothing when the data has no payment fields.
2. **`klartex/templates/_page_template.tex.jinja`** (lines 34–42): remove the `data is defined and data.get('footer')` branch and the comment that announces the recipe-level footer; the `columns` variant then always renders its fragment when predefined. Keep the `pagenumber`/`page_numbers` branch as is.
3. **`klartex/templates/_footer_macros.tex.jinja`**: delete the file — its only consumer was step 1 (verified by grep: `emit_kxfooter` appears nowhere else). **`klartex/renderer.py`**: drop the `footer_keyvals` import (line 15) and the `_jinja_env.globals["footer_keyvals"]` registration (line 38) — the global existed only for that macro; the `columns` fragment path calls `footer_keyvals` directly in Python (`PageTemplate.footer_fragment`, `page_templates.py:691–703`), so the function itself stays in `page_templates.py`.
4. **`klartex/templates/faktura/schema.json`**
   - Replace the `footer` property's object schema with `"footer": false` (decision 1): a payload that still sends it fails validation with the path `footer`, instead of rendering an invoice with no payment details.
   - Rewrite the four fallback descriptions (`bankgiro`, `plusgiro`, `iban`, `bic`): "Fallback: payment details belong in the page template's footer slot (`page_template.footer.fields`). The in-body block is suppressed when those structured fields carry a payment detail; a custom footer source or whole-page source is not inspected, so a caller whose own source prints payment details omits these fields."
   - `sender.description`: "…even when a logo or a page-template footer is present."
   - `note.description` says "Footer note" but the field is rendered in the body by `invoice_note`; change to "Optional note shown below the invoice content."
5. **`klartex/templates/kvitto/schema.json`**: same `"footer": false`; adjust `sender.description` and `note.description` ("Optional note shown below the receipt content.") the same way.
6. **`klartex/templates/faktura/example.json`** and **`kvitto/example.json`**: move the `footer` object to `"page_template": {"footer": {"variant": "columns", "fields": { …same keys… }}}`. Keep the key order of the example readable (put `page_template` last or where `footer` sat). Validate both with `jsonschema` against `get_registry()[name].schema` locally; consider a small test (see Test Plan) so the examples stay valid.
7. **`tests/test_renderer.py`**
   - `test_kvitto_sender_logo_and_footer` (line 573): send the footer as `page_template.footer` slot form; assertions unchanged.
   - `test_recipe_footer_still_wins_over_a_whole_page_source` (line 726) and `test_page_numbers_still_reaches_the_recipe_footer_in_whole_page_mode` (line 742): delete. Under a whole-page source the source owns the footer; there is no recipe-level footer to survive it any more. Replace with `test_whole_page_source_owns_the_footer_and_leaves_payment_info_in_body`: data with `bankgiro="9999-9999"` and `page_template={"footer": {"variant": "columns", "fields": {"bankgiro": "1111-1111"}}}`, rendered with `page_template_source="% whole page"`; assert the marker appears once, `\kxfooter{` and `1111-1111` are absent, and `Betalningsinformation` with `9999-9999` is present (the source owns both slots, so `footer_has_payment` is False and the in-body fallback renders).
   - `test_faktura_margins_reach_its_own_footer_geometry` (line 759): re-express through the slot: `page_template={"margins": {"bottom": "3cm"}, "footer": {"variant": "columns", "fields": {"company": "Bolaget AB"}}}` and keep the assertion `\renewcommand{\kxfooterbottom}{3cm}` precedes `\kxfooter{` (settings step precedes the footer slot in `_page_template.tex.jinja`, so this holds).
   - `test_faktura_top_level_footer_emitted_and_suppresses_payment_info` (line 882): delete; `test_faktura_page_template_dict_emits_footer` (line 802) already covers suppression through the slot.
   - `test_faktura_data_footer_wins_over_page_template_footer` (line 901): delete.
   - `TestRecipePageTemplateSlots` (line 1127): update the class docstring (no template-level footer any more); delete `test_data_footer_still_wins_over_the_footer_slot` and `test_data_footer_still_wins_over_a_custom_footer_source`. Add `test_custom_footer_source_leaves_payment_info_in_body`: with `footer_source=r"\fancyfoot[C]{Egen}"` and `bankgiro="9999-9999"` in the data, `Betalningsinformation` is rendered (a custom source has no fields, so `footer_has_payment` is False) — this documents the one behavioural consequence of the removal.
   - Add `test_faktura_top_level_footer_is_not_rendered`: send `footer={"company": "Från data", "bankgiro": "1111-1111"}` through `_render_recipe_tex` (which bypasses schema validation, so this exercises the template layer) and assert neither string reaches the tex and `\usepackage{klartex-footer}` is absent.
8. **`tests/test_schemas.py`**: add a test parametrised over `faktura`/`kvitto` asserting that a minimal valid payload plus `"footer": {"company": "X"}` raises `jsonschema.ValidationError` whose `path` is `["footer"]` (this is what locks decision 1 at the public `render()` boundary — `_render_recipe_tex` never validates), and that `example.json` validates against the registry schema (mirrors the protokoll example test at lines 44–62).
9. **Comments / docs in now-state**: re-read `_recipe_base.tex.jinja` and `_page_template.tex.jinja` for any remaining mention of a template-level or recipe-level footer (there are two comments besides the code). `README.md` does not document the top-level `footer`, so it needs no change; `CLAUDE.md`'s page-template paragraph says "A recipe's top-level `footer` is document content, not chrome, and is emitted after the composition, so it still wins over either form" — remove that sentence.
10. Confirm `klartex schema faktura` / `kvitto` show `"footer": false` and that `klartex/server/render.py`'s validation-error mapping reports `detail.path == ["footer"]` for a payload sending it (no code change expected; one assertion in `tests/test_server.py` if the existing error-contract tests make it a one-liner, otherwise skip).
11. Run `pytest -n auto`; the golden preamble test (`test_faktura_preamble_unchanged_from_golden`) must pass unchanged — `tests/fixtures/faktura.json` carries no footer, so the default preamble is untouched.
12. PR body: summarise the change, list the breaking-change text for the release CHANGELOG entry (Swedish, under "Breaking changes"), list the agent-judgment decisions below, end with `Closes #79`.

## Design Decisions

### 1. A top-level `footer` is rejected by the schema, not silently ignored

- **Options:** (a) drop the property and let the schema's default `additionalProperties` accept-and-ignore it; (b) set `"footer": false` so a producer that still sends it gets a validation error at `footer`.
- **Decision:** (b).
- **Provenance:** agent judgment. The issue says "drop the top-level `footer` from the … schemas" and nothing about rejecting it, but klartex.se's `llms.txt` has told agents for a release that this field is the canonical place for payment details, and klartex is a public package. With (a), a producer following that guidance would get an invoice with no payment details and no error — a data gap on a customer-facing document that nobody is told about. `false` is one line per schema, not a compatibility shim (nothing is accepted or translated), and it does not pre-empt #78: if #78 lands on `additionalProperties: false`, the entry becomes redundant and is removed then.
- **Consequence if wrong:** a producer gets a 400 instead of a silent render until it moves the fields — the error names the path. Bounded.
- **What would make (a) right:** #78 landing on strict schemas first, which makes the explicit `false` unnecessary.

### 2. `_footer_macros.tex.jinja` is deleted

- **Options:** delete the file; or keep it for a future caller.
- **Decision:** delete.
- **Provenance:** agent judgment, backed by the repo convention of no dead compatibility surface (no aliases/shims).
- **Consequence if wrong:** trivially reversible from git history.

### 3. Whole-page source owns the footer outright

- **Options:** with `page_template_source`, (a) nothing recipe-side emits a footer; (b) keep emitting `\kxfooter` from the slot fields after the source.
- **Decision:** (a). This is what the slot model already does for every other document type (`load_page_template` treats a whole-page source as owning both slots).
- **Provenance:** existing convention (`klartex/page_templates.py`, CLAUDE.md: "the payload's `header`/`footer` are then not read for composition").
- **Consequence if wrong:** a producer combining a whole-page source with slot fields loses the footer; the source can render its own. Bounded.

### 4. Examples move the footer to the slot form; fixtures stay as they are

- **Decision:** `example.json` for both recipes gets `page_template.footer` (issue text). `tests/fixtures/faktura.json` and `kvitto.json` carry no footer today and are left alone — the faktura fixture feeds the golden preamble test, and a footer there would change the default preamble the golden locks.
- **Provenance:** user decision (issue) for the examples; agent judgment for leaving the fixtures untouched.
- **Consequence if wrong:** none beyond a fixture edit in a follow-up.

### 5. A custom `footer_source` no longer suppresses the in-body `payment_info`

- **Decision:** with a custom footer source, `footer_has_payment` is False (no fields), so the in-body block renders when the data has payment fields. Before, a producer could pair a custom source with a top-level `footer` to suppress it; now the producer simply omits the standalone `bankgiro`/… fields.
- **Provenance:** follows from the issue ("let `footer_has_payment` … read the footer slot alone"); locked by the new test in step 7.
- **Consequence if wrong:** duplicate payment details on a page for that pairing until the producer drops the fields. Bounded.

## Risks

- **Published guidance on klartex.se contradicts this change** (`llms.txt` line 101, `backend/README.md`). Until it is updated, agents reading it will send a field the schema now rejects. Mitigated by decision 1 (a clear 400 at `footer`, not a silent gap) and by step 0's klartex.se follow-up, which needs the user's OK to open. This is what makes the risk Medium rather than Low.
- Test churn is the bulk of the diff; the risk is deleting a test that also locked something else. Each test listed in step 7 was read during planning and locks only the top-level-footer precedence, except the margins test, which is re-expressed rather than deleted.
- #99 is blocked on this and will change the same `payment_info`/footer region of `_recipe_base.tex.jinja`; landing this first is the agreed order (issue comment).
- #96 (retire `narrowmargins`) touches `_recipe_base.tex.jinja`'s `\documentclass` line and the recipe.yaml files, not the footer region; no conflict beyond merge adjacency.
- klartex.se's runtime sends no top-level `footer` for the two recipes, so nothing breaks at runtime today; the documentation follow-up above is the coordination point.

## Test Plan

- `pytest -n auto` green (xelatex required); in particular `tests/test_renderer.py::test_faktura_preamble_unchanged_from_golden` passes without a golden update.
- New/updated tests in `tests/test_renderer.py`: slot-form kvitto footer; top-level `footer` renders nothing; custom `footer_source` leaves the in-body payment block; whole-page source with slot fields emits no `\kxfooter`; margins reach the slot footer's `\kxfooterbottom` before `\kxfooter{`.
- `tests/test_schemas.py`: a top-level `footer` fails validation at path `footer` on both recipes; both `example.json` validate against their registry schema.
- Manual: `klartex example faktura | klartex -t faktura -o /tmp/faktura.pdf` (with the repo's code, not the stale PATH shim) renders with the three-column footer from `page_template.footer.fields` and no in-body Betalningsinformation; `klartex schema faktura` shows `"footer": false`; `klartex -t faktura` with a payload carrying a top-level `footer` fails validation naming `footer`.
- `grep -rn 'data.footer\|emit_kxfooter\|data_footer\|template-level footer\|recipe-level footer' klartex tests CLAUDE.md` returns nothing.
