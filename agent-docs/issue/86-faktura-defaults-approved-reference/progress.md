# Progress: Issue #86 — Faktura defaults: close the gap to the approved reference invoice

## Status: Completed

**Completed:** 2026-08-31
**Branch:** `issue/86-faktura-defaults-approved-reference` (from `main`)

(Update as work proceeds — newest entries first)

## 2026-08-31 — All steps done

- [x] Step 9 — `pytest -rs -n auto`: 535 passed, 0 skipped, 0 failed.
- [x] Step 8 — Visual matrix rendered and eyeballed: faktura, faktura + logo (no
      `logo_height`), kvitto, protokoll, resultaträkning, `block_kallelse`. All
      1 page; over/underfull box warnings unchanged against a 3 cm-margin
      control render.
- [x] Step 7 — `faktura/example.json`: `web` dropped from `footer` (D5).
- [x] Step 6 — Static tests: `test_class_default_chrome` (class margins + black
      brand colors) in `test_renderer.py`, `test_logo_height_schema_default`
      (faktura + kvitto) in `test_schemas.py`.
- [x] Step 5 — `_recipe_base.tex.jinja` both fallbacks `0.8cm` → `1cm`; faktura
      and kvitto schema defaults follow (description example → `'1.5cm'`);
      `test_kvitto_sender_logo_and_footer` updated; new
      `test_faktura_logo_default_height`.
- [x] Step 4 — Reclaim string updated in `test_block_engine.py` (three
      occurrences) and in the four `page_template_*.tex` goldens.
- [x] Step 3 — `page_templates.py::_RECLAIM` `top=2cm` → `top=1.7cm`.
- [x] Step 2 — `klartex-base.cls` geometry `left/right` 3 cm → 2 cm.
- [x] Step 1 — `brandprimary` / `brandsecondary` → `000000`.

### Off-plan adjustment

`tests/test_pdf_text_layer.py::_two_page_body` used `LOREM * 30`, which no
longer paginates at the wider text block — the two tests asserting
`Sida 1 av 2` and a multi-page render failed. The multiplier is now `50`,
which lands mid-band (40 and 60 both still give exactly two pages), keeping
the helper's documented contract.
