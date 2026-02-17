# Implementation Plan: Publish to PyPI

## Summary

Set up a GitHub Actions workflow so that tagged releases of klartex are automatically built with hatchling and published to PyPI using trusted publishing. This enables `pip install klartex` for end users.

## Triage Info

> Decision-support metadata for this issue.

| Field | Value |
|-------|-------|
| **Blocked by** | None |
| **Blocks** | None |
| **Related issues** | #3 GitHub Actions CI (complementary, open) |
| **Scope** | 1 new file, 1 minor edit |
| **Risk** | Low |
| **Complexity** | Low |
| **Safe for junior** | Yes |
| **Conflict risk** | Low (no other plans touch `.github/workflows/`) |
| **External dependencies** | PyPI project name `klartex` must be available; swedev org must configure trusted publisher on PyPI |

### Triage Notes

No blockers. Issue #3 (GitHub Actions CI) is related -- ideally a CI test workflow would run before publishing, but the publish workflow can be created independently and gated on a test job. The `pyproject.toml` is already configured with hatchling as build backend and has the correct metadata. No `.github/workflows/` directory exists yet.

Note: The test job in CI will only run non-render tests (schema validation, tex escaping, API structure) since xelatex is not available in standard GitHub runners. Render tests are gated behind `HAS_XELATEX` and will be skipped.

## Analysis

The project already has:
- A well-configured `pyproject.toml` with `hatchling` build backend
- Package metadata (name, version, description, license, dependencies)
- A CLI entry point (`klartex = "klartex.cli:app"`)
- An `__init__.py` that exports the public API
- Tests that gracefully skip when xelatex is not available

What's needed:
1. A GitHub Actions workflow that triggers on version tag pushes (e.g., `v0.1.0`)
2. PyPI trusted publishing configuration (no API tokens needed -- GitHub OIDC)
3. A small test step before publishing to catch obvious breakage (non-render tests only)
4. A `__version__` attribute in the package for runtime version queries (with safe fallback)

## Implementation Steps

### Phase 1: Add version metadata to package

1. Add `__version__` to `klartex/__init__.py`
   - Use `importlib.metadata` to read version from installed package metadata
   - Wrap in try/except `PackageNotFoundError` for source checkouts where the package is not installed
   - Fallback to `"0.0.0-dev"` when metadata is unavailable
   - Files to modify: `klartex/__init__.py`

### Phase 2: Create the publish workflow

1. Create `.github/workflows/publish.yml`
   - Trigger on push of tags matching `v*` (e.g., `v0.1.0`)
   - Jobs:
     - **test**: Install project with dev extras (`pip install .[dev]`), then run `pytest`. Note: only non-render tests will execute since xelatex is not on GitHub runners.
     - **build**: Install `build` package (`pip install build`), then build sdist and wheel using `python -m build`. Run `twine check dist/*` to validate metadata before publishing.
     - **publish**: Upload to PyPI using `pypa/gh-action-pypi-publish` with trusted publishing (OIDC). Use `environment: pypi` to match the trusted publisher config on PyPI.
   - The publish job should depend on both test and build succeeding
   - Files to create: `.github/workflows/publish.yml`

2. Configure the workflow with proper permissions
   - Set `id-token: write` permission for OIDC trusted publishing
   - Set `contents: read` for checkout
   - Use `actions/setup-python@v5` with Python 3.13
   - Use `actions/upload-artifact` and `actions/download-artifact` to pass built distributions between jobs

### Phase 3: Register on PyPI (manual)

1. Create the PyPI project (manual step, documented here for reference)
   - Go to https://pypi.org and create account / verify swedev org
   - Register the `klartex` package name (verify availability first)
   - Configure trusted publisher:
     - Repository owner: `swedev`
     - Repository name: `klartex`
     - Workflow name: `publish.yml`
     - Environment: `pypi` (must match the `environment:` in workflow)

### Phase 4: Test the workflow

1. Optionally test with TestPyPI first
   - Configure a second trusted publisher on test.pypi.org
   - Tag with `v0.1.0rc1` and verify the workflow publishes successfully
   - Verify `pip install --index-url https://test.pypi.org/simple/ klartex` works

