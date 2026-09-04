# Issue #67: Page numbers: auto/on/off, as a setting on the slot that carries them

**Branch from:** main

## Summary

Replaces the document-level boolean `page_template.page_numbers` with a tri-state `"auto" | "on" | "off"` (default `auto` — page numbers only when the document has more than one page) that sits on the footer slot carrying the numbers: both the `pagenumber` and the `columns` variant get it among their settings. The global key is removed with no alias (breaking). The LaTeX-time page-count test moves into one shared class macro, `\kxifpagenumbers`, used by the `pagenumber` fragment and `klartex-footer.sty`; the composition stops special-casing page numbers. Verified premise correction: today only the columns footer has the "more than one page" rule — the `pagenumber` footer prints `Sida 1 av 1` on one-page documents, so the `auto` default changes what a one-page block or protokoll document shows in its footer. klartex.se must drop its top-level `page_numbers` before the release that ships this.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Medium |
| **Blocked by** | None for implementation (#63, the slot model this builds on, is closed). Release dependency: swedev/klartex.se must stop emitting a top-level `page_numbers` before the release that ships this |
| **Related** | #63 (closed; reserved `page_numbers` on the footer slot for this issue), #62 (open; footer layout options, same sty), #66 (open; `first_page_header`/title-page chrome, neighbouring lines in the composition) |
| **Issue metadata** | No labels, no assignee, no comments, no project item |

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-09-04
**Feedback:** Codex corrected the server error-path expectation (`detail.path` is the containing object, `["page_template"]`), completed the rendered-PDF matrix for the `columns` variant including a faktura case through the `fields_from` merge, fixed the schema-test description (the boolean slot case was already rejected), reordered the implementation so the model lands before the fragments and marked steps 5–8 atomic, added the requirement that `\kxifpagenumbers` expand its mode argument (literal from the fragment, macro from the sty), replaced the invalid `klartex templates` check with `klartex schema _block`, refreshed stale line references, and separated "implementation unblocked" from the klartex.se release dependency.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress log
