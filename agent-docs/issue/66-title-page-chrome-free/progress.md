# Progress: Issue #66 — `title_page` should render a fully chrome-free page (no header, no footer)

## Status: Completed

Completed: 2026-09-04

(Update as work proceeds — newest entries first)

- Review fix (PR #112): a title block long enough to overflow printed the chrome again on its continuation pages, since `\thispagestyle` covers one page only. `\makedoctitle` now sets `\pagestyle{empty}` inside a group and ends with `\clearpage` before `\endgroup`, so every page of the block is bare and the surrounding style is restored afterwards. Locked by `test_a_title_block_spanning_pages_leaves_every_page_bare`; `CLAUDE.md` and the CHANGELOG fix entry restate the mechanism.
- Step 8: `pytest -n auto` green — 932 passed, 9 skipped (only the pre-existing local font-availability skips in `test_renderer.py`; no xelatex or server skips). Manual render of `tests/fixtures/avtal_block.json`: page 1 carries only the title block, page 2 carries the footer `Konsultavtal • Sida 2 av 3`.
- Step 7: `README.md`, `README.en.md` (drop `first_page_header`, add the title-page sentence), `CLAUDE.md` (`DOCUMENT_SETTINGS` list, composition order, `\makedoctitle` sentence in the LaTeX-layer section), `CHANGELOG.md` (breaking change + fix under `## Orealiserat`).
- Step 6: `TestTitlePageChrome` added to `tests/test_block_engine.py` — two source-level cases and five `pdftotext` cases (predefined slots, `columns` footer, per-slot custom sources, whole-page source, mid-document title page).
- Step 5: `first_page_header` removed from / rewritten in `tests/test_page_templates.py`, `tests/test_block_engine.py`, `tests/test_schemas.py`.
- Step 4: `tests/fixtures/golden/page_template_empty_header.tex` lost its two `plain` lines.
- Step 3: `first_page_header` removed from `DOCUMENT_SETTINGS`, `PageTemplate`, `load_page_template` and the module docstring in `klartex/page_templates.py`.
- Step 2: composition step 5 removed from `klartex/templates/_page_template.tex.jinja`.
- Step 1: `\clearpage\thispagestyle{empty}` at the start of `\makedoctitle`, `\thispagestyle{fancy}` removed, header comment updated in `klartex/cls/klartex-titelsida.sty`.
- Step 0: branch `issue/66-title-page-chrome-free` created from `main`; plan read.
