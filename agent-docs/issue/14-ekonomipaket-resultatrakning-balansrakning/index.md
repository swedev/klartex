# Issue #14: Ekonomipaket -- resultatrakning, balansrakning, budgetrapport

**Based on:** main

## Summary

Create four standalone financial document templates (resultatrakning, balansrakning, budgetrapport, SIE-exportrapport) as YAML recipes using the composable architecture from #9 and the economic components from #12. Each template combines reusable `.sty` components with JSON Schema validation to produce professional financial PDFs from structured accounting data. This issue is directly relevant to the OpenVera project for structured bookkeeping data to PDF conversion.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | No (blocked by #9 and #12) |
| **Risk** | Medium |
| **Safe for junior** | Yes (once #9 and #12 establish the patterns) |

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-02-18
**Feedback:** Codex review applied. Key changes: (1) Added Phase 0 dependency sync gate to verify #9/#12 interfaces before starting. (2) Fixed conflict risk — #11 overlaps on `tests/test_renderer.py` and `tests/test_schemas.py`. (3) Specified balansrakning balance-check behavior (warning row for imbalance, not validation error). (4) Added `balansrakning_imbalanced.json` fixture. (5) Added explicit test cases for branding, header layouts, and note references. (6) Added `README.en.md` to docs phase. (7) Noted #9 engine selection contract and escaping convention in Phase 0. (8) Fixed scope to ~18 files. (9) Flagged component naming convention as TBD pending #12.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress (if exists)

## Related Issues

- #9 - Composable architecture -- YAML-recept-engine + .sty-komponenter (BLOCKER, OPEN)
- #12 - Ekonomikomponenter -- resultatrakning, budgettabell, notapparat (BLOCKER, OPEN)
- #1 - Improve faktura design (related)
- #8 - Kvitto receipt template (related)
- #11 - Foreningskomponenter -- dagordning + namnrollista (sibling, also blocked by #9)
