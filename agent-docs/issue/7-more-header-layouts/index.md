# Issue #7: More Header Layouts

**Based on:** main
**Status:** Superseded

## Summary

~~Add three new header layout options -- centered, banner, and compact -- to complement the existing standard, minimal, and none layouts.~~

**Superseded:** The page template system was redesigned. Instead of `_header_{name}.jinja` include files selected via schema enum, page templates are now self-contained `.tex.jinja` files whose source is injected directly into the preamble. Custom layouts are achieved by writing a page template file and passing it via `--page-template` (CLI) or `page_template_source` (API). There is no longer a need to add header layouts to the codebase — users create their own.

## Related Files

- [plan.md](plan.md) - Original implementation plan (outdated)
