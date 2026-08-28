# Plan: Issue #55 — Own the render environment: publish the TeX Live base image and test inside it

## Goal

The environment klartex renders correctly in gets a single owner: this repository. Today two definitions exist — the apt list in `.github/workflows/ci.yml`/`publish.yml` here, and `backend/Dockerfile.base` in `swedev/klartex.se` (built on `texlive/texlive:latest` + Microsoft core fonts, published as `ghcr.io/swedev/klartex-se-base`). The suite passes in an environment nobody renders in, which is how the Georgia-font 500 (`swedev/klartex.se#13`) escaped: `tests/test_renderer.py::test_faktura_font_options_emitted` (line ~662) only asserts that `\newfontfamily\kxheaderfontfamily{Georgia}` is *emitted*, never rendered, because Georgia is not in CI.

Deliverables:

- `docker/Dockerfile.base` in this repo — the moved base image, comments rewritten for the new home, published as `ghcr.io/swedev/klartex-base` (date tag + run number, no `latest`, consumers pin by digest).
- `.github/workflows/base-image.yml` — builds when the Dockerfile (or the workflow) changes, **runs the full klartex test suite inside the freshly built amd64 image before pushing**, so a klartex-incompatible amd64 base is never published (arm64 gets the Dockerfile's build-time sanity check, not the full suite — see Risks).
- `publish.yml` gains a release gate: the full suite runs inside the pinned base image before the package is built, so nothing reaches PyPI that has not passed in the production environment. The pin (tag + digest) lives in the workflow file and is bumped by PR. A `workflow_dispatch` dry run exercises the gate before the first real release.
- A regression test that actually *renders* with Georgia, skipped where mscorefonts are absent (per-push apt CI) and **required** (skip turned into failure via an env flag) in both in-image runs — the concrete "next Georgia" catcher.
- Per-push `ci.yml` keeps its apt list as fast approximate feedback; the release gate is where the real environment is enforced. (User decision, issue Provenance section.) One drive-by correctness fix there: its `pytest | tee` pipeline currently reports tee's exit status, not pytest's (`run:` steps without an explicit `shell:` get bash *without* `pipefail`), so a pytest failure could pass the step — fix with `shell: bash` (GitHub then uses `bash --noprofile --norc -eo pipefail`).
- README (`README.md` + `README.en.md`) consumer documentation for the image, and a corrected framing of what the apt set is (per-push approximation) vs where the full production-environment run happens (release gate + base build).

Out of scope for this repo's PRs: the `swedev/klartex.se` cleanup (delete `backend/Dockerfile.base` + `backend-base.yml`, repoint the `FROM` pin) — listed under Migration below as coordinated follow-up in that repo, tracked by an issue there.

## Approach

### 1. `docker/Dockerfile.base` (new)

Copy `backend/Dockerfile.base` from `swedev/klartex.se` essentially verbatim — `FROM texlive/texlive:latest`, the `python3 python3-pip python3-venv curl` layer (kept per the issue: needed to install and test klartex inside the image, and consumers build on them), the mscorefonts layer with debconf EULA acceptance + `fc-cache`, the `/usr/local/texlive-bin` symlink, and the build-time sanity check (`xelatex --version`, `kpsewhich fontspec.sty`, `fc-list | grep -qi georgia/arial`).

Changes on move:

- Rewrite the header comments: published as `ghcr.io/swedev/klartex-base` by `.github/workflows/base-image.yml`; consumers (currently `swedev/klartex.se`'s `backend/Dockerfile`, later e.g. `swedev/valsedel`) pin a tag + manifest digest and add their venv/app on top. Written in now-state — no references to the old location.
- Parameterise the upstream base so the tested image and the pushed image are provably built from the same upstream snapshot:
  ```dockerfile
  ARG TEXLIVE_REF=texlive/texlive:latest
  FROM ${TEXLIVE_REF}
  ```
  The workflow resolves `texlive/texlive:latest` to a digest once per run and passes the digest-pinned ref to **both** builds (see below). Local `docker build` without args behaves as before.
- Add OCI ownership metadata so the ghcr package is reliably associated with this repository (GitHub recommends the source label for repository linking/permissions) and carries its license:
  ```dockerfile
  LABEL org.opencontainers.image.source="https://github.com/swedev/klartex"
  LABEL org.opencontainers.image.licenses="<SPDX id from this repo's LICENSE>"
  ```
- Location `docker/Dockerfile.base` is *agent judgment, open to challenge*: the issue says only "move it here". A `docker/` directory keeps the repo root clean and gives the workflow an obvious `paths:` trigger; root-level `Dockerfile.base` would work equally well. The Dockerfile has no `COPY`, so build context is irrelevant.
- **No test-only packages are added** (notably `poppler-utils` for `pdftotext`): the image is a production artifact and must stay faithful to what production runs. Test-only deps are installed transiently by the workflows at test time (see below). *Agent judgment, open to challenge* — the alternative (bake `poppler-utils` in) simplifies the workflows at the cost of a slightly less faithful production image, and is the documented fallback if apt-at-test-time proves flaky.

### 2. `.github/workflows/base-image.yml` (new)

Adapted from `swedev/klartex.se`'s `backend-base.yml`, keeping its security-conscious details:

- Triggers: `push` to `main` and `pull_request`, both with `paths: [docker/Dockerfile.base, .github/workflows/base-image.yml]`, plus `workflow_dispatch` with an optional `tag` input. On `pull_request` the workflow runs only the amd64 build + in-image self-test (no login, no push, no pin report — those steps are conditioned on `push`/`workflow_dispatch`), so PR 1 gets pre-merge validation of the image instead of the first integration test happening after merge. The build is rare (a few times a year) so the ~10-minute PR cost is acceptable. *Review-driven addition; the old `backend-base.yml` had no PR trigger.*
- `actions/checkout` as the first step — required both for the self-test's `-v "$PWD:/work"` mount and for building from the workspace; `docker/build-push-action` gets explicit `context: .` and `file: docker/Dockerfile.base` (its default Git context would not populate the runner workspace).
- Tag resolution unchanged: default `<YYYYMMDD>-<run_number>`, dispatch input reaches bash **via `env`, never `${{ }}` interpolation**, validated against the Docker tag grammar (`^[a-zA-Z0-9_][a-zA-Z0-9._-]{0,127}$`). No `latest` tag, ever.
- `permissions: contents: read, packages: write`; QEMU + buildx; ghcr login with `GITHUB_TOKEN`.
- **Resolve upstream once**: `docker buildx imagetools inspect texlive/texlive:latest` → digest; export `TEXLIVE_REF=texlive/texlive:latest@sha256:…` as a step output. Both builds receive it as `build-args: TEXLIVE_REF=…`, so upstream drift between the two builds is impossible.
- **Self-test before any push** (the behavioural addition over the old workflow):
  1. `docker/build-push-action` build #1: `platforms: linux/amd64`, `push: false`, `load: true`, explicit local tag `klartex-base:selftest`. The buildx builder's layer cache is retained within the job, so build #2 reuses these layers.
  2. Run the suite inside it, mounting the checkout (`shell: bash` on the step, and strict mode inside the container):
     ```
     docker run --rm -v "$PWD:/work" -w /work \
       -e KLARTEX_REQUIRE_GEORGIA=1 \
       klartex-base:selftest bash -c '
         set -euo pipefail
         apt-get update
         apt-get install -y --no-install-recommends poppler-utils
         python3 -m venv /tmp/venv
         /tmp/venv/bin/pip install .[dev]
         export PATH=/usr/local/texlive-bin:$PATH
         /tmp/venv/bin/pytest -v -rs --tb=short 2>&1 | tee /tmp/test-output.txt
         ! grep -q "SKIPPED.*xelatex" /tmp/test-output.txt'
     ```
     A venv is used because the image's Debian Python is PEP 668-managed (a throwaway venv is cleaner than `--break-system-packages`, and `python3-venv` is already in the base); all Python entry points are invoked by absolute venv path. `PATH` must include `/usr/local/texlive-bin` — the texlive image only sets PATH via `/etc/profile` login shells, and the explicit export makes the script independent of login-shell behaviour. `set -euo pipefail` guarantees an apt/pip/pytest failure fails the `docker run`. The xelatex no-skip grep mirrors `ci.yml`; the Georgia test needs no grep because `KLARTEX_REQUIRE_GEORGIA=1` turns its skip into a hard failure (see §4).
  3. Build #2: `platforms: linux/amd64,linux/arm64`, `push: true`, tag `ghcr.io/swedev/klartex-base:<tag>`, same `TEXLIVE_REF` build-arg. Runs only if the test step passed.
- Keep the "Report pin" step: print `ghcr.io/swedev/klartex-base:<tag>@<digest>` to `$GITHUB_STEP_SUMMARY` so the follow-up pin PR (here in `publish.yml`, and in `swedev/klartex.se`'s `backend/Dockerfile`) can copy it.
- `timeout-minutes: 90` retained (QEMU arm64 build is 15–20 min; the in-image test run adds a few minutes). No GHA cache, same rationale as before: ~7 GB per arch never fits the 10 GB repo cache.
- Note in the workflow header: published tags referenced by any consumer Dockerfile in history must never be deleted.

### 3. `publish.yml` — release gate inside the pinned base

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
      image: ghcr.io/swedev/klartex-base:<tag>@sha256:<digest>   # bumped by PR; copy from base-image.yml step summary
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
- The apt TeX Live install disappears from `publish.yml` entirely — one duplicate environment definition gone. The `publish` job (PyPI trusted publishing) is untouched apart from the `if:` guard that makes dry runs safe.
- The pin is a literal `tag@digest` string in the workflow file: which environment a given release was tested in is readable from git history. No further bookkeeping.
- Image pull happens before any step runs, so pull auth must be right: `packages: read` is added to the workflow permissions (the existing explicit `permissions:` block zeroes everything not listed), and `credentials:` covers a private package. **Prerequisite for PR 2**: the ghcr package is public, or grants this repository's Actions access — making `ghcr.io/swedev/klartex-base` public is recommended anyway (library consumers are the point of the move) and is a one-time manual GHCR setting (user action).
- **Mandatory dry run**: after PR 2 merges and before #55 closes, trigger `workflow_dispatch` once — it exercises image pull, checkout-in-container, apt, venv, the full suite, and the package build, and stops before `publish`. The next real release is then not the gate's first integration test.
- The gate runs on amd64 runners while production is arm64. Both architectures are built from the same Dockerfile and the same digest-pinned upstream, but they are separate manifests and exact cross-architecture parity is unverified — an explicitly accepted risk, per the issue.
- `timeout-minutes` raised from 10 to ~20: pulling the ~2.75 GB image costs a couple of minutes, acceptable at release cadence (user decision).

### 4. The Georgia render regression test

Add to `tests/test_renderer.py` (near `test_faktura_font_options_emitted`, whose emit-only assertion stays as the fast check):

```python
import os, shutil, subprocess   # os/shutil/subprocess as needed at module top

def _has_font(name: str) -> bool:
    if shutil.which("fc-list") is None:
        return False
    out = subprocess.run(["fc-list"], capture_output=True, text=True).stdout
    return name.lower() in out.lower()

REQUIRE_GEORGIA = os.environ.get("KLARTEX_REQUIRE_GEORGIA") == "1"
HAS_GEORGIA = _has_font("Georgia")

@pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
@pytest.mark.skipif(
    not HAS_GEORGIA and not REQUIRE_GEORGIA, reason="Georgia not installed"
)
def test_header_font_georgia_renders():
    data = _minimal_faktura(
        page_template={"name": "formal", "header_font": "Georgia"}
    )
    pdf = render("faktura", data)          # full pipeline, real xelatex run
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000
```

- Only `header_font: "Georgia"` is set — **not** the neighbouring test's `font: "Futura"`, which mscorefonts does not provide and would fail even in the image.
- Where the fonts are genuinely absent (per-push apt CI, contributor laptops without mscorefonts) the test skips; the reason string deliberately does not contain "xelatex", so `ci.yml`'s `SKIPPED.*xelatex` guard is not tripped. `-rs` is added to the pytest invocations so skips are listed stably in output.
- In environments that *must* have Georgia (both in-image runs), `KLARTEX_REQUIRE_GEORGIA=1` disables the skip: a Georgia-less image makes the test **fail** (xelatex errors on the missing font), which is more robust than grepping human-readable skip output. *Agent judgment*: the issue does not literally ask for this test, but "cannot catch the next one" is its stated problem, and without at least one font-render test the new gate proves nothing the apt run doesn't.

### 5. Documentation

- `README.md` **and** `README.en.md` (they are maintained as a pair): short section under the install instructions — a ready, tested render environment is published as `ghcr.io/swedev/klartex-base` (tag + digest pinning, what it contains, that releases are gated on the suite passing inside it). Points consumers (e.g. future `swedev/valsedel`) at it instead of reconstructing the apt list. Also **revise the existing sentence** ("The Debian/Ubuntu package set is the one CI installs, so it is the set the full test suite runs against" / Swedish counterpart, both at ~line 45): the apt set is the per-push approximation; the production environment is enforced at release and base-image builds.
- `CLAUDE.md`: one-line additions — the base image lives in `docker/Dockerfile.base`/`base-image.yml`, and the `publish.yml` release gate runs the suite inside the pinned image (so a base bump implies a follow-up pin PR, copied from the build's step summary).
- CHANGELOG is written at release time per the repo's release process — not part of this change.

### Rollout order (bootstrap)

`publish.yml` cannot pin a digest that does not exist yet, so the work lands in two PRs:

1. **PR 1**: `docker/Dockerfile.base` + `.github/workflows/base-image.yml` + the Georgia test + `ci.yml` pipefail fix + docs. Merging triggers the first `ghcr.io/swedev/klartex-base` build, which self-tests (including the new Georgia test with `KLARTEX_REQUIRE_GEORGIA=1` — its first must-run execution) and publishes the first tag. Then the ghcr package is made public (manual, user).
2. **PR 2**: `publish.yml` switched to the container gate, pinned to the tag + digest from PR 1's step summary, with `packages: read` and the `workflow_dispatch` dry-run trigger. Same "bump the pin by PR" mechanism every future base bump uses. Before closing #55: run the dry run once and confirm it is green through the `build` job.

PR 1 uses `Part of #55`; PR 2 uses `Closes #55`.

## Migration (follow-up in `swedev/klartex.se` — separate PR there, not part of this repo's changes)

- File a tracking issue in `swedev/klartex.se` so the cleanup has an owner and does not rely on memory. It covers:
  - Delete `backend/Dockerfile.base` and `.github/workflows/backend-base.yml`.
  - `backend/Dockerfile` moves its `FROM` pin to `ghcr.io/swedev/klartex-base` at its **next** base bump — nothing forces an immediate one. The deletion PR can land immediately, the repoint later.
- `ghcr.io/swedev/klartex-se-base` stays and its published tags are never deleted (historical `backend/Dockerfile` pins reference them); it simply stops receiving new tags.

## Steps

1. Create `docker/Dockerfile.base` — content from `swedev/klartex.se` `backend/Dockerfile.base` with the `ARG TEXLIVE_REF` parameterisation, OCI source/license labels, and header comments rewritten for this repo; keep the python3/pip/venv/curl layer, mscorefonts layer, texlive-bin symlink, and sanity-check `RUN` unchanged.
2. Create `.github/workflows/base-image.yml` — push/PR/dispatch triggers with path filters, checkout, tag resolution (env-passed, grammar-validated), QEMU/buildx (+ login on push/dispatch only), upstream-digest resolution, amd64 `load` build tagged `klartex-base:selftest` with explicit `context: .`/`file:`, in-image test run (strict mode, apt update+poppler-utils, venv with absolute paths, PATH export, `KLARTEX_REQUIRE_GEORGIA=1`, pytest `-rs`, xelatex no-skip grep), then — push/dispatch only — multi-arch push build with the same `TEXLIVE_REF` and pin report to step summary.
3. Add `test_header_font_georgia_renders` to `tests/test_renderer.py` per §4 (fc-list probe, `KLARTEX_REQUIRE_GEORGIA` override, `%PDF-` + size assertions); verify locally that it runs (Georgia present via mactex) and that `KLARTEX_REQUIRE_GEORGIA=1` on a Georgia-less machine turns the skip into a failure.
4. Fix `ci.yml`'s test step: `shell: bash` (pipefail) and `-rs` on pytest, everything else unchanged.
5. Update `README.md`, `README.en.md` (consumer section + corrected "test suite runs against" sentence) and `CLAUDE.md`.
6. Run `pytest` locally; optionally `docker build --file docker/Dockerfile.base docker/` as a local sanity check. Open **PR 1** (`Part of #55`), targeting `main`.
7. After merge: watch the first `base-image.yml` run — self-test must pass (zero xelatex skips, Georgia test executed) and a tag must publish. Copy the tag + digest from the step summary. Ask the user to set the ghcr package public.
8. Rewrite `publish.yml` per §3: container-pinned `build` job, `packages: read`, `workflow_dispatch` + `if: github.event_name == 'release'` on `publish`, absolute venv paths, apt update, `shell: bash` on pipeline steps, `timeout-minutes: 20`.
9. Open **PR 2** (`Closes #55`), noting in the body which `base-image.yml` run the pin came from. After merge, trigger the `workflow_dispatch` dry run and confirm the `build` job is green before closing out.
10. File the `swedev/klartex.se` tracking issue per the Migration section (ask the user before creating it — cross-repo issue creation is their call).

## Risks

- **Container-job pull auth**: if the package permission setup is wrong, the release gate fails at image pull, before any step runs. Mitigated by `packages: read` in the workflow permissions, the explicit `credentials:` block, making the package public, and the mandatory `workflow_dispatch` dry run after PR 2 — the failure mode is discovered on demand, not at the next release.
- **Bootstrap ordering**: PR 2 depends on PR 1's successfully published tag + digest and on the GHCR visibility/access being configured; landing both together would break `publish.yml` on a non-existent pin. Mitigated by the explicit two-PR rollout with the dependency stated in each PR body.
- **Tested-vs-pushed image identity**: builds #1 and #2 are separate; without the `TEXLIVE_REF` digest resolution, upstream `texlive/texlive:latest` could theoretically move between them. The shared build-arg pin plus the shared builder cache close that gap for amd64. **arm64 is not full-suite tested** — it gets the Dockerfile's build-time sanity check (xelatex runs, fontspec resolves, fonts present) only; the issue explicitly accepts amd64-only suite runs.
- **In-image apt installs at test time**: `apt-get update`/mirror availability adds a network dependency to the gate and the base build, and the base build additionally depends on the mscorefonts external font download. If flakiness shows up, the documented fallback is baking `poppler-utils` into the image (revisiting the "production-faithful" judgment in §1); the mscorefonts download risk is inherent to the existing image and unchanged by the move.
- **`texlive/texlive:latest` drift**: each base rebuild takes whatever TeX Live is current. That is the existing, accepted mechanism (digest pinning isolates consumers), but a rebuild can surface unrelated TeX regressions in the self-test — which is exactly the point of self-testing before push.
- **Skip-guard coupling**: the xelatex guard greps pytest's human-readable output (`SKIPPED.*xelatex`); renaming skip reasons silently weakens it. Kept because it matches the established `ci.yml` pattern; the Georgia requirement deliberately avoids the pattern via the env flag.
- **Open-issue interaction**: #53 (XeLaTeX vs LuaLaTeX) would change what the image must contain; the full `texlive/texlive` base already ships LuaLaTeX, so no conflict, but a future engine switch should update the sanity-check line. #51 (sandbox xelatex) may want firejail/bwrap in the image later — out of scope here.

## Test Plan

- **Local**: `pytest` green (with mactex + Georgia the new test executes; without Georgia it skips with the non-xelatex reason). `KLARTEX_REQUIRE_GEORGIA=1 pytest tests/test_renderer.py::test_header_font_georgia_renders` fails, not skips, on a Georgia-less machine. Optional local `docker build` of the base.
- **PR 1 CI**: `ci.yml` green with the pipefail fix in place; verify in the run log that the Georgia test shows `SKIPPED ... Georgia not installed` and the xelatex-skip guard still passes. The path-filtered `pull_request` leg of `base-image.yml` runs the amd64 build + in-image self-test pre-merge — the image is validated before it can publish.
- **First `base-image.yml` run**: in-image suite passes with zero xelatex skips and the Georgia test *executed*; multi-arch push succeeds; step summary shows the pin; both builds log the same resolved `TEXLIVE_REF`.
- **PR 2 dry run (mandatory)**: `workflow_dispatch` on `publish.yml` — image pull with credentials, checkout inside the container, apt, venv install, full suite, `python -m build`, dist artifact uploaded; `publish` job correctly skipped on the dispatch event.
- **Next real release**: the gate runs on the release event and `publish` executes after it — the dry run has already de-risked everything up to the PyPI step.
- **Negative check (locked in by `KLARTEX_REQUIRE_GEORGIA`)**: removing Georgia from the image now fails the base self-test — the class of bug from `swedev/klartex.se#13` cannot ship again.
