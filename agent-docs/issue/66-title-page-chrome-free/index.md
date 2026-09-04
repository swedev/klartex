# Issue #66: `title_page` should render a fully chrome-free page (no header, no footer)

**Branch from:** main

## Summary

Makes a `title_page` block its own page and renders it without header or footer, in every chrome mode (predefined slots, per-slot custom sources, whole-page source): `\makedoctitle` in `klartex-titelsida.sty` opens with `\clearpage\thispagestyle{empty}` (a no-op break at document start) and drops its `\thispagestyle{fancy}`. With the title-page case owned by the block, the header-only `first_page_header` setting is removed from the page-template surface — `DOCUMENT_SETTINGS`, `PageTemplate`, the loader default and composition step 5 (the `plain` redefinition) go, so the key is rejected by the generated schema and the loader like #67's top-level `page_numbers`. The `empty_header` golden loses its two `plain` lines, the `first_page_header` tests are rewritten as rejection tests, and new `pdftotext`-based tests assert chrome absent on page 1 and present on page 2. README/CLAUDE.md drop the key; CHANGELOG gets a breaking-change and a fix entry under `Orealiserat`.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Medium |

Issue is open, unlabeled, unassigned, no comments; no `agent-docs/github/project.json`, so no board fields or branch alignment. No blockers: the slot model (#63), page numbers (#67) and margins (#65) it builds on are merged. Open issues on the same surface without plans — #61 (typography) and #62 (footer layouts) — will touch `page_templates.py` and the footer fragments later but not the lines removed here. No open plan conflicts. Risk is Medium because two visible changes ship at once: existing documents that pair `title_page` with chrome lose it on the title page (the requested behaviour), and `first_page_header` goes from accepted to rejected — mitigated by the loud pathed error and by verifying that the only consumer, `klartex.se`, never sends the key in code (its `llms.txt`/`backend/README.md` mention it and need a follow-up there). Agent-judgment calls: D1's location of the change, D2's custom-source corollary, D3 (remove rather than keep/generalise the key — delegated to planning by the issue), D5 (page numbering untouched).

## Plan Review

**Status:** Reviewed

**Reviewed:** 2026-09-04

**Feedback:** Two codex passes. First pass applied: a leading `\clearpage` in `\makedoctitle` so a mid-document `title_page` does not strip the chrome from the preceding content's page, with the empty style set before the title content; D3 states the removal of `first_page_header` as a deliberate capability loss (header-less first page without a title page); a whole-page-source PDF case and a mid-document case added to the tests; `_pages`/`requires_tools` reused from `test_pdf_text_layer.py`; schema-absence asserted across every template; the Jinja step ordered before the dataclass-field removal (an undefined attribute is falsy in Jinja and would emit `plain` for every predefined header); the stale `page_numbers` mention in CLAUDE.md line 96 and in `klartex.se`'s docs noted for correction; the misleading `-k "not xelatex"` checkpoint replaced with explicit test files. Second pass: ready; codex compiled the TeX sequence and confirmed `\clearpage` produces no blank page at document start or after a preceding title page's `\newpage`, and that `\thispagestyle{empty}` governs the title page only.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress log
