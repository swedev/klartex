# Progress: Issue #98 — Letterhead columns overflow on a single unbreakable token

## Status: Completed (2026-09-02)

(Update as work proceeds — newest entries first)

- **Step 7 — full suite.** `pytest -rs` (sequential): 765 passed, 9 skipped. Every skip is `font family '<X>' not available to the TeX engine` (test_renderer.py:1143) — a local OS-font gap, not an xelatex-tagged or `test_server` skip. `tests/test_server.py` runs green (75 passed). `ruff check` reports the same six pre-existing errors as on `main`.
- **Step 6 — docs.** `README.md` and `README.en.md`: one clause after the `logo` sentence in the letterhead notes. `CLAUDE.md`, Page templates: the `Field` sentence now names `breaks_after` and `allow_breaks`.
- **Manual check.** Rendered the issue's payload (`Brf Ekbacken`, the long email, the long `www.` address, an address and a phone). No `Overfull \hbox` in the xelatex log; every contact word ends at xMax ≤ 329.02 against the 331.65 column edge; the seven-line header's last line ends at y = 88.84, above the heading at y = 93.70. fancyhdr's `\headheight is too small` warning is logged, as D6 anticipated, and does not fail the run.
- **Step 5 — goldens.** `TestPageTemplateGoldens` and `test_faktura_preamble_unchanged_from_golden` pass unchanged.
- **Step 4 — render tests.** `tests/test_pdf_text_layer.py`: `_word_boxes()` returns all first-page words as `(xMin, yMin, xMax, yMax, text)` and `_word_box()` is now a wrapper over it. Module constants `_A4_WIDTH_PT`, `_SIDE_MARGIN_PT`, `_CONTACT_LEFT_PT`, `_CONTACT_RIGHT_PT` derive the column edges from the fragment's 0.30/0.03/0.25 split. `test_a_long_letterhead_address_wraps_inside_the_contact_column` is parameterized over the issue's email, the `www.` address and the `https://…/styrelsen` URL: every header word's xMax stays inside the column, and the contact words rejoin to the address exactly. `test_the_tallest_realistic_contact_column_clears_the_page_and_the_body` pins D6. Negative control: with `CONTACT_BREAKS = ""` the three horizontal cases fail (the URL measures xMax 410.4 against the 331.7 edge).
- **Step 3 — schema description.** `tests/test_schemas.py::test_letterhead_address_fields_document_where_they_wrap` asserts the "may wrap after @, . and /" clause reaches the generated schema for both fields; the structure tests strip descriptions, so nothing else covers it.
- **Step 2 — unit tests.** `tests/test_page_templates.py::TestAddressBreaks`: breaks after each run of separators, nothing after a trailing run, escape sequences intact, identity for an empty separator set, `header_macros` annotating `web`/`email` only, and the shared `LOGO` field left verbatim.
- **Step 1 — slot model.** `klartex/page_templates.py`: `Field.breaks_after`, the pure `allow_breaks()`, the `CONTACT_BREAKS = "@./"` constant on the letterhead's `web` and `email` (descriptions extended), and `header_macros` applying it.
- Started. Branch `issue/98-letterhead-columns-overflow-unbreakable-token` from `main`.
