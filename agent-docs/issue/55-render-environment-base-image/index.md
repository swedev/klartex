# Issue #55: Own the render environment: publish the TeX Live base image and test inside it

**Branch from:** main

## Summary

Moves the production TeX Live base image (`Dockerfile.base`, currently in `swedev/klartex.se`) into this repository as `docker/Dockerfile.base`, published as `ghcr.io/swedev/klartex-base` by a new workflow that runs the full test suite inside the freshly built amd64 image before pushing. `publish.yml` gains a release gate that runs the suite inside the pinned base image (tag + digest in the workflow file, bumped by PR) before building the PyPI package. Per-push `ci.yml` keeps its cheap apt list. Adds a Georgia font render test — the concrete regression that motivated the issue — guarded against skipping in both in-image runs. Lands as two PRs (image + workflow first, then the `publish.yml` pin), with `swedev/klartex.se` cleanup as a follow-up in that repo.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Medium |

No blockers to starting PR 1. Rollout dependencies, explicit: PR 2 depends on PR 1's successfully published tag + digest; GHCR package visibility/access is a one-time manual setting (user action); `packages: read`/`write` permissions must be verified; the gate and base build depend on Debian mirrors (and the base build on the mscorefonts download); the `swedev/klartex.se` cleanup needs a tracking issue there. Related: #53 (engine re-evaluation — no conflict, noted in Risks), #51 (xelatex sandboxing — possible future image concern, out of scope). Cross-repo references: `swedev/klartex.se#13` (the Georgia incident) and `swedev/klartex.se#18` (consumer motivation) are context, not dependencies. Prior plan `agent-docs/issue/4-docker-image/` concerns the closed issue #4 (a different, app-level image) — no conflict. No other open plan touches `.github/workflows/` or a `docker/` directory.

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-08-28
**Feedback:** Two codex rounds. Round 1 (applied): shell strictness (`set -euo pipefail`/`shell: bash`) so test failures cannot pass silently, absolute venv paths + `apt-get update` in container steps, `packages: read` + GHCR-visibility prerequisite, a mandatory `workflow_dispatch` dry run of the release gate, `TEXLIVE_REF` digest pinning so the tested amd64 image is the pushed one, a concrete Georgia-test contract with a `KLARTEX_REQUIRE_GEORGIA` env flag instead of grep, and `README.en.md` in scope. Round 2 (applied): explicit `actions/checkout` + `context:`/`file:` in the base workflow, a path-filtered `pull_request` self-test leg for pre-merge validation, OCI source/license labels, and softened amd64/arm64 parity wording.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress log
