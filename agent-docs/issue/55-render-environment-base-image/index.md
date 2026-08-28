# Issue #55: Own the render environment: publish the TeX Live base image and test inside it

**Branch from:** main

## Summary

Moves the production TeX Live base image into this repository as `docker/Dockerfile.base`, published as `ghcr.io/swedev/klartex-base` by `.github/workflows/base-image.yml`, which runs the full test suite inside the freshly built amd64 image before pushing. That half landed with PR #56 (merged 2026-08-28): the first build published tag `20260828-3` and the ghcr package is public. Remaining work is PR 2: `publish.yml` gains a release gate that runs the suite inside the pinned base image (tag + digest in the workflow file, bumped by PR) before building the PyPI package, plus a `workflow_dispatch` dry run and the release-gate sentence in both READMEs. Per-push `ci.yml` keeps its cheap apt list. The `swedev/klartex.se` cleanup is a follow-up in that repo, behind a tracking issue the user approves first.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Low |

No blockers: PR 2's prerequisites are met — PR #56 is merged, the first `base-image.yml` run (33190682385) published `ghcr.io/swedev/klartex-base:20260828-3` with its index digest, and the package is public (verified via the packages API). Remaining coordination: confirm the pin against the run's step summary; after PR 2 merges, run the mandatory `workflow_dispatch` dry run before closing #55; ask the user before filing the `swedev/klartex.se` cleanup issue. Related: #53 (engine re-evaluation — no conflict, noted in Risks), #51 (xelatex sandboxing — possible future image concern, out of scope). Cross-repo references `swedev/klartex.se#13` (the Georgia incident) and `swedev/klartex.se#18` (consumer motivation) are context, not dependencies. No other open plan touches `.github/workflows/` or `docker/`.

## Plan Review

**Status:** Amended
**Reviewed:** 2026-08-28
**Feedback:** Two codex rounds on the original plan. Round 1 (applied): shell strictness (`set -euo pipefail`/`shell: bash`) so test failures cannot pass silently, absolute venv paths + `apt-get update` in container steps, `packages: read` + GHCR-visibility prerequisite, a mandatory `workflow_dispatch` dry run of the release gate, `TEXLIVE_REF` digest pinning so the tested amd64 image is the pushed one, a concrete Georgia-test contract with a `KLARTEX_REQUIRE_GEORGIA` env flag instead of grep, and `README.en.md` in scope. Round 2 (applied): explicit `actions/checkout` + `context:`/`file:` in the base workflow, a path-filtered `pull_request` self-test leg for pre-merge validation, OCI source/license labels, and softened amd64/arm64 parity wording. Amended 2026-08-28 after PR #56 merged: plan rescoped to the remaining PR 2 with the concrete pin (`20260828-3@sha256:b011056…`); no design changes.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress log
