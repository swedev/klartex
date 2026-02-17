# Implementation Plan: Docker image

## Summary

Test the existing Dockerfile, set up publishing to GitHub Container Registry (GHCR) as `ghcr.io/swedev/klartex`, and add a GitHub Actions workflow for automated image builds.

## Triage Info

> Decision-support metadata for this issue.

| Field | Value |
|-------|-------|
| **Blocked by** | None |
| **Blocks** | None |
| **Related issues** | #3 GitHub Actions CI (complementary -- CI tests Python code), #2 Publish to PyPI (also creates `.github/workflows/` file) |
| **Scope** | 4 files across workflows, Docker config, and docs |
| **Risk** | Low |
| **Complexity** | Low-Medium |
| **Safe for junior** | Yes |
| **Conflict risk** | Low -- #3 creates `ci.yml`, #2 creates `publish.yml`, this creates `docker.yml` (all separate workflow files) |
| **External dependencies** | Org/repo must allow workflow token write access to packages; GHCR package visibility may need manual configuration for public access |

### Triage Notes

No blockers. The Dockerfile already exists and looks reasonable (based on `texlive/texlive:latest-minimal`, installs Python and TeX Live packages, runs the FastAPI service). The docker-compose.yml also exists for local development. The main work is: (1) verifying the existing Docker setup works, (2) creating a GHCR publish workflow, and (3) adding a `.dockerignore` for cleaner builds.

Issue #3 (GitHub Actions CI) is related but independent -- it tests the Python code, while this issue handles container image builds. They can proceed in parallel.

## Analysis

The project already has:
- **Dockerfile** -- Single-stage image based on `texlive/texlive:latest-minimal`, installs Python 3 + pip, TeX Live packages via `tlmgr`, creates a venv, installs the klartex package, and exposes port 8000 running `klartex serve`
- **docker-compose.yml** -- Simple service definition mapping port 8000 and mounting `./branding` as a volume
- **No `.dockerignore`** -- The `COPY . .` in the Dockerfile will copy everything including `.git`, `__pycache__`, tests, and agent-docs
- **No `.github/` directory** -- No workflows exist yet
- **API endpoints** -- FastAPI app exposes `/render` (POST), `/templates` (GET), `/templates/{name}/schema` (GET). No dedicated `/health` endpoint.

Key considerations:
1. The image is large due to `texlive/texlive:latest-minimal` base (~1.5 GB+). This is unavoidable since xelatex + fonts are needed at runtime.
2. GHCR authentication uses `GITHUB_TOKEN` which is automatically available in GitHub Actions. However, the org/repo settings must allow workflow tokens to write packages.
3. The Dockerfile does not use multi-stage builds. Since the runtime needs the same tools as the build, a multi-stage approach would not reduce image size.
4. Build caching can be leveraged via `docker/build-push-action` with GitHub Actions cache.

## Implementation Steps

### Phase 1: Add .dockerignore

