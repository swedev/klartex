# Issue #13: Arsmotespaket -- 8 foreningsmallar som YAML-recept

**Based on:** main

## Summary

Create a complete annual meeting document package consisting of 8 YAML recipe templates for Swedish associations. The templates cover all standard documents needed for an annual meeting: kallelse (summons), verksamhetsberattelse (annual report), arsredovisning (financial report), revisionsberattelse (audit report), budget, valberedningens forslag (nomination proposal), motion, and styrelsens svar (board response). Each template is a YAML recipe + JSON schema using the composable architecture from #9 with components from #10, #11, and #12. The package enables AI agents to generate all 8 PDFs from structured data with unified branding.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | No (blocked by #9, #10, #11, #12) |
| **Risk** | Medium |
| **Safe for junior** | Yes (once dependencies land) |

## Plan Review

**Status:** Skipped
**Reviewed:** 2026-02-18
**Feedback:** Codex review not available; plan ready for manual review

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress (if exists)

## Related Issues

- #9 - Composable architecture -- YAML-recept-engine (blocker, OPEN)
- #10 - Content-lager -- markdown to LaTeX-rendering (blocker, OPEN)
- #11 - Foreningskomponenter -- dagordning + namnrollista (blocker, OPEN)
- #12 - Ekonomikomponenter -- resultatrakning, budgettabell, notapparat (blocker, OPEN)
- #14 - Ekonomipaket -- shares economic components, potential test/doc conflicts
- #15 - Self-describing metadata -- meta.yaml per komponent (related)
