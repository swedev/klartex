# Progress: Issue #79 — faktura and kvitto: use the regular footer slot instead of their own top-level `footer`

## Status: Completed (2026-09-02)

(Update as work proceeds — newest entries first)

## 2026-09-02

All plan steps done on branch `issue/79-faktura-kvitto-footer-slot`.

- **Step 0** — consumer audit re-run against `~/repos/klartex.se`. Runtime sends no top-level `footer` for either recipe (`backend/src/klartex_se/render.py` touches only `page_template.footer`); `llms.txt:101` and `backend/README.md` still document the old field. The klartex.se documentation follow-up is **not** opened — issue creation needs the user's explicit OK.
- **Step 1** — `_recipe_base.tex.jinja`: `emit_kxfooter` import and the template-level footer block removed; the `payment_info` arm now reads `page_template.footer_has_payment` alone.
- **Step 2** — `_page_template.tex.jinja`: the `columns`-vs-`data.footer` branch removed, so a predefined `columns` footer always renders its fragment.
- **Step 3** — `_footer_macros.tex.jinja` deleted; `footer_keyvals` import and Jinja global dropped from `renderer.py` (the function stays in `page_templates.py`).
- **Steps 4–5** — `footer` rejected in both recipe schemas; fallback/`sender`/`note` descriptions repointed at `page_template.footer.fields`.
- **Step 6** — both `example.json` moved to `page_template.footer` slot form; both validate against their registry schema.
- **Steps 7–8** — tests rewritten (see report); new tests for the whole-page source, the custom footer source, the non-rendered top-level footer, schema rejection at path `footer`, example validity, and the server's `detail.path`.
- **Step 9** — the recipe-footer sentence removed from `CLAUDE.md`; grep for `data.footer` / `emit_kxfooter` / `data_footer` / template-level footer returns nothing.
- **Steps 10–11** — `pytest -n auto` green (688 passed, 9 pre-existing font-availability skips); `test_faktura_preamble_unchanged_from_golden` passes without a golden update; both examples render to PDF with the columns footer and no in-body Betalningsinformation.

### Deviation from the plan

Step 4/8 specified `"footer": false`. Under jsonschema 4.26 a boolean-`false` subschema raises with an **empty** `absolute_path`, so neither the message nor the server's `detail.path` names the field. `{"not": {}, "description": …}` is equivalent in strictness, reports `path == ["footer"]`, and the description tells the producer where the fields belong.
