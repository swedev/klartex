# Plan: Issue #37 — Page template assets resolve relative to cwd instead of the template's directory

> **Round 2 (reopened).** Round 1 landed in PR #38 (merged, commit `9d3e7d2`): the CLI now derives `asset_dir` from the page-template file's directory and `render()` puts it on `TEXINPUTS`, so assets referenced by *plain name* (`\includegraphics{logo.pdf}`, `\input{brand-colors}`) resolve next to the template. The issue was reopened because *explicitly relative* names (`./logo.pdf`, `../shared.tex`) still fail: Kpathsea never searches `TEXINPUTS` for names starting with `./` or `../` — it tries them as-is against xelatex's working directory, which is the private tempdir `_compile_tex` compiles in. This was verified empirically in the unresolved review thread on PR #38 and is currently locked as a documented limitation by `tests/test_renderer.py::test_explicitly_relative_asset_path_is_not_searched`.

## Goal

Explicitly relative asset paths inside a page template (`\includegraphics{./logo.pdf}`, `\input{../shared/colors.tex}`) must resolve relative to the template's directory, completing the issue's "Expected" behavior. After this round, *any* relative asset reference — plain or `./`-prefixed — works when the template and its assets live together in one canonical place and are used from any cwd.

## Approach

**Give xelatex a meaningful working directory instead of the tempdir.** Kpathsea's handling of explicitly relative names is not configurable via search paths — the only base directory they ever resolve against is the compiling process's cwd. So `_compile_tex` changes from "run in tmpdir" to "run in the asset root, write output to tmpdir":

- Compute `asset_root = Path(asset_dir).resolve()` when `asset_dir` is given, else the caller's cwd.
- Run xelatex with `cwd=asset_root`, passing `-output-directory=<tmpdir>` and the `.tex` file as an **absolute** path (`tmp / "document.tex"`; jobname stays `document`).
- Build artifacts (`.aux`, `.log`, `.pdf`) land in tmpdir via `-output-directory`. TeX Live also searches the output directory for input files, so the second run finds the `.aux` from the first; the tempdir goes on `TEXINPUTS` explicitly as belt-and-braces (see next point).
- **Preserve search precedence for plain names:** today's `TEXINPUTS` starts with `.`, which meant tmpdir. After the cwd change `.` would mean the asset root and be searched *before* the bundled `cls/`, letting a template-dir file accidentally shadow a `.sty`/`.cls`. Fix by replacing the leading `.` with the absolute tmpdir: `TEXINPUTS = f"{tmp}:{CLS_DIR}:{asset_part}{cwd}:{existing}"`. Search order for plain names is then *identical* to today: tmpdir → cls → asset_dir → caller cwd.

**Resulting semantics (document these exactly, incl. in the `render()` docstring):**

- Plain names: unchanged search order — the full chain is tmpdir → bundled `cls/` → `asset_dir` → caller cwd → inherited/default `TEXINPUTS`; among the *user-controlled* roots that means template dir first, caller cwd as fallback.
- Explicitly relative names: resolve against exactly one base — the template's directory when an external template is in use (`asset_dir` set), otherwise the caller's cwd. No fallback chain; that is the nature of a single process cwd, and it is predictable.
- `../` now works too, e.g. `Branding/vastkustens.tex.jinja` referencing `\input{../shared/colors.tex}`.
- A `./` reference inside a *nested* included file still resolves against the single asset root, not the nested file's own directory — worth one sentence in the docstring so nobody expects per-file bases.

**Default-case change (deliberate):** when `asset_dir` is `None`, xelatex's cwd becomes the *caller's cwd* instead of the tempdir. This makes `./x` references in e.g. raw `latex` blocks resolve against the working directory — consistent with the pre-#38 "assets resolve relative to cwd" model — rather than failing mysteriously against a tempdir. Read access to cwd already existed via the `TEXINPUTS` cwd entry, so this exposes nothing new; writes are redirected by `-output-directory`. (Conservative alternative — keep `cwd=tmpdir` when `asset_dir is None` — was rejected: it leaves the current confusing failure mode in place for the no-template case and splits the mental model in two.)

