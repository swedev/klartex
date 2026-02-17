# Issue #1: Improve faktura template design

**Based on:** main

## Summary

The faktura template produces a functional invoice but needs visual polish. The plan covers restructuring the title area, improving recipient/reference layout, polishing the line items table, enhancing the totals section, and improving the payment information block. All changes are confined to the Jinja template file -- no Python or cls changes needed.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Low |
| **Safe for junior** | Yes |

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-02-17
**Feedback:** Codex review applied: clarified table styling approach (no new packages, right-align is sufficient), added Phase 0 baseline render, expanded verification to cover header modes and optional field edge cases, added concrete CLI commands for testing, tightened scope to single file.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress (if exists)

## Related Issues

None identified.
