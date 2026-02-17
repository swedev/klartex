# Issue #8: Template: kvitto (receipt)

**Based on:** main

## Summary

Add a kvitto (receipt) template to klartex. This is a simpler document type than faktura -- no VAT breakdown, a single total amount, and a lightweight items list. The implementation follows the existing template pattern: create a `templates/kvitto/` directory with `schema.json` and `kvitto.tex.jinja`. No Python code changes are needed since the registry auto-discovers templates.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Low |
| **Safe for junior** | Yes |

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-02-17
**Feedback:** Added missing test fixture, test assertion updates, and README documentation steps. Corrected scope from 3 to 7 files.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress (if exists)

## Related Issues

- #1 - Improve faktura template design (same area: templates)
- #7 - More header layouts (adds header enum values to schemas)
