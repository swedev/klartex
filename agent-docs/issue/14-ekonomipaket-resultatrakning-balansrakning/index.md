# Issue #14: Financial package — resultaträkning, balansräkning, budgetrapport

**Branch from:** main

## Summary

Four standalone financial document templates as YAML recipes: income statement, balance sheet, budget report, and SIE export report. These use the financial components from #12 via the recipe engine. Fixed layouts with structured tables — explicitly recipe templates, not block engine documents.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | No (blocked by #12) |
| **Risk** | Medium |

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-03-29
**Feedback:** Rewrote to match current architecture. Removed #9 as blocker (closed). Updated file paths to klartex/ prefix. Noted that _recipe_base.tex.jinja may need financial component rendering branches. SIE-exportrapport flagged as potential stretch goal.

## Related Files

- [plan.md](plan.md) - Implementation plan

## Related Issues

- #12 — Financial components (blocker, OPEN)
- #9 — Composable architecture (closed, prerequisite)
- #13 — Annual meeting package (sibling, also depends on #12)
- #1 — Faktura (related, established recipe pattern)