2. Create the production release
   - Tag with `v0.1.0` and push
   - Verify the workflow triggers and passes
   - Verify the package appears on PyPI
   - Verify `pip install klartex` works in a clean environment

## Out of Scope (follow-up)

- GitHub Release creation from tags (can be added as a step in publish.yml or separate workflow later)
- TeX Live installation in CI for full render tests (consider for issue #3)

## Files Summary

| File | Action | Purpose |
|------|--------|---------|
| `.github/workflows/publish.yml` | Create | GitHub Actions workflow for building and publishing to PyPI |
| `klartex/__init__.py` | Modify | Add `__version__` via importlib.metadata with safe fallback |

## Codebase Areas

- `.github/workflows/`
- `klartex/`

## Design Decisions

> Non-trivial choices made during planning. Feedback welcome; otherwise implementation proceeds with these.

### 1. Trusted publishing (OIDC) over API tokens
**Options:** (A) PyPI API token stored as GitHub secret vs (B) Trusted publishing via GitHub OIDC
**Decision:** B -- Trusted publishing
**Rationale:** Trusted publishing is the modern recommended approach. No secrets to manage or rotate. PyPI verifies the request came from the specific GitHub repo/workflow via OIDC. The issue itself suggests this approach.

### 2. Tag-triggered workflow over manual dispatch
**Options:** (A) Trigger on tag push `v*` vs (B) Manual workflow dispatch vs (C) Trigger on GitHub Release creation
**Decision:** A -- Tag push trigger
**Rationale:** Tag-based triggering is the most common pattern and integrates naturally with `git tag v0.1.0 && git push --tags`. It can be combined with GitHub Releases later. Manual dispatch adds friction.

### 3. Version via importlib.metadata with safe fallback
**Options:** (A) Hardcode `__version__ = "0.1.0"` in `__init__.py` vs (B) Read from `importlib.metadata` with `PackageNotFoundError` fallback
**Decision:** B -- importlib.metadata with fallback
**Rationale:** Single source of truth in `pyproject.toml`. No risk of version string getting out of sync. Python 3.13 has `importlib.metadata` in stdlib. The try/except fallback ensures imports work in source checkouts and editable installs.

### 4. Include test job in publish workflow
**Options:** (A) Separate CI workflow (issue #3) as prerequisite vs (B) Include test step in publish workflow
**Decision:** B -- Include test step
**Rationale:** Since no CI workflow exists yet (#3), including a test job in the publish workflow provides a safety net. When #3 is implemented, the publish workflow can optionally be simplified to depend on CI status instead. Note that only non-render tests will run (schema, escaping, API structure) since xelatex is not on GitHub runners.

### 5. Use explicit `environment: pypi` in workflow
**Options:** (A) No environment (simpler) vs (B) Named `pypi` environment (more secure)
**Decision:** B -- Named environment
**Rationale:** Environments provide an extra layer of protection (optional approval rules, deployment logs). The trusted publisher config on PyPI must match the workflow's environment name, so being explicit prevents OIDC failures.

## Verification Checklist

- [ ] `pyproject.toml` has correct metadata for PyPI (name, version, description, license)
- [ ] `.github/workflows/publish.yml` triggers on `v*` tags
- [ ] Workflow installs dependencies (`pip install .[dev]`, `pip install build`)
- [ ] Workflow runs `pytest` before building
- [ ] Workflow builds sdist and wheel with `python -m build`
- [ ] Workflow runs `twine check dist/*` to validate metadata
- [ ] Workflow uses trusted publishing (OIDC) with `environment: pypi`
- [ ] `__version__` in `__init__.py` uses importlib.metadata with PackageNotFoundError fallback
- [ ] `pip install klartex` works after publishing
- [ ] `klartex --help` works after pip install
- [ ] `python -c "import klartex; print(klartex.__version__)"` returns correct version
- [ ] PyPI trusted publisher is configured for `swedev/klartex` repo with environment `pypi`
