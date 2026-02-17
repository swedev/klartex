# Issue #5: TypeScript client SDK

**Based on:** main

## Summary

Create `@swedev/klartex` npm package in a new repo (`swedev/klartex-js`) -- a typed fetch wrapper around the Klartex HTTP API with three methods: `render()`, `templates()`, and `schema()`. Uses native `fetch` with zero dependencies, following the same TypeScript tooling patterns as the `@svensk/*` packages (tsup + vitest).

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Low |
| **Safe for junior** | Yes |

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-02-17
**Feedback:** Fixed API contract inconsistency (render signature vs RenderOptions), added camelCase-to-snake_case mapping design decision, expanded test coverage (trailing slashes, non-JSON errors, header merging), corrected file count from ~8 to ~12, added external dependencies row.

## Related Files

- [plan.md](plan.md) - Full implementation plan

## Related Issues

- #4 Docker image - Provides the server this SDK connects to
