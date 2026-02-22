# Issue #11: Foreningskomponenter -- dagordning + namnrollista

**Based on:** main

## Summary

Create two reusable LaTeX component packages for Swedish association documents: `dagordning.sty` (paragraph-numbered agenda lists) and `namnrollista.sty` (formatted name/role tables). These components extract recurring patterns from the existing monolithic protokoll template into standalone, self-describing packages with `.meta.yaml` metadata. The work depends on issue #9 (composable architecture) which will establish the component pattern and directory structure.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | No (blocked by #9) |
| **Risk** | Medium |
| **Safe for junior** | Yes (once #9 establishes the pattern) |

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-02-18
**Feedback:** Updated file paths and naming to align with #9 plan (klartex- prefix, files in cls/). Added component registry step (klartex/components.py). Clarified discussion field support in dagordning. Added design decision for table vs list format.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress (if exists)

## Related Issues

- #9 - Composable architecture -- YAML-recept-engine + .sty-komponenter (BLOCKER, OPEN)
- #15 - Self-describing metadata -- meta.yaml per komponent (related, OPEN)
