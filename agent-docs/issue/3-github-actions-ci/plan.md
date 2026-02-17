# Implementation Plan: GitHub Actions CI

## Summary

Set up a GitHub Actions CI workflow that runs tests automatically on push and pull requests. The key challenge is making xelatex available in the runner so that the full test suite (including PDF render tests) executes. The project already has 22 tests with graceful xelatex skip logic, but the goal is to run *all* tests in CI, including render tests.

## Triage Info

> Decision-support metadata for this issue.

| Field | Value |
|-------|-------|
| **Blocked by** | None |
| **Blocks** | None |
| **Related issues** | #2 Publish to PyPI (complementary -- publish workflow includes a lightweight test step) |
| **Scope** | 1 new file (`.github/workflows/ci.yml`) |
| **Risk** | Low-Medium |
| **Complexity** | Low-Medium (TeX Live + Python 3.13 setup adds complexity) |
| **Safe for junior** | Yes |
| **Conflict risk** | Low -- #2 plan also creates a file in `.github/workflows/` but a different one (`publish.yml` vs `ci.yml`) |
| **External dependencies** | GitHub Actions minutes, Docker Hub availability for texlive image, TeX mirror availability for tlmgr |

### Triage Notes

No blockers. Issue #2 (Publish to PyPI) has a related plan that includes a basic test job in its publish workflow, but that job intentionally skips render tests. This CI workflow is the dedicated solution for full test coverage including PDF rendering. The two workflows are complementary and non-conflicting.

The Dockerfile already demonstrates the exact TeX Live packages needed (`texlive/texlive:latest-minimal` base image with specific `tlmgr install` packages), which can be reused as a reference for the CI setup.

**Python 3.13 constraint:** The project requires `>=3.13`. The TeX Live Docker container is Debian-based and ships Python 3.11 or 3.12 via apt. The recommended approach is to use a standard Ubuntu runner with `setup-python` for Python 3.13 and install TeX Live via apt (faster than pulling a Docker image, and avoids the Python version mismatch).

## Analysis

The project currently has:
- **4 test files**: `test_renderer.py`, `test_schemas.py`, `test_api.py`, `test_tex_escape.py`
- **22 tests** (per issue description): 18 unique test functions, some parametrized (e.g., `test_render_pdf` x3, `test_fixture_validates` x3)
- Tests that require xelatex are gated with `@pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")`
- A `Dockerfile` based on `texlive/texlive:latest-minimal` that installs the required TeX Live packages
- Python 3.13 requirement (`requires-python = ">=3.13"`)
- Dev dependencies: `pytest>=8.0`, `httpx>=0.28.0`
- No `.github/` directory exists yet

**Runtime strategy decision:** Use a standard Ubuntu runner with `actions/setup-python` for Python 3.13, and install TeX Live packages via `apt-get install texlive-xetex texlive-fonts-recommended texlive-latex-extra`. This avoids the Python version mismatch of the Docker container approach and leverages GitHub's cached tool versions for faster setup.

## Implementation Steps

### Phase 1: Create the CI workflow

1. Create `.github/workflows/ci.yml` with the following structure:

   **Triggers:**
   - Push to `main`
   - Pull requests targeting `main`

   **Concurrency:** Cancel in-progress runs for the same branch/PR

   **Job: test** (single job -- no separate lint since no linter is configured)
   - Runner: `ubuntu-latest`
   - Permissions: `contents: read`
   - Timeout: 10 minutes
   - Steps:
     1. `actions/checkout@v4`
     2. `actions/setup-python@v5` with Python `3.13`
     3. Install TeX Live via apt:
        ```bash
        sudo apt-get update
        sudo apt-get install -y --no-install-recommends \
          texlive-xetex texlive-fonts-recommended texlive-latex-extra \
          texlive-latex-recommended
        ```
     4. Verify xelatex is available:
        ```bash
        which xelatex && xelatex --version
        ```
     5. Install project with dev extras:
        ```bash
        pip install .[dev]
        ```
     6. Run full test suite:
        ```bash
        pytest -v --tb=short
        ```
     7. Verify no tests were skipped due to missing xelatex:
        ```bash
        pytest -v 2>&1 | grep -c "SKIPPED.*xelatex" | xargs test 0 -eq
        ```
        (Fails the step if any tests were skipped for xelatex reasons)

   - Files to create: `.github/workflows/ci.yml`

