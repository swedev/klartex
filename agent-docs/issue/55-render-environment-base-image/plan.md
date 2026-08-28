# Plan: Issue #55 — Own the render environment: publish the TeX Live base image and test inside it

## Goal

The environment klartex renders correctly in gets a single owner: this repository. Previously two definitions existed — the apt list in `.github/workflows/ci.yml`/`publish.yml` here, and `backend/Dockerfile.base` in `swedev/klartex.se` (built on `texlive/texlive:latest` + Microsoft core fonts, published as `ghcr.io/swedev/klartex-se-base`). The suite passed in an environment nobody renders in, which is how the Georgia-font 500 (`swedev/klartex.se#13`) escaped: the emit-only assertion in `tests/test_renderer.py` never rendered with Georgia, because Georgia is not in the apt CI environment.

Deliverables, split across two PRs:

**Landed with PR #56 (merged to `main` 2026-08-28):**

- `docker/Dockerfile.base` — the moved base image, comments rewritten for this repo, `ARG TEXLIVE_REF` parameterisation, OCI source/licenses labels; python3/pip/venv/curl layer, mscorefonts layer, texlive-bin symlink and build-time sanity check kept. No test-only packages baked in (`poppler-utils` is installed transiently at test time — the image stays production-faithful).
- `.github/workflows/base-image.yml` — builds on changes to the Dockerfile or itself, **runs the full klartex test suite inside the freshly built amd64 image before pushing** (strict shell mode, venv with absolute paths, `PATH` export for `/usr/local/texlive-bin`, `KLARTEX_REQUIRE_GEORGIA=1`, xelatex no-skip grep); a path-filtered `pull_request` leg gives pre-merge validation; upstream `texlive/texlive:latest` is digest-resolved once and passed to both builds so the tested amd64 image is provably the pushed one; pin (`tag@digest`) reported to the step summary. Published as `ghcr.io/swedev/klartex-base`, date tag + run number, no `latest`.
- `test_header_font_georgia_renders` in `tests/test_renderer.py` — the concrete "next Georgia" catcher: renders with `header_font: "Georgia"` through the full pipeline, skips where mscorefonts are absent (skip reason avoids the word "xelatex" so `ci.yml`'s skip guard is untouched), and `KLARTEX_REQUIRE_GEORGIA=1` turns the skip into a hard failure in both in-image runs.
- `ci.yml` pipefail fix (`shell: bash`) and `-rs` on pytest; the apt list stays as fast per-push approximation (user decision, issue Provenance section).
- README (`README.md` + `README.en.md`) consumer section for the image and the apt set reframed as the per-push approximation; `CLAUDE.md` note on the image and the pin-bump-by-PR mechanism.

**First build after merge (run 33190682385, success):** published `ghcr.io/swedev/klartex-base:20260828-3`, index digest `sha256:b011056413d449bdc41b893ff1bd538a2be46d78d3794698eb134f45936d6ff2` (verify against the run's step summary before pinning). The ghcr package is **public** (verified via the packages API), so the pull-auth prerequisite for PR 2 is met.

**Remaining — PR 2 (`Closes #55`):**

- `publish.yml` release gate: the `build` job runs inside the pinned base image before the package is built, so nothing reaches PyPI that has not passed in the production environment. The pin lives in the workflow file and is bumped by PR.
- A `workflow_dispatch` dry run of the gate, run once after merge and before closing #55.
- The release-gate sentence in both READMEs (deferred from PR 1 because the gate did not exist yet and the READMEs are written in now-state).

Out of scope for this repo's PRs: the `swedev/klartex.se` cleanup (delete `backend/Dockerfile.base` + `backend-base.yml`, repoint the `FROM` pin) — listed under Migration below as coordinated follow-up in that repo, tracked by an issue there.

## Approach

### 1. `publish.yml` — release gate inside the pinned base (PR 2, the active work)

Restructure the `build` job to run **in the pinned base image** instead of installing the apt TeX list:

```yaml
on:
  release:
    types: [published]
  workflow_dispatch:        # dry run of the gate, no publish

permissions:
  contents: read
  packages: read            # container image pull
  id-token: write

jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    container:
      image: ghcr.io/swedev/klartex-base:20260828-3@sha256:b011056413d449bdc41b893ff1bd538a2be46d78d3794698eb134f45936d6ff2
      credentials:
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    env:
      KLARTEX_REQUIRE_GEORGIA: "1"
    steps:
      - checkout
      - name: Install test-only deps
        run: apt-get update && apt-get install -y --no-install-recommends poppler-utils
      - name: Install project
        run: python3 -m venv /tmp/venv && /tmp/venv/bin/pip install .[dev]
      - name: Run tests
        shell: bash                     # pipefail
        run: |
          export PATH=/usr/local/texlive-bin:$PATH
          /tmp/venv/bin/pytest -v -rs --tb=short 2>&1 | tee test-output.txt
          ! grep -q "SKIPPED.*xelatex" test-output.txt
      - name: Build package
        run: /tmp/venv/bin/pip install build && /tmp/venv/bin/python -m build
      - upload dist artifact

  publish:
    if: github.event_name == 'release'   # dry runs stop after build
    needs: build
    ...unchanged...
```

- Every Python entry point is invoked via `/tmp/venv/bin/...` — venv activation does not persist between Actions steps, and system pip is PEP 668-managed. `apt-get update` is mandatory: the base image deletes `/var/lib/apt/lists/*`. Steps that use pipelines declare `shell: bash` for `pipefail`.
- The apt TeX Live install disappears from `publish.yml` entirely — the last duplicate environment definition outside per-push `ci.yml` is gone. The `publish` job (PyPI trusted publishing) is untouched apart from the `if:` guard that makes dry runs safe.
- The pin is a literal `tag@digest` string in the workflow file: which environment a given release was tested in is readable from git history. No further bookkeeping. Take the digest from the `base-image.yml` step summary of run 33190682385 (the pinned digest must be the **index/manifest-list** digest, which is what `docker buildx imagetools inspect` and consumers resolve).
- Image pull happens before any step runs: `packages: read` is added to the workflow permissions (the existing explicit `permissions:` block zeroes everything not listed), and `credentials:` is belt-and-braces — the package is already public.
- `timeout-minutes` raised from 10 to 20: pulling the ~2.75 GB image costs a couple of minutes, acceptable at release cadence (user decision).
- **Mandatory dry run**: after PR 2 merges and before #55 closes, trigger `workflow_dispatch` once — it exercises image pull, checkout-in-container, apt, venv, the full suite, and the package build, and stops before `publish`. The next real release is then not the gate's first integration test.
- The gate runs on amd64 runners while production is arm64. Both architectures are built from the same Dockerfile and the same digest-pinned upstream, but they are separate manifests and exact cross-architecture parity is unverified — an explicitly accepted risk, per the issue.

### 2. Documentation (PR 2 remainder)

- `README.md` and `README.en.md`: add the release-gate sentence to the "Ready-made render environment" section — releases to PyPI run the full suite inside the pinned image before the package is built, so every published version has passed in the render environment. Same sentence in both languages, in the section's existing style.
- `CLAUDE.md` already documents the image and the pin-bump mechanism (landed in PR #56); PR 2 adds the release-gate half of the story to its one-liner if it is not already implied.
- CHANGELOG is written at release time per the repo's release process — not part of this change.

### 3. What already landed (reference, PR #56)

The full design rationale for the Dockerfile, the base-image workflow, the Georgia test contract (`KLARTEX_REQUIRE_GEORGIA`), and the `ci.yml` fix is preserved in the merged PR #56 and its files on `main`:

- `docker/Dockerfile.base` — `ARG TEXLIVE_REF` so workflow-resolved digests pin both builds to the same upstream snapshot; OCI `source`/`licenses` labels for ghcr repository association; location `docker/` was agent judgment (issue said only "move it here"), unchallenged in review.
- `.github/workflows/base-image.yml` — self-test before push (build #1 amd64 `load` → in-image suite → build #2 multi-arch push), dispatch tag input passed via `env` and grammar-validated, `permissions: contents: read, packages: write`, `timeout-minutes: 90`, no GHA cache (~7 GB/arch never fits), pin report to `$GITHUB_STEP_SUMMARY`, header note that published tags referenced by consumer history must never be deleted.
- `tests/test_renderer.py::test_header_font_georgia_renders` — `fc-list` probe, env-flag skip override, `%PDF-` + size assertions; only `header_font` is set (not `font: "Futura"`, which mscorefonts does not provide).

## Migration (follow-up in `swedev/klartex.se` — separate PR there, not part of this repo's changes)

- File a tracking issue in `swedev/klartex.se` so the cleanup has an owner and does not rely on memory (ask the user first — cross-repo issue creation is their call). It covers:
  - Delete `backend/Dockerfile.base` and `.github/workflows/backend-base.yml`.
  - `backend/Dockerfile` moves its `FROM` pin to `ghcr.io/swedev/klartex-base` at its **next** base bump — nothing forces an immediate one. The deletion PR can land immediately, the repoint later.
- `ghcr.io/swedev/klartex-se-base` stays and its published tags are never deleted (historical `backend/Dockerfile` pins reference them); it simply stops receiving new tags.

## Steps

1. ~~Create `docker/Dockerfile.base`~~ — done, PR #56.
2. ~~Create `.github/workflows/base-image.yml`~~ — done, PR #56.
3. ~~Add `test_header_font_georgia_renders` to `tests/test_renderer.py`~~ — done, PR #56 (335 passed, 0 skipped locally; missing-font → failure verified).
4. ~~Fix `ci.yml` test step (`shell: bash`, `-rs`)~~ — done, PR #56.
5. ~~Update `README.md`, `README.en.md`, `CLAUDE.md`~~ — done, PR #56, except the release-gate sentence (moves to step 8).
6. ~~Open PR 1, merge~~ — done: PR #56, merged 2026-08-28.
7. ~~Watch the first `base-image.yml` run; ghcr package public~~ — done: run 33190682385 green (self-test passed, multi-arch push), tag `20260828-3` published, package verified public. Pin: `ghcr.io/swedev/klartex-base:20260828-3@sha256:b011056413d449bdc41b893ff1bd538a2be46d78d3794698eb134f45936d6ff2` (confirm against the run's step summary before use).
8. Rewrite `publish.yml` per §1: container-pinned `build` job, `packages: read`, `workflow_dispatch` + `if: github.event_name == 'release'` on `publish`, absolute venv paths, `apt-get update` + poppler-utils, `shell: bash` on pipeline steps, `KLARTEX_REQUIRE_GEORGIA=1`, `timeout-minutes: 20`. Add the release-gate sentence to both READMEs (and `CLAUDE.md` if needed).
9. Open **PR 2** (`Closes #55`) from a fresh branch off current `main`, noting in the body which `base-image.yml` run the pin came from. After merge, trigger the `workflow_dispatch` dry run and confirm the `build` job is green (and `publish` skipped) before closing out.
10. File the `swedev/klartex.se` tracking issue per the Migration section (ask the user before creating it).

## Risks

- **Container-job pull auth**: if permissions were wrong, the release gate would fail at image pull, before any step runs. Largely retired: the package is public and `credentials:` + `packages: read` are belt-and-braces; the mandatory `workflow_dispatch` dry run discovers any residual failure mode on demand, not at the next release.
- **Wrong digest pinned**: the ghcr versions API lists several digests (index + per-arch manifests + attestations); pinning a per-arch or attestation digest would break the pull or pin the wrong artifact. Mitigated: take the pin from the `base-image.yml` step summary, which prints the index digest consumers resolve.
- **In-image apt installs at test time**: `apt-get update`/mirror availability adds a network dependency to the gate. If flakiness shows up, the documented fallback is baking `poppler-utils` into the image (revisiting the production-faithful judgment). The base build's mscorefonts download risk is inherent to the image and unchanged by the move.
- **`texlive/texlive:latest` drift**: each base rebuild takes whatever TeX Live is current. That is the existing, accepted mechanism (digest pinning isolates consumers), but a rebuild can surface unrelated TeX regressions in the self-test — which is exactly the point of self-testing before push.
- **Skip-guard coupling**: the xelatex guard greps pytest's human-readable output (`SKIPPED.*xelatex`); renaming skip reasons silently weakens it. Kept because it matches the established `ci.yml` pattern; the Georgia requirement deliberately avoids the pattern via the env flag.
- **Release-before-PR-2 window**: until PR 2 merges, a release would still be gated only by the apt environment. Low likelihood (releases are user-initiated) but worth landing PR 2 promptly.
- **Open-issue interaction**: #53 (XeLaTeX vs LuaLaTeX) would change what the image must contain; the full `texlive/texlive` base already ships LuaLaTeX, so no conflict, but a future engine switch should update the Dockerfile's sanity-check line. #51 (sandbox xelatex) may want firejail/bwrap in the image later — out of scope here.

## Test Plan

- ~~**Local / PR 1 CI / first `base-image.yml` run**~~ — all verified: local suite green with the Georgia test executing; `ci.yml` green with the pipefail fix; the `pull_request` self-test leg ran pre-merge; the first push-build's in-image suite passed with zero xelatex skips and published the multi-arch tag.
- **PR 2 review checks**: workflow YAML parses; the pin string matches the step-summary pin of run 33190682385; `permissions` block includes `packages: read`; `publish` job carries `if: github.event_name == 'release'`.
- **PR 2 dry run (mandatory, after merge)**: `workflow_dispatch` on `publish.yml` — image pull with credentials, checkout inside the container, apt, venv install, full suite with `KLARTEX_REQUIRE_GEORGIA=1`, `python -m build`, dist artifact uploaded; `publish` job correctly skipped on the dispatch event.
- **Next real release**: the gate runs on the release event and `publish` executes after it — the dry run has already de-risked everything up to the PyPI step.
- **Negative check (locked in by `KLARTEX_REQUIRE_GEORGIA`)**: removing Georgia from the image now fails the base self-test, and after PR 2 also the release gate — the class of bug from `swedev/klartex.se#13` cannot ship again.
