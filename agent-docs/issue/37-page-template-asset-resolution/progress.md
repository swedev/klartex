# Progress: Issue #37 — Page template assets resolve relative to cwd instead of the template's directory

## Status: Completed

**Completed:** 2026-07-25
**Branch:** `issue/37-page-template-asset-resolution` (from `main`)

(Update as work proceeds — newest entries first)

## Steps

- [x] 1. `klartex/cli.py` — `asset_dir` initialized next to `page_template_source`; set to `pt_path.resolve().parent` in the explicit `--page-template` branch and `auto.resolve().parent` in the auto-detect branch; passed to `render()`
- [x] 2. `klartex/cli.py` — `--page-template` help text notes template-dir asset resolution, cwd fallback, and the symlink-target contract
- [x] 3. `klartex/renderer.py::_compile_tex` — `asset_part` built from `Path(asset_dir).resolve()`; `render()` docstring documents relative-path resolution and that `page_template_source` callers must pass `asset_dir` themselves
- [x] 4. Fast CLI tests (`TestAssetDirKwarg`, monkeypatched `klartex.cli.render`) — explicit absolute, explicit relative, sibling auto-detect in subdir, cwd-default auto-detect, no-template → `None`
- [x] 5. xelatex end-to-end tests (`TestAssetDirEndToEnd`) — issue repro, cwd fallback, template-dir precedence
- [x] 6. `tests/test_renderer.py::test_render_resolves_relative_asset_dir` — relative `asset_dir` under `monkeypatch.chdir`
- [x] 7. Docs — `README.md` / `README.en.md` split CLI vs API asset resolution; `CLAUDE.md` pipeline `TEXINPUTS` line and page-templates section refreshed
- [x] 8. Full `pytest` run — 246 passed, no skips

## Verification notes

Both discriminating tests were confirmed to fail without the fix:

- With `asset_dir=None` forced in `cli.py`, `test_asset_next_to_template_resolves_from_other_cwd` and `test_template_dir_takes_precedence_over_cwd` fail.
- With the `Path(asset_dir).resolve()` hardening reverted, `test_render_resolves_relative_asset_dir` fails.

The precedence test needed strengthening during implementation: the first version used an undefined color as the discriminator, which `-interaction=nonstopmode` compiles through with only a warning. It now uses a same-named asset copy containing a missing `\input` target, which is fatal even in nonstopmode, so a successful compile proves the template-dir copy won.

## Notes

- CHANGELOG is intentionally not updated here — per `CLAUDE.md` that happens at release time. The search-order change (an asset present both beside the template and in cwd now resolves to the template's copy) is worth a line in the eventual entry.
