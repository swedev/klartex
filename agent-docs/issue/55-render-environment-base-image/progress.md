# Progress: Issue #55 — Own the render environment: publish the TeX Live base image and test inside it

## Status: PR 2 implemented on `issue/55-render-environment-base-image-r2` — not committed, awaiting review

(Update as work proceeds — newest entries first)

## 2026-08-28 — PR #57 review feedback addressed

- `publish.yml` tees the pytest log to `/tmp/test-output.txt` instead of the workspace root, and the xelatex skip guard greps that path. Reviewer finding, verified locally: hatchling's sdist packs the checkout, and `test-output.txt` matches neither `.gitignore` (`*.log`/`*.out`, no `.txt`) nor `[tool.hatch.build].exclude`, so a build after the test step shipped `klartex-0.15.0/test-output.txt` inside the PyPI tarball. This mirrors what `base-image.yml`'s self-test already does. `ci.yml` tees to the workspace root as before — it builds no package, so nothing is packed there.

## 2026-08-28 — PR 2 implemented (release gate in `publish.yml`)

Branch `issue/55-render-environment-base-image-r2`, cut from current `main` because the round-1 branch carries merged PR #56.

Plan step 8 done:

- [x] `.github/workflows/publish.yml` rewritten as the release gate. The `build` job runs in `container: ghcr.io/swedev/klartex-base:20260828-3@sha256:b011056413d449bdc41b893ff1bd538a2be46d78d3794698eb134f45936d6ff2` with `credentials:` from `GITHUB_TOKEN`, `timeout-minutes: 20`, `KLARTEX_REQUIRE_GEORGIA: "1"` at job level. Steps: checkout, `apt-get update` + `poppler-utils`, venv at `/tmp/venv` with absolute-path invocation throughout, `pytest -v -rs --tb=short | tee` under `shell: bash`, a separate xelatex no-skip grep step matching `ci.yml`'s shape, `python -m build`, artifact upload. The apt TeX Live install is gone. `permissions:` gains `packages: read`; `on:` gains `workflow_dispatch`; the `publish` job gains `if: github.event_name == 'release'` so dispatch runs stop after the build.
- [x] Release-gate paragraph added to the "Färdig renderingsmiljö" / "Ready-made render environment" section of `README.md` and `README.en.md`.
- [x] `CLAUDE.md`: the render-environment paragraph now names `publish.yml` as a pin consumer and as the release gate; the release checklist's step 4 says the suite runs inside the pinned image before the package is built.

Verification (plan's PR 2 review checks):

- [x] Pin confirmed against run 33190682385, not just the packages API: its push step logs `exporting manifest list sha256:b011056…` and `pushing manifest for ghcr.io/swedev/klartex-base:20260828-3@sha256:b011056…`, so the pinned digest is the index digest, and the ghcr versions API shows tag `20260828-3` resolving to it.
- [x] `publish.yml` parses as YAML; `actionlint` reports no findings.
- [x] `permissions` includes `packages: read`; `publish` carries `if: github.event_name == 'release'`.
- No Python or LaTeX sources changed, so the local suite is unaffected by this round.

Open point for review: `docker/Dockerfile.base` installs no `git`, so `actions/checkout@v4` inside the container falls back to the REST API tarball. That is a supported checkout path and hatchling reads a static `version` plus `.gitignore` from the filesystem, so the package build does not need a repository — but this is the one step of the gate that the base image's own self-test never exercises (it bind-mounts the workspace instead of checking out). The mandatory `workflow_dispatch` dry run covers it.

Remaining (plan steps 9–10):

- Open PR 2 (`Closes #55`) against `main`, noting run 33190682385 as the pin's source.
- After merge, trigger the `workflow_dispatch` dry run of `publish.yml` and confirm `build` is green and `publish` skipped, before closing #55.
- Ask the user before filing the `swedev/klartex.se` cleanup tracking issue.

## 2026-08-28 — PR 1 merged (#56), first base image published, PR 2 unblocked

- PR #56 merged to `main` (commit 783cf01). The path-filtered `pull_request` self-test leg of `base-image.yml` ran green pre-merge.
- First push-triggered `base-image.yml` run on `main` (33190682385): success — in-image self-test passed, multi-arch push done.
- Published: `ghcr.io/swedev/klartex-base:20260828-3`, index digest `sha256:b011056413d449bdc41b893ff1bd538a2be46d78d3794698eb134f45936d6ff2` (per the packages API; confirm against the run's step summary before pinning).
- The ghcr package is **public** — the manual visibility prerequisite for PR 2 is already met.
- Plan updated to now-state: steps 1–7 done, remaining work is PR 2 (`publish.yml` container gate + README release-gate sentence deferred from PR 1), the post-merge `workflow_dispatch` dry run, and the `swedev/klartex.se` tracking issue (user approval first).

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
