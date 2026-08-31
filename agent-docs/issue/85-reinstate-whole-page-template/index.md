# Issue #85: Reinstate the whole-page custom template: one file for the full design, plus autodetection

**Branch from:** main

## Summary

Brings back the whole-page custom page-template source removed in #80: `render(page_template_source=…)`, `--page-template` on the CLI, and autodetection of `<data-stem>.tex.jinja` / `page_template.tex.jinja`. The source owns both slots (emitted once, via the reinstated `shared_source` flag) while document-level settings (`font`, `header_font`, `diff_style`, `margins`) keep applying and a recipe's top-level `footer` keeps its precedence, matching the per-slot source behavior. Also proposes an optional `page_template_source` field on `POST /render` (D4 — agent judgment beyond the issue's ask, open to question, severable into a follow-up).

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Medium |

Related: #80 (the removal, closed), #63/#77 (slot model), #37 (asset resolution — reused as-is), #65/#89 (margins) and #92 (file-form fonts) as post-removal document-level settings the mode must not bypass. No open plans conflict; plan verified against `main` at `24e81a6`.

## Plan Review

**Status:** Reviewed

Reviewed: 2026-08-31. Feedback applied: made recipe-footer precedence and the `page_numbers` plumbing explicit (a top-level `data.footer` still wins over the custom footer slot); corrected the server error-mapping facts (core `ValueError` already → 400; oversized source → 400, not 413) and dropped the redundant endpoint-side conflict check; centralized mutual exclusion in `load_page_template()`; placed restored tests by their historical files and added forwarding to both `_render_tex` helpers; `is_file()` hardening for autodetection; refreshed stale triage (#86 is merged) and raised risk to Medium.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress log
