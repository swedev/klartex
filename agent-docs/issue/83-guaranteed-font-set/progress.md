# Progress: Issue #83 — Guaranteed font set in the render environment, and a path for external fonts

## Status: Phases A and B merged, Phase C implemented

(Update as work proceeds — newest entries first)

## 2026-08-31 — Phase C implemented on `issue/83-guaranteed-font-set-r3`

Steps 10–14 of the plan. Step 15 (CHANGELOG) belongs to the next release.

- `klartex/page_templates.py`: `FONT_FILENAME_PATTERN`, `FONT_FACE_OPTIONS`
  (the four keys mapped to their fontspec options), `_check_font`,
  `_fontspec_setup` and `font_files()`; `font` / `header_font` become
  `oneOf` [family name, file object] in `DOCUMENT_SETTINGS`, with the file
  form described once and reused by both; `PageTemplate.font_setup` /
  `.header_font_setup` emit the ready LaTeX.
- `klartex/templates/_page_template.tex.jinja`: emits those two properties in
  place of the inline `\setmainfont` / `\newfontfamily` blocks. The name form
  is byte-identical, so the golden preambles are untouched.
- `klartex/renderer.py`: `_resolve_asset_root()` factored out of
  `_compile_tex`, and `_preflight_font_files()` in `render()` — every
  referenced face must be a readable file in the asset root, else a
  `ValueError` naming the file and the contract, raised before the
  xelatex-presence check.
- `klartex/server/`: unchanged, as the plan expected — the faces ride the
  existing `assets` map and the preflight `ValueError` maps to the endpoint's
  structured 400.
- `README.md` / `README.en.md`: the file form documented beside the
  guaranteed set.

### Decisions carried out as planned

- Absent face key → no fontspec option → the regular face; nothing is
  synthesised. Stated in the schema description.
- File names carry no underscore, so the value survives `escape_data()`
  byte-identical; the tex-level tests assert the emitted command after
  escaping, which is what locks that.

### Deviation

- `FONT_FILENAME_PATTERN` ends `$(?![\s\S])` rather than plain `$`. Python's
  `$` also matches before a final newline, so `"Inter.ttf\n"` would otherwise
  satisfy jsonschema's `pattern`. Same guard, same reason, as
  `DIMENSION_PATTERN`.

### Verification

- `pytest -n auto`: 643 passed, 9 skipped (the guaranteed families macOS
  lacks — the same 9 as before this round).
- New coverage: loader validation of both forms and every rejected filename
  shape; the emitted fontspec commands (all four faces, regular only, header
  reuse, the two forms mixed); the preflight (missing regular face, missing
  optional face, cwd as asset root, invalid `asset_dir`); two xelatex
  round-trips using the Latin Modern OTF faces located with `kpsewhich`, so
  they run wherever the other compile tests do; three endpoint tests (a face
  sent through `assets` renders, a missing face is a structured 400 naming
  the file, and a name the endpoint's own `ASSET_NAME_RE` would accept is
  still rejected by the stricter font pattern).

## 2026-08-31 — Phase B implemented on `issue/83-guaranteed-font-set-r2`

Step 9 of the plan. Steps 10-14 (Phase C, the file form) remain, as a separate
PR; step 15 (CHANGELOG) belongs to the next release.

- Step 8 completed itself: merging PR #90 triggered `base-image.yml` on `main`
  (run 33431438070). Its self-test ran the full suite inside the freshly built
  amd64 image with `KLARTEX_REQUIRE_FONTS=1` — **621 passed, 0 skipped**, every
  `test_guaranteed_font_renders[...]` case among them, so the new base honours
  the guarantee `GUARANTEED_FONTS` promises.
- New pin, read from the run's `Report pin` step and cross-checked against the
  push log's manifest-list digest and the ghcr versions API (tag resolves to
  the same index digest):
  `ghcr.io/swedev/klartex-base:20260831-12@sha256:4dbabb8953ca8c307055d1130ecd642000140819b1e3b272f358eb08598dcb4e`
- `.github/workflows/publish.yml` (`container.image`, the release gate) and
  `docker/Dockerfile.render` (`FROM`) move to it in the same commit — the
  `image` job refuses to publish when those two diverge.

