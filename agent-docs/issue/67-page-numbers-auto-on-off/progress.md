# Progress: Issue #67 — Page numbers: auto/on/off, as a setting on the slot that carries them

## Status: Completed (2026-09-04)

(Update as work proceeds — newest entries first)

- 2026-09-04: All eleven plan steps done on `issue/67-page-numbers-auto-on-off`.
  - Steps 1–4 (red tests): `tests/test_page_templates.py` (new `TestFooterPageNumbers`, document-level key now rejected), `tests/test_schemas.py` (accept/reject cases plus generated-schema and `list_slot_variants()` locks), `tests/test_block_engine.py` (composition emits `\kxifpagenumbers{<mode>}`, never `\fancyfoot[C]{}`; columns emits `pagenumbers=<mode>`), `tests/test_server.py` (top-level `page_numbers` → `400 validation_error`, `detail.path == ["page_template"]`), `tests/test_pdf_text_layer.py` (nine-case rendered matrix over both variants plus the faktura `fields_from` case).
  - Steps 5–8 (one atomic change): `PAGE_NUMBERS_SETTING` on both footer variants, `page_numbers` out of `DOCUMENT_SETTINGS`, `SlotSpec.page_numbers`, `PageTemplate.page_numbers` removed, enum value validation in `_check_settings`; `\kxifpagenumbers` in `klartex-base.cls` with `\RequirePackage{refcount}` moved there; `pagenumber`/`columns` fragments and `klartex-footer.sty` rewritten to the mode string; the composition's page-number arm removed.
  - Step 9: the four goldens edited in place (the footer line only) rather than regenerated, since they are hand-held normalised files.
  - Step 10: `README.md`, `README.en.md` (a "Sidnummer"/"Page numbers" section each) and `CHANGELOG.md` under an `## Orealiserat` heading.
  - Step 11: `pytest -n auto` → 915 passed, 9 skipped (only the pre-existing "font family not available" skips; no xelatex or `test_server` skips). Manual renders through the repo code confirm the matrix, and the generated `_block` schema has no `page_numbers` at document level and the enum on both footer object forms.
- 2026-09-04: Branch `issue/67-page-numbers-auto-on-off` created from `main`. Starting step 1.
