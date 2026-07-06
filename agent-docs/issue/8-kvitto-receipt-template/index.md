# Issue #8: Template: kvitto (receipt)

**Branch from:** main

## Summary

New `kvitto` recipe template — a lightweight payment confirmation (receipt number, date, simple items list, explicit total, payment method). Built on the recipe path like faktura, with two new recipe-only components (`receipt_header`, `receipt_table`) and reuse of `description_list` metadata and `invoice_note`.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Low |
| **Issue state** | Open, label `template`, unassigned, no milestone |
| **Blockers** | None found (no blocker references in issue; no conflicting open plans) |

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-07-06
**Feedback:** Codex review applied: empty-metadata guard on the description_list arm made an explicit step, `amount: 0` vs missing-amount handling specified with `is not none` + focused test, component-registration assertions added to test scope, README component lists added to docs step.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress log
