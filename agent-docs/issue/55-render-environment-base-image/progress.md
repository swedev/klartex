# Progress: Issue #55 — Own the render environment: publish the TeX Live base image and test inside it

## Status: PR 1 implemented (PR 2 blocked on PR 1 being merged and published)

(Update as work proceeds — newest entries first)

## 2026-08-28 — PR 1 complete on `issue/55-render-environment-base-image`

Plan steps 1–6 done:

- [x] 1. `docker/Dockerfile.base` — moved from `swedev/klartex.se` `backend/Dockerfile.base`, header comments rewritten for this repo, `ARG TEXLIVE_REF` parameterisation, OCI source/licenses/description labels. python3/pip/venv/curl layer, mscorefonts layer, texlive-bin symlink and sanity check unchanged. No test-only packages baked in.
- [x] 2. `.github/workflows/base-image.yml` — push/PR/dispatch with path filters, checkout, env-passed grammar-validated tag, QEMU/buildx, login skipped on `pull_request`, upstream digest resolved once and passed to both builds, amd64 `load` build tagged `klartex-base:selftest`, in-image suite (strict mode, `apt-get update` + poppler-utils, venv with absolute paths, `PATH` export, `KLARTEX_REQUIRE_GEORGIA=1`, `pytest -rs`, xelatex no-skip grep), then push-only multi-arch push and pin report to the step summary.
- [x] 3. `test_header_font_georgia_renders` in `tests/test_renderer.py` — `fc-list` probe, `KLARTEX_REQUIRE_GEORGIA` override, `%PDF-` + size assertions. Skip reason avoids the word "xelatex" so `ci.yml`'s guard is untouched.
- [x] 4. `ci.yml` test step: `shell: bash` (pipefail) and `-rs` on pytest.
- [x] 5. `README.md`, `README.en.md` (consumer section + apt set reframed as the per-push approximation) and `CLAUDE.md`.
- [x] 6. `pytest` locally: 335 passed, 0 skipped — the Georgia test executes on this machine (mactex + system Georgia). Verified separately that a missing font makes `render()` fail, so `KLARTEX_REQUIRE_GEORGIA=1` on a Georgia-less machine yields a failure rather than a skip. Workflow YAML parses. Local `docker build` not run (daemon not running; optional in the plan).

Deviation from the plan, flagged for review: the README consumer section describes the base image and its in-image self-test but **not** the release gate. The gate does not exist until PR 2 lands, and the READMEs are written in now-state. The release-gate sentence moves into PR 2 together with the `publish.yml` rewrite.

Remaining (plan steps 7–10), all gated on PR 1 being merged:

- Watch the first `base-image.yml` run; copy tag + digest from the step summary.
- Ask the user to make the `ghcr.io/swedev/klartex-base` package public.
- PR 2: `publish.yml` container gate pinned to that tag + digest, `packages: read`, `workflow_dispatch` + `if: github.event_name == 'release'` on `publish`, `timeout-minutes: 20`; then the mandatory dry run.
- Ask the user before filing the `swedev/klartex.se` cleanup tracking issue.
