# Issue #65: Expose page margins on the page-template surface

**Branch from:** main

## Summary

Adds a structured `margins` setting (`top`/`bottom`/`left`/`right`, LaTeX dimension strings) to the `page_template` surface, on both render paths. The values mean **text-block margins** — the distance from the paper edge to the body text — and the chrome geometry adapts: `top` is emitted as both a `headsep` adjustment (header present, band anchored as today) and a `\kxreclaimtop` renewal (header reclaimed), letting the existing LaTeX-time `\ifdefempty` reclaim pick the regime, which is the "interplay with the chrome geometry" the issue demands. The setting rides the `DOCUMENT_SETTINGS` machinery (schema subtree, key allow-list and `klartex schema _block` come for free), is strictly pattern-validated (injection-safe, escape-proof), applies in every mode with custom slot sources winning like they do for `font`, and leaves faktura/kvitto's `narrowmargins` class option in place as the recipe default that explicit margins override. The columns footer's forced bottom geometry (`klartex-footer.sty`) becomes late-bound macros so an explicit `bottom` wins there too. Touches `page_templates.py`, `_page_template.tex.jinja`, `klartex-footer.sty`, five test files (including a delta-based `pdftotext -bbox` layout check) and the READMEs/CLAUDE.md; no schema files change by hand.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Medium |

Issue is open, unlabeled, unassigned, no comments, and there is no `agent-docs/github/project.json` (no board fields). No blockers: the referenced #63 (slot model) is closed and shipped in v0.16.0/v0.17.0. Related open issues from the same template-editor design session share the surface but not the work: #61 (typography — will add sibling `DOCUMENT_SETTINGS` entries), #62 (footer layout), #64 (variant naming), #66 (`title_page` chrome), #67 (page numbers), #79 (faktura/kvitto footer migration — merge-coordination overlap, not a blocker), plus #85 (whole-page custom source — its planning owns the settings-vs-whole-page interaction) and #84 (letterhead layout bug). No open plan touches `klartex/page_templates.py` or the composition include, so no plan-file conflicts. Risk is Medium: the change is additive (no existing payload changes shape, no defaults move) but sits in the geometry/reclaim ordering, which is guarded by new ordering tests and a cls-lock extension. Eight design calls are agent judgment (D1–D8 in the plan), flagged for the PR body — chiefly the text-block-margin semantics, dimension-string typing, the dual-regime `top` emission, the conditional minimum-`top` validation and the late-bound columns-footer bottom geometry.

## Plan Review

**Status:** Reviewed

**Reviewed:** 2026-08-31

**Feedback:** Two codex passes. First pass applied: `\setlength{\headwidth}{\textwidth}` sync when side margins change (fancyhdr does not track a later `\textwidth` change), exact `Fraction`-based unit conversion with a strict `top > 2.1cm` boundary, explicit null/empty/zero contract for `margins`, a sum-based cls↔Python constant sync test instead of literal assertions, a measurable `pdftotext -bbox` layout test, mandatory schema-surface tests, footer-clipping risk widened beyond the columns footer, and #79 added to related issues. Second pass applied: `\kxfooter`'s forced `bottom=3.6cm, footskip=2.6cm` (klartex-footer.sty:96) would override `margins.bottom`, resolved with late-bound `\kxfooterbottom`/`\kxfooterfootskip` macros (new D8); the `margins` schema made object-or-null to match the loader; the bbox test switched to positional deltas since absolute first-word coordinates include `\topskip` and font metrics. Not adopted: marking the plan not-ready until design calls are pre-approved (the repo convention is flagging agent judgment in the PR body) and removing the `progress.md` link (repo template convention — the file is created at work time).

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress log
