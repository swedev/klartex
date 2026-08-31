# Issue #83: Guaranteed font set in the render environment, and a path for external fonts

**Branch from:** main

## Summary

Curates and guarantees a font set in the render base image (MS core fonts plus open Debian families), surfaces the guaranteed list in the `font`/`header_font` schema descriptions generated from a single `GUARANTEED_FONTS` constant, and adds a file form (`{"file": "Inter-Regular.ttf", …}`) so external fonts can travel as assets per render call. Three phases: code+schema+Dockerfile+tests, then the base-image pin bump (publish.yml + Dockerfile.render in one commit), then the file form.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Medium |

No blockers or parent issue; issue is open, unlabeled, unassigned. Scope splits into three PRs: Phase A (code/schema/Dockerfile/tests), Phase B (base-image pin bump in `publish.yml` + `Dockerfile.render`, one commit), Phase C (file form). Related: #61 "Expand the page-template typography surface beyond font and header_font" (open) touches the same `DOCUMENT_SETTINGS` area of `klartex/page_templates.py` — no dependency, rebase whoever lands second. No file conflicts with other open plans. External coordination: klartex.se gets the guarantee only when it moves its own base pin after Phase B.

## Plan Review

**Status:** Reviewed

**Reviewed:** 2026-08-31

**Feedback:** Codex review applied: underscore removed from the font filename pattern (LaTeX special — the escape-invariance claim was wrong), the Debian package list verification promoted to an explicit first step, missing bold/italic face behaviour decided and documented (regular-face fallback, no synthesis), Dockerfile checks extended to exact-match every guaranteed family, preflight factored through a shared `_resolve_asset_root()` with fuller test coverage, and the file-form test font sourced deterministically via `kpsewhich` instead of fontconfig.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress log
