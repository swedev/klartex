# Progress: Issue #85 — Reinstate the whole-page custom template: one file for the full design, plus autodetection

## Status: Completed (2026-08-31)

(Update as work proceeds — newest entries first)

- Step 9 — full suite `pytest -rs -n auto`: 687 passed, 9 skipped (pre-existing
  local font-availability skips only; no xelatex or `test_server` skips).
  User-shaped smoke check passes: data file + sibling `report.tex.jinja` + logo
  in one directory, rendered from another cwd, with both `{logo.png}` and
  `{./logo.png}`.
- Step 8 — docs: `CLAUDE.md` (page-template + HTTP sections), `README.md`,
  `README.en.md`.
- Step 7 — tests: `test_page_templates.py` (`TestWholePageSource`),
  `test_block_engine.py` (`TestWholePageTemplateSource` + conflict test),
  `test_renderer.py` (recipe forwarding, faktura footer/`page_numbers`
  precedence, xelatex end-to-end), `test_cli_page_template.py` (autodetect
  helper, flag, autodetection), `test_server.py` (field, conflict, size,
  surrogate, forwarding). Both `_render_*` helpers forward the argument.
- Step 6 — server: `page_template_source` on `RenderRequest` (D4).
- Step 5 — CLI: `--page-template`, `_autodetect_page_template()`, conflict and
  suppression rules, `asset_dir` from the template's resolved parent.
- Steps 1–4 — slot model (`shared_source`, loader argument, mutual exclusion),
  composition guard, engine plumbing, renderer keyword.