### Phase 2: Validate TeX Live package coverage

1. The Dockerfile installs specific packages via `tlmgr`: xetex, fontspec, fancyhdr, geometry, xcolor, titlesec, enumitem, lastpage, hyperref, parskip, setspace, etoolbox, booktabs, tabularx, collection-fontsrecommended
2. The Ubuntu `texlive-xetex` + `texlive-fonts-recommended` + `texlive-latex-extra` packages should cover all of these. If any template fails to render due to a missing `.sty`, add the corresponding Ubuntu package.
3. This validation happens on the first CI run -- if tests fail, check the LaTeX log for missing packages and add the relevant `texlive-*` apt package.

## Files Summary

| File | Action | Purpose |
|------|--------|---------|
| `.github/workflows/ci.yml` | Create | CI workflow running full test suite with xelatex |

## Codebase Areas

- `.github/workflows/`

## Design Decisions

> Non-trivial choices made during planning. Feedback welcome; otherwise implementation proceeds with these.

### 1. Ubuntu runner + setup-python over Docker container

**Options:** (A) Use `container: texlive/texlive:latest-minimal` in the job vs (B) Use Ubuntu runner with `setup-python` + TeX Live via apt
**Decision:** B -- Ubuntu runner with apt-installed TeX Live
**Rationale:** The project requires Python `>=3.13`. The TeX Live Docker container is Debian-based and ships Python 3.11/3.12 via apt -- installing 3.13 inside it requires building from source or complex workarounds. The Ubuntu runner approach uses `actions/setup-python` which natively supports Python 3.13 and is well-cached by GitHub. TeX Live packages via apt are sufficient for the templates used and install in under 2 minutes.

### 2. Single test job (no separate lint job)

**Options:** (A) Single test job vs (B) Separate lint and test jobs
**Decision:** A -- Single test job
**Rationale:** The project has no linter configured (no ruff, flake8, mypy in `pyproject.toml` or config files). Adding a lint job would require adding a linter dependency first. A lint job can be added later when linting tools are configured.

### 3. Trigger scope: main + PRs only

**Options:** (A) All branches on push vs (B) Only `main` branch push + all PRs vs (C) All branches + all PRs
**Decision:** B -- Main branch push + PRs
**Rationale:** Running CI on every push to every branch wastes Actions minutes. The main use case is validating PRs and ensuring main stays green. Feature branch pushes that are not yet in a PR don't need CI.

### 4. Explicit xelatex skip verification

**Options:** (A) Trust that xelatex is installed and tests run vs (B) Add explicit post-test check that no tests were skipped for xelatex reasons
**Decision:** B -- Explicit verification
**Rationale:** The whole point of this CI workflow is to run *all* tests including render tests. If TeX Live installation silently breaks, tests would be skipped (not failed) due to the `skipif` decorators. An explicit check ensures the CI catches this regression.

## Verification Checklist

- [ ] `.github/workflows/ci.yml` triggers on push to main and pull requests
- [ ] `actions/checkout@v4` and `actions/setup-python@v5` are used
- [ ] Python 3.13 is set up via `setup-python`
- [ ] TeX Live packages are installed via apt (texlive-xetex, texlive-fonts-recommended, texlive-latex-extra)
- [ ] xelatex is verified as available before running tests
- [ ] `pip install .[dev]` succeeds
- [ ] `pytest -v` runs all 22 tests (none skipped due to missing xelatex)
- [ ] Post-test step verifies zero xelatex-related skips
- [ ] Render tests produce valid PDFs (tests check `%PDF-` header and minimum size)
- [ ] Concurrency group is set to cancel in-progress runs for same branch
- [ ] Workflow completes in reasonable time (target: under 5 minutes)
- [ ] No secrets or tokens required (all tests are self-contained)
