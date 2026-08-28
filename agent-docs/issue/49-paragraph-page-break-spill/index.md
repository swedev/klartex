# Issue #49: A paragraph longer than a page does not break — it spills past the bottom margin

**Branch from:** main

## Summary

Fixes the eTeX penalty arrays in `klartex-base.cls` so a paragraph longer than one page breaks onto the next page instead of silently spilling past the bottom margin. Root cause: `\widowpenalties 2 10000 10000` / `\clubpenalties 2 10000 10000` repeat their last value for all remaining lines, forbidding every interline page break; the fix appends a terminating `0` (`3 10000 10000 0`) so only 1–2-line widows/orphans stay forbidden. Two-line change plus a regression test.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Low |

No blockers: refs #40 (closed) and PR #45 (merged) are context only. Issue is open, unassigned, no labels. No other open plan touches `klartex/cls/klartex-base.cls` or `tests/test_pdf_text_layer.py`. Affected since v0.6.0 (commit `fbbfc79`); the shared class means both block-engine and recipe renders are affected. Test dependencies (xelatex, pdftotext) are already required locally and in CI.

## Plan Review

**Status:** Reviewed

**Reviewed:** 2026-08-28

**Feedback:** Codex review confirmed the root-cause diagnosis and file choices; applied its four points — red-before-green step ordering, a preservation test for the 1–2-line policy (via `\the\widowpenalties`/`\the\clubpenalties` probes), corrected release history (v0.6.0, not v0.9.x), and a page-count assertion on raw `pdftotext` output with the marker asserted on the final page.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress log
