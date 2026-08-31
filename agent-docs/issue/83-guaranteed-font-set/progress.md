# Progress: Issue #83 — Guaranteed font set in the render environment, and a path for external fonts

## Status: Phase A complete (Phases B and C not started)

(Update as work proceeds — newest entries first)

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
