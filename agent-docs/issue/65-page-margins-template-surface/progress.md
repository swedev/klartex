# Progress: Issue #65 — Expose page margins on the page-template surface

## Status: Completed

(Update as work proceeds — newest entries first)

### Steps

- [x] 1. Model + validation in `page_templates.py`
- [x] 2. Loader + `PageTemplate.margin_setup`
- [x] 3. D8 in `klartex-footer.sty`
- [x] 4. Composition in `_page_template.tex.jinja`
- [x] 5. Unit tests (`tests/test_page_templates.py`)
- [x] 6. Tex-level tests (`tests/test_block_engine.py`)
- [x] 7. Recipe + cls↔Python sync tests (`tests/test_renderer.py`)
- [x] 8. Measurable layout test (`tests/test_pdf_text_layer.py`)
- [x] 9. Schema surface (`tests/test_schemas.py`)
- [x] 10. Docs (README, README.en.md, CLAUDE.md)
- [x] 11. Full suite `pytest -n auto`

**Completed:** 2026-08-31 — full suite green (596 passed, xelatex + pdftotext present).
