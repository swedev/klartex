# Issue #10: Content-lager -- markdown to LaTeX-rendering

**Based on:** main

## Summary

Add a content layer that converts a simple markdown subset to LaTeX, enabling AI agents and users to write rich text (headings, bold, lists) in JSON data fields without LaTeX knowledge. Implemented as a Jinja2 filter (`| content`) that templates opt into per field, with a minimal custom parser and no new dependencies. Raw data is passed alongside escaped data in the Jinja2 context to support the dual escaping strategy.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Partially (core filter is independent of #9; template integration overlaps with #9 and #11) |
| **Risk** | Medium |
| **Safe for junior** | Yes |

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-02-18
**Feedback:** Resolved contradictory escaping strategy (settled on dual data context), reordered phases so escaping contract is decided before template updates, raised conflict risk to medium due to overlap with #9/#11, added parser edge cases (unmatched markers, list transitions, consecutive blank lines), clarified subclauses as plain text, and added .tex source assertion to integration tests.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress (if exists)

## Related Issues

- #9 - Composable architecture -- YAML-recept-engine + .sty-komponenter (partial prerequisite, OPEN)
- #11 - Foreningskomponenter (overlaps on `templates/protokoll/` and `klartex/renderer.py`)