**Invalid `asset_dir` becomes fatal — validate it.** Today a bogus `asset_dir` is just a dead `TEXINPUTS` entry; with `cwd=asset_root` the subprocess would die with a raw `FileNotFoundError`. Raise a clear `ValueError` ("asset_dir is not a directory: …" — `.is_dir()` rejects both missing paths and existing plain files) in `_compile_tex`, **before** the `shutil.which("xelatex")` check, so the validation is testable without xelatex installed. The CLI always passes the parent of an existing file, so only API callers with a caller bug hit this — failing fast with a clear message is correct.

**No new write surface:** `-no-shell-escape` stays; `\openout`/aux/log writes go to `-output-directory` (the tempdir), not the template directory or cwd. A test asserts the template dir is byte-identical after a render.

**Rejected alternatives:**
- `\graphicspath{{<dir>/}}` injection — only covers `\includegraphics`, not `\input`/fonts, and still cannot express `../`; rejected already in round 1.
- Rewriting `./`-prefixed names in the template source before compiling — fragile text munging of user LaTeX, misses generated/nested references.

## Steps

1. **`klartex/renderer.py::_compile_tex`** — implement the cwd change:
   - `asset_root = Path(asset_dir).resolve() if asset_dir is not None else Path(os.getcwd())`; raise `ValueError("asset_dir is not a directory: …")` if `asset_dir` was given and `asset_root` is not a directory — placed **before** the `shutil.which("xelatex")` check.
   - `subprocess.run([... , "-output-directory", tmpdir, str(tex_path)], cwd=asset_root, ...)` (tex file by absolute path).
   - `TEXINPUTS`: replace the leading `.` with the absolute tempdir so precedence stays tmpdir → cls → asset_dir → cwd → inherited. Keep the explicit `asset_part` and `cwd` entries (plain-name fallback chain unchanged).
   - Update the comment block explaining the mechanism: cwd carries explicitly relative names, `TEXINPUTS` carries plain names.
2. **`klartex/renderer.py::render` docstring** — rewrite the `asset_dir` paragraph: explicitly relative names (`./`, `../`) now resolve against `asset_dir` (or cwd when unset) with no fallback chain; plain names keep the full search order (tmpdir → cls → asset_dir → cwd → inherited `TEXINPUTS`); `./` inside nested included files resolves against the single asset root, not the nested file's directory.
3. **`klartex/cli.py`** — trim the `--page-template` help: drop "Reference them by plain name (logo.pdf) — a ./ or ../ prefix is not searched for." and state that both plain and `./`/`../` relative references resolve against the template's directory (plain names fall back to cwd; `./`/`../` do not).
4. **`tests/test_renderer.py`** — replace `test_explicitly_relative_asset_path_is_not_searched` (it locks the now-removed limitation) with tests for the new behavior:
   - `./brand-colors` resolves via `asset_dir` (the inverted assertion of the old test — this is the discriminating test; it fails on current `main`).
   - `../`-reference: `asset_dir=tmp_path/"branding"`, asset at `tmp_path/"shared"/…`, template does `\input{../shared/…}` → succeeds.
   - `asset_dir=None` + `monkeypatch.chdir(tmp_path)`: `./brand-colors` resolves against the caller's cwd (locks the deliberate default-case change).
   - No-artifacts guard: recursive snapshot of *relative path → file bytes* (not just `os.listdir` — that would miss modified files) before/after a render → identical. Two variants: (a) `asset_dir` set, protecting the template dir; (b) `asset_dir=None` with `monkeypatch.chdir`, protecting the caller cwd, since that too becomes xelatex's cwd.
   - Invalid `asset_dir` → `ValueError` matching "not a directory" (fast, no xelatex — validation precedes the xelatex-presence check). Two cases: a missing path and an existing plain file.
   - Invocation-shape test (fast, monkeypatched `subprocess.run` returning a fake success + fake PDF): both xelatex calls use the same absolute `.tex` path, `cwd=asset_root`, `-output-directory=<tmpdir>`, and `TEXINPUTS` ordered tmpdir → cls → asset_dir → cwd.
   - Two-pass regression (xelatex): a fixture that is genuinely two-run-sensitive (body with a `latex` block using `\label`/`\pageref`); wrap `subprocess.run` with a delegating spy and assert `document.aux` exists in the tempdir after the first run — proving `-output-directory` receives the aux and the second run can find it. (Existing tests only assert the `%PDF-` signature, which would not catch unresolved `??` references.)
   - Keep `test_render_resolves_asset_dir` and `test_render_resolves_relative_asset_dir` as-is — they must still pass (plain-name path and relative-`asset_dir` resolution are unchanged).
