# Issue #13: Annual meeting package — 8 association documents via block engine

**Branch from:** main

## Summary

Verify and demonstrate that all 8 annual meeting document types can be composed from the block engine. Create example fixtures, render tests, and documentation. No new recipe templates — the block engine is the composing layer and the agent picks the blocks.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | No (blocked by #12) |
| **Risk** | Low |

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-03-29
**Feedback:** Complete rewrite. Old plan created 8 recipe templates, contradicting the issue body which says "No separate template per document type needed." New plan uses block engine exclusively. Scope reduced from ~32 files to ~12. Only blocker remaining is #12 (financial components).

## Related Files

- [plan.md](plan.md) - Implementation plan

## Related Issues

- #12 — Financial components (blocker, OPEN — needed for årsredovisning and budget)
- #9 — Composable architecture (closed, prerequisite)
- #11 — Association components (closed, provided agenda + name_roster)
- #15 — Universal block engine (closed, prerequisite)
- #14 — Financial reports package (sibling, also depends on #12)
