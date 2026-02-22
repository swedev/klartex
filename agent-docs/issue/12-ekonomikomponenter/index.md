# Issue #12: Ekonomikomponenter -- resultatrakning, budgettabell, notapparat

**Based on:** main

## Summary

Create three reusable LaTeX component packages for financial documents within the Klartex system. The components handle complex tabular layouts for income statements (resultatrakning), budget tables (budgettabell), and numbered footnotes (notapparat). Each component accepts structured JSON/YAML data and produces formatted financial tables following Swedish conventions. This issue depends on #9 (composable architecture) which must land first to provide the component infrastructure.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | No (blocked by #9) |
| **Risk** | Medium |
| **Safe for junior** | No |

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-02-18
**Feedback:** Applied 9 review findings: added #13/#14 to Blocks, added explicit resultat input + Jinja path for rrresultat, standardized \notentry macro name, fixed budgetpost to all-positional API, moved numformat phase before components, resolved siunitx as number formatting choice, removed label/ref contradiction in note-linking, namespaced test fixtures to avoid collision with #14, corrected scope count to ~16 files.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress (if exists)

## Related Issues

- #9 - Composable architecture -- YAML-recept-engine + .sty-komponenter (blocker, OPEN)
- #11 - Foreningskomponenter -- dagordning + namnrollista (sibling, also blocked by #9)
- #15 - Self-describing metadata -- meta.yaml per komponent (defines .meta.yaml format)
