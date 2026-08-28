# Progress: Issue #49 — A paragraph longer than a page does not break — it spills past the bottom margin

## Status: Completed

**Completed:** 2026-08-28

(Update as work proceeds — newest entries first)

## Steps

- [x] 1. Regression test `test_paragraph_longer_than_a_page_breaks_onto_next_page` added in `tests/test_pdf_text_layer.py`; `_text_layer` split into `_raw_text_layer` (untouched output, `\f` intact), `_text_layer` (normalized) and `_pages` (per-page, trailing empties dropped)
- [x] 2. Preservation test `test_widow_and_orphan_penalties_keep_the_two_line_policy` added, probing `\the\widowpenalties`/`\the\clubpenalties` at positions 1–3 through a raw `latex` block
- [x] 3. Both tests confirmed red against the unchanged class — regression test: marker missing from the last page; preservation test: position 3 read `10000`
- [x] 4. Fix applied in `klartex/cls/klartex-base.cls`: `\widowpenalties 3 10000 10000 0` / `\clubpenalties 3 10000 10000 0`, with a comment on why the terminating `0` is required
- [x] 5. Focused tests green (6 passed); full suite green (350 passed). Manual sanity: `block_kallelse` (1 page) and `block_arsredovisning` (2 pages) render to the same page counts as on `main`
- [ ] 6. CHANGELOG entry under `Fixes` — deferred to release time (releases are user-initiated)

## Notes

- Verified page counts of existing fixtures against `main` to check for layout drift: unchanged.
