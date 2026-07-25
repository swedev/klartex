# Issue #37: Page template assets resolve relative to cwd instead of the template's directory

**Branch from:** main

## Summary

External page templates referenced via `--page-template` (or auto-detected next to the data file) fail to find their own assets (`\includegraphics{logo.pdf}` etc.) unless the assets are copied into the build cwd. Fix: the CLI passes the template file's directory as `asset_dir` to `render()` — a renderer mechanism that already exists and injects the directory into `TEXINPUTS` before cwd — so assets resolve next to the template, with cwd kept as fallback.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Low |
| **Issue state** | Open, unassigned, no labels or milestone |
| **Blockers** | None |
| **Test dependency** | XeLaTeX (already required by CI) |
| **Prerequisite in place** | `render(asset_dir=...)` landed in v0.11.1 |

## Plan Review

**Status:** Reviewed

**Reviewed:** 2026-07-25

**Feedback:** Codex confirmed the diagnosis and approach; applied amendments: doc wording must not imply API `page_template_source` resolves paths (CLI-only fix), added missing cwd-default test branch, fallback/precedence and relative-`asset_dir` hardening tests, and documented the symlink-target resolution as a deliberate contract.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress log (created during implementation)
