# Issue #12: Financial components — resultaträkning, budgettabell, notapparat

**Branch from:** main

## Summary

Three financial block types for the block engine: income statement, budget table, and numbered notes. Follow the established component pattern (.sty + schema + components.py + block engine jinja). Shared number formatting via `siunitx`. These are building blocks for #13 and #14.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Medium |

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-03-29
**Feedback:** Rewrote plan to match actual architecture after #9/#11/#15 landed. Removed outdated .meta.yaml and separate jinja macro references. Aligned file paths with current package layout (klartex/ prefix). Unblocked — #9 and #15 are closed.

## Related Files

- [plan.md](plan.md) - Implementation plan
- [research.md](research.md) - Research findings (if exists)

## Related Issues

- #9 — Composable architecture (closed, prerequisite)
- #11 — Association components (closed, sibling — established the pattern)
- #15 — Universal block engine (closed, prerequisite)
- #13 — Annual meeting package (downstream, uses these components)
- #14 — Financial reports package (downstream, uses these components)
