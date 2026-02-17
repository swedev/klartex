# Issue #7: More Header Layouts

**Based on:** main

## Summary

Add three new header layout options -- centered, banner, and compact -- to complement the existing standard, minimal, and none layouts. Each layout is a self-contained Jinja2 snippet using the established `_header_{name}.jinja` pattern. Changes touch the header snippet files, all three template schemas, and tests. No modifications to klartex-base.cls are required.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Low |
| **Safe for junior** | Yes |

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-02-17
**Feedback:** Plan is clear and follows established patterns. Low risk, no blockers. Banner colorbox approach validated -- xcolor is already loaded.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress (if exists)

## Related Issues

- None