### Verification

- The `publish.yml` guard's own `sed` extraction, run over the working tree,
  reports identical pins for `Dockerfile.render` and the gate.
- `publish.yml` parses as YAML; no other file in the tree references the old
  pin (the remaining hits are historical plan documents under `agent-docs/`).
- Both READMEs cite the image as `<tag>@sha256:<digest>` placeholders, so no
  documentation needed the new value.
- No Python or LaTeX changed, so the suite is unaffected; the pin's real proof
  is the base-image self-test above, and the release gate re-runs it on the
  pinned image at the next release.

### Remaining coordination

- `swedev/klartex.se` gets the font guarantee only when it moves its own base
  pin to `20260831-12`.

## 2026-08-31 — PR #90 review feedback addressed

- `base-image.yml`: `docker/guaranteed-fonts.txt` added to both `paths`
  filters. Without it a change to the guaranteed set that needs no Dockerfile
  edit would trigger neither the PR-time self-test nor the post-merge rebuild,
  so the schema could promise a family no image build ever verified.
- `tests/test_renderer.py`: font availability is decided by the compile itself
  instead of by `fc-list`. On macOS the engine resolves fonts through Core
  Text, so fontconfig can report a family the engine cannot load; the render is
  attempted and only a fontspec "cannot be found" failure for that exact family
  turns into a skip. `KLARTEX_REQUIRE_FONTS=1` re-raises instead.

## 2026-08-31 — Phase A implemented on `issue/83-guaranteed-font-set`

Steps 1–7 of the plan are done. Steps 8–9 (Phase B, base-image pin bump) wait
on Phase A merging and `base-image.yml` publishing a new tag; steps 10–14
(Phase C, the file form) are a separate PR; step 15 (CHANGELOG) belongs to the
next release.

### Step 1 — package list verified

Verified inside `ghcr.io/swedev/klartex-render:0.17.0`, which is built FROM the
currently pinned base (Debian forky):

- `fonts-crimson-pro` does not exist in forky, and no other Crimson package
  does either. **Crimson Pro is dropped** from the guaranteed set; EB Garamond,
  Noto Serif and IBM Plex Serif carry the text-serif slot.
- `fonts-inter` ships static OTF faces (not only a variable font), so Inter
  stays.
- The remaining packages install and every proposed family appears as an exact
  name in `fc-list : family`.
- Finding: all the open families already resolve in the base image *without*
  the Debian packages — TeX Live's `texmf-dist` fonts are on fontconfig's path
  in `texlive/texlive`. The packages are kept anyway (as the plan specifies):
  they make the guarantee independent of an upstream image detail that could
  change, at a cost of tens of MB on a ~7 GB image.

### Steps 2–7 — code, schema, image, tests, workflows, docs

- `klartex/page_templates.py`: `GUARANTEED_FONTS` (16 families) plus rewritten
  `font` / `header_font` descriptions generated from it.
- `docker/guaranteed-fonts.txt`: the list in a form the image build can read
  before klartex is installed; locked to the constant by a test.
- `docker/Dockerfile.base`: the seven font packages, and an exact-match check
  over every guaranteed family replacing the two `grep -qi` checks.
- `tests/test_renderer.py`: `test_guaranteed_font_renders` parametrized over
  `GUARANTEED_FONTS`, gated by `KLARTEX_REQUIRE_FONTS`.
- `tests/test_schemas.py`: schema-description lock and Dockerfile-list lock.
- `.github/workflows/{base-image,publish}.yml`: `KLARTEX_REQUIRE_GEORGIA` →
  `KLARTEX_REQUIRE_FONTS`.
- `README.md` / `README.en.md`: the guaranteed families and the pointer to the
  schema descriptions as the authoritative list.

### Verification

- `pytest -n auto`: 612 passed, 9 skipped (the families macOS lacks).
- All 16 families render with `KLARTEX_REQUIRE_FONTS=1` inside the render
  image with the new packages installed — no skips.
- The Dockerfile check was build-tested both ways: it passes against the image
  as built, and fails the build when a family is missing from `fc-list`.
