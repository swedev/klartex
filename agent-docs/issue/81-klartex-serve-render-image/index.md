# Issue #81: Publish klartex-render:X.Y.Z at each release — a klartex serve compile endpoint

**Branch from:** main

## Summary

The core publishes its own render process: a `klartex serve` FastAPI compile endpoint (`POST /render` → PDF, `GET /health`) behind a new `serve` extra, moved from klartex.se's retired in-repo render service and adapted to the slot API — plus `docker/Dockerfile.render` and a new `image` job in `publish.yml` that pushes multi-arch `ghcr.io/swedev/klartex-render:X.Y.Z` at each release, built from the same pinned base the release gate tests in. Consumers pin one version equal to their `klartex==` pin. First image ships in the same release as the already-merged alias removal (#80).

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Medium |

No open blockers: the sequencing prerequisite (alias removal, PR #80) is merged on main and unreleased, so the next release carries both. #51 (xelatex sandboxing) is related but explicitly out of scope. #76 (structured block-path exception) is an open coordination dependency — if it lands first, the server consumes the structured path instead of the moved regex. Consumer-side work tracks in swedev/klartex.se#46.

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-08-30
**Feedback:** Codex review found two workflow flaws that were folded into the plan — dispatch-retry could rebuild post-release code under an old version (fixed: retry only from the release tag ref, version validated in the build job) and the no-overwrite guard was unauthenticated and racy (fixed: login before inspect, per-version concurrency). Also applied: a closed error contract via a 422→400 mapping (D7), positive-range env validation, the #76 coordination note, README.en.md, and a narrowed missing-extra ImportError catch. Declared-size-only 413 kept as the issue's stated mechanism.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress log
