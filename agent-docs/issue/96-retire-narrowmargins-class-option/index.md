# Issue #96: Re-express the invoice recipes' margins through the margins surface and retire the narrowmargins class option

**Branch from:** main

## Summary

faktura and kvitto keep their 2cm side margins and 1.7cm reclaimed text top, but declare them as recipe-default `page_template.margins` in `recipe.yaml`, merged key by key under the payload's own `margins` in `load_page_template` (via the existing `defaults` parameter). The `narrowmargins` documentclass option, `document.class_options` in the recipe schema and `RecipeDocument`, the `"class_options"` context key and the `\documentclass[...]` arm in `_recipe_base.tex.jinja` are removed. The faktura golden changes by exactly the `\documentclass` line plus the three emitted margin lines; a PDF text-layer test locks the 2cm body-text edge so the PDFs do not move. Breaking edge (agent judgment, Design Decision 3): a faktura/kvitto payload that adds a rendering predefined header must now also send `margins.top > 2.1cm`, and a custom header source without its own `\geometry` receives the 1.7cm top — klartex.se is checked for these shapes before the release. No `CHANGELOG.md` change in the PR; the entry is written at release from the PR body.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Medium |
| **Blocked by** | None |
| **Related** | #65 (margins surface, merged — the mechanism this builds on), #86/#88 (introduced the option in 0.18.0), #99 (closed; shared files, already merged) |

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-09-03
**Feedback:** Codex flagged the tension between "PDFs must not move" and the rendering-header edge of Design Decision 3; the plan now scopes invariance to the reclaimed-header geometry the option actually shaped, raises the risk to Medium, and adds a klartex.se pre-release check. Applied: `test_header_slot_settings_reach_the_recipe_path` gets `margins.top`, plus tests for `header_source`/`page_template_source` with and without geometry; the PDF invariance test commits `(x, y)` for a body-only word instead of "leftmost word"; `null`/`{}` inherit the defaults (new Design Decision 7); `README.en.md`, the `recipe.py:64` comment, `CLAUDE.md` and the stale golden-test docstring added; the `Unreleased` changelog step dropped in favour of the release-time flow; golden update moved after the post-change render; the cls assertion narrowed to `narrowmargins`.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress log
