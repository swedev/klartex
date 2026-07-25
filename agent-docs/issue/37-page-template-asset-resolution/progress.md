# Progress: Issue #37 — Page template assets resolve relative to cwd instead of the template's directory

## Status: Round 2 completed (2026-07-25)

Round 1 (PR #38, merged) is logged at the bottom. Round 2 scope — explicitly
relative asset paths (`./`, `../`) — is planned in [plan.md](plan.md).

**Round 2 branch:** `issue/37-page-template-asset-resolution` (from `main`)

(Update as work proceeds — newest entries first)

## Round 2 steps

- [x] 1. `klartex/renderer.py::_compile_tex` — `asset_root` + `ValueError` validation (before the `shutil.which` check), `cwd=asset_root`, `-output-directory`, `TEXINPUTS` reorder (leading `.` → absolute tempdir); `import os` moved to module level
- [x] 2. `klartex/renderer.py::render` docstring — `asset_dir` paragraph rewritten: two mechanisms (plain names via TEXINPUTS chain, `./`/`../` via cwd), no fallback for explicitly relative names, nested-file note, no-artifacts note
- [x] 3. `klartex/cli.py` — `--page-template` help text: both name shapes resolve against the template dir; only plain names fall back to cwd
- [x] 4. `tests/test_renderer.py` — limitation test replaced; added `./` via asset_dir, `../` above asset_dir, `./` against cwd when `asset_dir=None`, two recursive byte-level no-artifacts guards, `ValueError` (missing path + plain file), invocation-shape test (fake subprocess), two-pass aux-discovery spy, plus a shadowing guard (see note below)
- [x] 5. `tests/test_cli_page_template.py` — `test_explicitly_relative_logo_resolves_from_other_cwd` using `\includegraphics{./logo.pdf}`
- [x] 6. Docs — `README.md`, `README.en.md`, `CLAUDE.md` (pipeline line + page-templates section rewritten)
- [x] 7. Full `pytest` run — 257 passed, no skips (round 1 was 246; 11 new tests)

### Round 2 verification notes

Discriminating tests confirmed to fail without the fix. With `cwd=tmpdir`
restored in `_compile_tex` (everything else unchanged), these four fail:

- `test_explicitly_relative_asset_path_resolves_via_asset_dir`
- `test_parent_relative_asset_path_resolves_above_asset_dir`
- `test_explicitly_relative_path_falls_back_to_cwd_without_asset_dir`
- `test_xelatex_invocation_shape`

**One addition beyond the plan's step list.** The plan's risk section assumed
the existing precedence test (`test_template_dir_takes_precedence_over_cwd`)
guarded the `TEXINPUTS` reorder. It does not — that test's discriminator is a
`brand-colors.tex` that never exists in `cls/`, so it passes either way.
Verified empirically: with the leading entry flipped back from the absolute
tempdir to `.`, a `klartex-callout.sty` planted in `asset_dir` *does* shadow
the bundled package, and the full suite stays green. Added
`test_asset_dir_cannot_shadow_bundled_sty` to close that gap — it renders a
`callout` block with a decoy `klartex-callout.sty` in `asset_dir` whose
`\input` target is missing (fatal even under `-interaction=nonstopmode`), so a
successful compile proves the bundled package won.

## Round 1 (completed 2026-07-25, PR #38)

- [x] 1. `klartex/cli.py` — `asset_dir` initialized next to `page_template_source`; set to `pt_path.resolve().parent` in the explicit `--page-template` branch and `auto.resolve().parent` in the auto-detect branch; passed to `render()`
- [x] 2. `klartex/cli.py` — `--page-template` help text notes template-dir asset resolution, cwd fallback, and the symlink-target contract
- [x] 3. `klartex/renderer.py::_compile_tex` — `asset_part` built from `Path(asset_dir).resolve()`; `render()` docstring documents relative-path resolution and that `page_template_source` callers must pass `asset_dir` themselves
- [x] 4. Fast CLI tests (`TestAssetDirKwarg`, monkeypatched `klartex.cli.render`) — explicit absolute, explicit relative, sibling auto-detect in subdir, cwd-default auto-detect, no-template → `None`
- [x] 5. xelatex end-to-end tests (`TestAssetDirEndToEnd`) — issue repro, cwd fallback, template-dir precedence
- [x] 6. `tests/test_renderer.py::test_render_resolves_relative_asset_dir` — relative `asset_dir` under `monkeypatch.chdir`
- [x] 7. Docs — `README.md` / `README.en.md` split CLI vs API asset resolution; `CLAUDE.md` pipeline `TEXINPUTS` line and page-templates section refreshed
- [x] 8. Full `pytest` run — 246 passed, no skips

### Round 1 verification notes

Both discriminating tests were confirmed to fail without the fix:

- With `asset_dir=None` forced in `cli.py`, `test_asset_next_to_template_resolves_from_other_cwd` and `test_template_dir_takes_precedence_over_cwd` fail.
- With the `Path(asset_dir).resolve()` hardening reverted, `test_render_resolves_relative_asset_dir` fails.

The precedence test needed strengthening during implementation: the first version used an undefined color as the discriminator, which `-interaction=nonstopmode` compiles through with only a warning. It now uses a same-named asset copy containing a missing `\input` target, which is fatal even in nonstopmode, so a successful compile proves the template-dir copy won.

## Notes

- CHANGELOG is intentionally not updated here — per `CLAUDE.md` that happens at release time. Round 2 entry should mention: `./`/`../` resolution, the default-cwd change, and the `ValueError` on a nonexistent `asset_dir`.
