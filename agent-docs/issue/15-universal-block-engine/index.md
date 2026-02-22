# Issue #15: Universal Block Engine and Self-Describing Components

**Based on:** main

## Summary

Replace the template-per-document-type model with a universal block engine where the agent composes `body[]` freely from typed blocks (heading, clause, signatures, etc.). Introduces page templates to replace the header enum, and a self-describing block registry accessible via API (`GET /blocks`, `GET /blocks/{name}/schema`). This is the architectural foundation for issues #11, #12, #13, and #14.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Medium |
| **Safe for junior** | No |

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-02-22
**Feedback:** Added missing files (recipe.py, registry.py, cli.py, test_recipe.py, block schema files). Noted that _header_*.jinja includes already define both header and footer (page templates wrap these). Added faktura to backward-compat verification. Scope updated to ~20 files.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress (if exists)

## Related Issues

- #7 - More header layouts (subsumed: header enum becomes page templates)
- #9 - Composable architecture (closed, prerequisite)
- #11 - Association components: dagordning + namnrollista (blocks on this)
- #12 - Financial components: resultatrakning, budgettabell, notapparat (blocks on this)
- #13 - Annual meeting package (blocks on this)
- #14 - Financial package (blocks on this)