5. **`tests/test_cli_page_template.py`** — extend `TestAssetDirEndToEnd` with the reopened repro using the issue's actual primitive: template in `tmp_path/branding/` referencing a sibling **via `\includegraphics{./logo.pdf}`** (a tiny PDF asset, generated once by a helper `render()` call or a minimal checked-in fixture), CLI invoked from a different cwd with `--page-template` → exit 0, PDF written. The renderer-level tests cover `\input`; this covers the graphics path the issue reported. Verify the existing precedence test (`test_template_dir_takes_precedence_over_cwd`) still passes — the `TEXINPUTS` reorder must not change plain-name precedence.
6. **Docs** — update the round-1 wording that documents the limitation:
   - `README.md` (~line 105) and `README.en.md` (~line 105): replace the "Referera alltid filer med enbart namnet" / "Always reference files by plain name" blockquote — `./`/`../` now resolve against the template's directory (or cwd without a template dir); note the one asymmetry: explicitly relative references do not fall back to cwd. Keep each file's language.
   - `CLAUDE.md`: pipeline line 53 (`TEXINPUTS=.:cls:[asset_dir:]cwd` → new shape with tmpdir + the cwd=asset-root mechanism) and the page-templates section — rewrite the "Known limitation" paragraph (line 97) to describe the implemented cwd mechanism instead.
7. Run the full `pytest` suite (xelatex on PATH) and verify no regressions, in particular the round-1 CLI tests (`TestAssetDirKwarg`, `TestAssetDirEndToEnd`) and all other xelatex compilation tests, which now all compile with the new cwd/`-output-directory` invocation.

## Risks

- **Every render changes invocation shape** (cwd + `-output-directory`), not just template-using ones. The whole xelatex-tagged suite is the guard here; CI fails if any xelatex test is skipped, so a full green run is meaningful coverage.
- **Search-precedence regression risk:** if the leading `.` in `TEXINPUTS` were kept, the asset root would be searched before the bundled `cls/`, letting template-dir files shadow class/style files. The plan replaces `.` with the absolute tmpdir precisely to keep today's order; the existing precedence test plus the full suite guard it.
- **Second-run `.aux` discovery** relies on TeX Live searching `-output-directory` for input files. This is standard, documented TeX Live behavior (latexmk depends on it daily), and tmpdir is additionally on `TEXINPUTS` — but existing tests only assert the `%PDF-` signature and would not catch unresolved `??` references, so the dedicated two-pass test in step 4 (aux-in-tempdir spy on a `\label`/`\pageref` fixture) is the actual guard.
- **API callers with an invalid `asset_dir`** (missing path or plain file) previously got a silent no-op search entry, now a `ValueError`. This is a behavior change for a caller bug; the clear error is strictly more debuggable. Worth a line in the eventual CHANGELOG entry.
- **Caller cwd disappears mid-process** (deleted directory): `subprocess.run(cwd=...)` would fail. Today's code already calls `os.getcwd()` and would raise in the same situation, so no regression.
- CHANGELOG is updated at release time per the release process in CLAUDE.md — not part of this change's PR. The entry should mention: `./`/`../` resolution, the default-cwd change, and the nonexistent-`asset_dir` error.

## Test Plan

- **Discriminating test:** `./brand-colors` via `asset_dir` — fails on current `main` (locked as failing by the old limitation test), passes with the fix.
- New renderer tests: `../` parent reference, `./` against caller cwd when `asset_dir=None`, recursive byte-identical guard for both the template dir and the caller cwd, invalid `asset_dir` (missing path + plain file) → `ValueError`, invocation-shape test (mocked subprocess), two-pass aux-discovery test (delegating spy + `\pageref` fixture).
- New CLI end-to-end test: the reopened repro — template + PDF logo in `branding/`, `\includegraphics{./logo.pdf}`, built from another cwd via `--page-template`.
- Regression guards: `test_render_resolves_asset_dir`, `test_render_resolves_relative_asset_dir`, `TestAssetDirKwarg`, `TestAssetDirEndToEnd` (incl. plain-name precedence) all unchanged and green.
- Full `pytest` run with xelatex on PATH — every compilation test now exercises the new invocation.