1. Create `.dockerignore` to exclude unnecessary files from the build context
   - Exclude: `.git/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `agent-docs/`, `*.egg-info/`, `.env`, `.venv/`, `tests/`
   - Keep: source code, templates, cls, branding defaults, pyproject.toml, README
   - Files to create: `.dockerignore`

### Phase 2: Verify existing Docker setup

1. Ensure the Dockerfile builds successfully:
   ```bash
   docker build -t klartex:test .
   ```
2. Verify the container starts and responds:
   ```bash
   docker run -d --name klartex-test -p 8000:8000 klartex:test
   curl -f http://localhost:8000/templates
   docker stop klartex-test && docker rm klartex-test
   ```
3. Fix any issues found during testing (update Dockerfile if needed)

### Phase 3: Create GHCR publish workflow

1. Create `.github/workflows/docker.yml` with the following structure:

   **Triggers:**
   - Push to `main` (build and push `latest` + `main` tags)
   - Push tags matching `v*` (build and push version-tagged image)
   - Pull requests targeting `main` (build only, no push -- validates Dockerfile)

   **Permissions:**
   - `contents: read`
   - `packages: write` (required for GHCR push)

   **Steps:**
   1. `actions/checkout@v4`
   2. `docker/setup-buildx-action@v3` -- enables build caching
   3. `docker/login-action@v3` -- login to GHCR using `GITHUB_TOKEN`
      **Important:** Gate with `if: github.event_name != 'pull_request'` to avoid auth failures on fork PRs.
      ```yaml
      if: github.event_name != 'pull_request'
      registry: ghcr.io
      username: ${{ github.actor }}
      password: ${{ secrets.GITHUB_TOKEN }}
      ```
   4. `docker/metadata-action@v5` -- generate image tags and labels
      ```yaml
      images: ghcr.io/swedev/klartex
      tags: |
        type=ref,event=branch
        type=semver,pattern={{version}}
        type=semver,pattern={{major}}.{{minor}}
        type=sha
        type=raw,value=latest,enable={{is_default_branch}}
      ```
   5. `docker/build-push-action@v6` -- build and conditionally push
      ```yaml
      push: ${{ github.event_name != 'pull_request' }}
      tags: ${{ steps.meta.outputs.tags }}
      labels: ${{ steps.meta.outputs.labels }}
      cache-from: type=gha
      cache-to: type=gha,mode=max
      ```

   - Files to create: `.github/workflows/docker.yml`

### Phase 4: Documentation update

1. Update `README.md` (Swedish) to add a Docker usage section:
   - How to pull from GHCR: `docker pull ghcr.io/swedev/klartex`
   - How to run: `docker run -p 8000:8000 ghcr.io/swedev/klartex`
   - Reference to docker-compose.yml for local development with branding volumes
2. Update `README.en.md` with the same Docker section in English

## Files Summary

| File | Action | Purpose |
|------|--------|---------|
| `.dockerignore` | Create | Exclude unnecessary files from Docker build context |
| `.github/workflows/docker.yml` | Create | Automated Docker image build and GHCR publish workflow |
| `README.md` | Modify | Add Docker usage instructions (Swedish) |
| `README.en.md` | Modify | Add Docker usage instructions (English) |

## Codebase Areas

- `.github/workflows/`
- Root directory (Dockerfile, .dockerignore, docker-compose.yml)
- Documentation (README.md, README.en.md)

## Design Decisions

> Non-trivial choices made during planning. Feedback welcome; otherwise implementation proceeds with these.

### 1. Use docker/build-push-action over manual docker commands

**Options:** (A) Manual `docker build` + `docker push` commands vs (B) `docker/build-push-action` with buildx
**Decision:** B -- Use the official Docker GitHub Actions
**Rationale:** The official actions handle GHCR authentication, multi-platform builds (if needed later), build caching via GitHub Actions cache, and OCI metadata/labels automatically. This is the standard pattern used across the ecosystem and is well-maintained.

### 2. Tag strategy: branch + semver + sha + latest

**Options:** (A) Only `latest` tag vs (B) Branch name + semantic version + commit SHA + explicit latest tags
**Decision:** B -- Multiple tag types via metadata-action
**Rationale:** Users pulling `ghcr.io/swedev/klartex:latest` get the newest main build (via explicit `type=raw,value=latest,enable={{is_default_branch}}`). Version tags (`0.1.0`, `0.1`) allow pinning to releases. SHA tags enable traceability to exact commits.

### 3. Build-only on PRs (no push), gated login

**Options:** (A) Skip Docker build on PRs entirely vs (B) Build but don't push on PRs
**Decision:** B -- Build on PRs to validate the Dockerfile, with login step gated behind `if: github.event_name != 'pull_request'`
**Rationale:** This catches Dockerfile regressions in PRs before merge. Gating the login step avoids auth failures on fork PRs where `GITHUB_TOKEN` may lack packages:write permission.

### 4. No multi-stage build

**Options:** (A) Multi-stage build to reduce image size vs (B) Single-stage build
**Decision:** B -- Keep the existing single-stage build
**Rationale:** The runtime needs the same TeX Live packages, Python, and pip-installed klartex that the build stage uses. A multi-stage build would not reduce image size since there is no compile step producing a smaller artifact.

### 5. Unpinned base image (follow-up consideration)

**Options:** (A) Pin `texlive/texlive` to a specific digest/tag vs (B) Keep `latest-minimal`
**Decision:** B for now -- Keep `latest-minimal` for initial setup
**Rationale:** Pinning improves reproducibility but requires maintenance to update. For the initial Docker/GHCR setup, using `latest-minimal` is acceptable. A follow-up task can pin the base image once the workflow is proven stable.

## Verification Checklist

- [ ] `.dockerignore` exists and excludes `.git`, `__pycache__`, `agent-docs`, test artifacts
- [ ] Docker image builds successfully with `docker build -t klartex:test .`
- [ ] Container starts and `klartex serve` runs on port 8000
- [ ] `curl -f http://localhost:8000/templates` returns a valid response
- [ ] `.github/workflows/docker.yml` triggers on push to main, version tags, and PRs
- [ ] GHCR login uses `GITHUB_TOKEN` and is gated to skip on PRs
- [ ] Image is tagged with branch name, semver (on tags), commit SHA, and `latest` on default branch
- [ ] PRs trigger build-only (no push)
- [ ] Push to main triggers build + push to `ghcr.io/swedev/klartex:main` and `:latest`
- [ ] Version tags (e.g., `v0.1.0`) trigger build + push with version tags
- [ ] GitHub Actions cache is configured for Docker layer caching
- [ ] README.md and README.en.md document Docker usage
- [ ] Org/repo settings allow workflow token to write packages
