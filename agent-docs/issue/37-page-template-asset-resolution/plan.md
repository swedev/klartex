# Plan: Issue #37 — Page template assets resolve relative to cwd instead of the template's directory

## Goal

A relative asset path inside an external page template (e.g. `\includegraphics{logo_vastkustens.pdf}`) must resolve relative to the template file's own directory, so a template plus its assets can live in one canonical place (e.g. a `Branding/` folder) and be referenced from any working directory via `--page-template`. Cwd resolution stays as a fallback so existing setups keep working.

## Approach

**The mechanism already exists — the CLI just doesn't use it.** `klartex.render()` gained an `asset_dir` parameter in v0.11.1 (see CHANGELOG): the directory is injected into `TEXINPUTS` between the bundled `cls/` dir and the caller's cwd (`renderer.py::_compile_tex`, line 270), exactly the search-path position the issue asks for. It is already covered by `tests/test_renderer.py::test_render_resolves_asset_dir`. The bug is confined to `klartex/cli.py::main`: it reads the page-template file's *text* (lines 82–93) and discards the *path*, then calls `render()` without `asset_dir` (line 106).

**Fix: derive `asset_dir` from the resolved page-template path** in all three file-based resolution branches:

1. Explicit `--page-template <path>` → `asset_dir = pt_path.resolve().parent` — this is the reported repro.
2. Auto-detected `<data-stem>.tex.jinja` next to the data file → `asset_dir = auto.resolve().parent` — fixes the same bug for data files rendered from a different cwd (`klartex -d docs/report.json` with `docs/report.tex.jinja` + `docs/logo.pdf`).
3. Auto-detected `./page_template.tex.jinja` in cwd → same expression; the parent is cwd, so this is a harmless no-op that keeps the code uniform.

When no external page template is used (built-in `formal`/`clean`/`none` from `data.page_template`), `asset_dir` stays `None` — unchanged behavior.

**Why `.resolve()` matters:** `_compile_tex` runs xelatex with `cwd=tmpdir`, so a *relative* `TEXINPUTS` entry would be interpreted relative to the tempdir and silently never match. `--page-template Branding/mall.tex.jinja` yields a relative parent, so the CLI must absolutize. As hardening, `_compile_tex` should also absolutize `asset_dir` itself so API callers can't fall into the same trap.

**Symlink contract (deliberate decision):** we use `pt_path.resolve().parent`, i.e. assets are searched next to the symlink *target*, not next to the symlink itself. Rationale: a symlinked template is a pointer into a canonical template bundle, and the bundle's assets live with the target. The alternative (`pt_path.parent.resolve()`) would break the bundle case while only helping the unusual "symlink into a foreign dir with local assets" case. Document this in the `--page-template` help/docstring.

**Scope note:** this fixes the CLI file-based paths only. The API's `page_template_source` parameter receives raw text with no file path, so API callers must keep passing `asset_dir` explicitly (unchanged, and documentation must not imply otherwise).

**Rejected alternative:** injecting `\graphicspath{{<dir>/}}` into the preamble. `TEXINPUTS` already covers `\includegraphics`, `\input`, and font files uniformly, is the mechanism `asset_dir` uses today, and requires no template-source manipulation.

## Steps

