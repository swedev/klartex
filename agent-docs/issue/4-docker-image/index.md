# Issue #4: Docker image

**Based on:** main

## Summary

Test the existing Dockerfile and docker-compose.yml setup, publish the image to GitHub Container Registry as `ghcr.io/swedev/klartex`, and add an automated CI workflow for building and pushing Docker images on push to main and version tags. Includes adding a `.dockerignore` and updating READMEs with Docker usage instructions.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Low |
| **Safe for junior** | Yes |

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-02-17
**Feedback:** Applied 6 fixes from codex review: added explicit `:latest` tag rule, gated GHCR login to skip on PRs (fork safety), replaced non-existent `/health` endpoint with `/templates`, fixed scope count (3 -> 4 files), added external dependencies row for GHCR permissions, and added design decision about base image pinning.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress (if exists)

## Related Issues

- #3 GitHub Actions CI - Complementary CI workflow for running tests (separate from Docker build)
- #2 Publish to PyPI - Also creates a `.github/workflows/` file (`publish.yml`), no conflict