1. **`klartex/cli.py`** — in `main()`, initialize `asset_dir: Optional[Path] = None` next to `page_template_source`. In the explicit `--page-template` branch set `asset_dir = pt_path.resolve().parent`; in the auto-detect branch set `asset_dir = auto.resolve().parent`. Pass `asset_dir=asset_dir` to `render(...)` (line 106).
2. **`klartex/cli.py`** — extend the `--page-template` help text with a sentence noting that assets (logos etc.) referenced from the template are found relative to the template's directory, with cwd as fallback.
3. **`klartex/renderer.py::_compile_tex`** — harden: build `asset_part` from `Path(asset_dir).resolve()` instead of interpolating `asset_dir` verbatim, so relative paths from API callers also work. Update the `asset_dir` docstring in `render()` to mention that relative paths are resolved against the caller's cwd.
4. **Tests (fast, no xelatex)** — in `tests/test_cli_page_template.py`, add CLI-level tests using `typer.testing.CliRunner` (pattern from `tests/test_cli_errors.py`) with `klartex.cli.render` monkeypatched to capture kwargs (the mock must return PDF-like bytes, e.g. `b"%PDF-1.5 fake"`, so the CLI's output-write path completes):
   - explicit `--page-template /abs/dir/mall.tex.jinja` → `asset_dir == /abs/dir`;
   - explicit *relative* `--page-template branding/mall.tex.jinja` from a different cwd → `asset_dir` is absolute and points at `branding/`;
   - auto-detected sibling `<data-stem>.tex.jinja` in a subdirectory → `asset_dir` is the data file's directory;
   - auto-detected `./page_template.tex.jinja` in cwd → `asset_dir` is the resolved cwd;
   - no external template → `asset_dir is None`.
5. **Tests (xelatex, end-to-end)** — in `tests/test_cli_page_template.py`, guarded by the repo's existing `HAS_XELATEX` + `@pytest.mark.skipif` convention (see `tests/test_renderer.py`):
   - **Repro:** `tmp_path/branding/` contains a `.tex.jinja` that `\input`s (or `\includegraphics`-loads) a sibling asset; invoke the CLI via `CliRunner` from a different cwd with `--page-template`; assert exit code 0 and a PDF is written. Fails on current `main`, passes with the fix.
   - **Cwd fallback:** asset absent beside the template but present in cwd → render still succeeds (guards the promised fallback).
   - **Precedence:** same asset filename in both template dir and cwd → the template-dir copy wins (e.g. via an `\input` snippet that only compiles in one variant). Guards the observable search-order change listed under Risks.
6. **Renderer hardening test** — in `tests/test_renderer.py`, add a test that passes a *relative* `asset_dir` to `render()` from a controlled cwd (`monkeypatch.chdir`) and asserts success — this exercises the new `Path(asset_dir).resolve()` in `_compile_tex`, which neither the existing absolute-path test nor the CLI tests cover.
7. **Docs** — update `README.md` line 98 and the corresponding sentence in `README.en.md`, distinguishing the two surfaces so the wording does not overpromise for the API: (a) CLI file templates — assets are found relative to the template file's directory, with the working directory as fallback; (b) API `page_template_source` — raw text has no path, so callers pass `asset_dir` (otherwise cwd applies). Also refresh the stale descriptions in `CLAUDE.md` ("TEXINPUTS=.:cls:cwd" in the pipeline section and "Logos resolve via TEXINPUTS" in the page-templates section). Keep README prose in each file's existing language.
8. Run `pytest` (full suite, xelatex required) and verify no regressions.

## Risks

- **Search-order behavior change:** a file that exists both next to the template *and* in cwd is now found in the template's directory first (asset_dir precedes cwd in `TEXINPUTS`). This is the intended semantics and matches the issue's "cwd as fallback", but it is technically observable for anyone relying on cwd shadowing. Risk: negligible; note it in the eventual CHANGELOG entry.
- **Symlinked template paths:** `.resolve()` follows symlinks, so assets are searched next to the symlink *target*, not the symlink itself. This is a deliberate product choice (see Approach), made in Python before TeX is involved — favors canonical template bundles referenced via symlink.
- CHANGELOG is updated at release time per the release process in CLAUDE.md — not part of this change's PR.

## Test Plan

- New fast tests in `tests/test_cli_page_template.py` assert the `asset_dir` kwarg for all three file-resolution branches (explicit absolute, explicit relative, sibling auto-detect, cwd-default auto-detect) plus the no-template case (monkeypatched `render`, no xelatex).
- New xelatex tests: (1) the issue's repro layout (template + asset in one dir, build from another cwd) — fails on current `main`, passes with the fix; (2) cwd fallback when the asset is only in cwd; (3) template-dir precedence when the asset exists in both places.
- New renderer test with a relative `asset_dir` exercises the `_compile_tex` hardening.
- Existing `test_render_resolves_asset_dir` guards the renderer half; existing `test_cli_page_template.py` auto-detect tests guard resolution priority.
- Full `pytest` run with xelatex on PATH.
