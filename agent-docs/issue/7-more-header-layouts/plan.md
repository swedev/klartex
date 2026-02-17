# Implementation Plan: More Header Layouts

## Summary

Add three new header layout options to klartex: **centered**, **banner**, and **compact**. Currently, the system supports three layouts (standard, minimal, none) via Jinja2 include files and JSON schema enum validation. This issue adds three more layouts following the same pattern.

## Triage Info

> Decision-support metadata for this issue.

| Field | Value |
|-------|-------|
| **Blocked by** | None |
| **Blocks** | None |
| **Related issues** | None |
| **Scope** | 9 files across templates/, tests/ |
| **Risk** | Low |
| **Complexity** | Low |
| **Safe for junior** | Yes |
| **Conflict risk** | Low (plan #1 touches faktura template body, not header includes or schemas) |

### Triage Notes
No blockers or dependencies. This is a self-contained feature addition that follows an established pattern. Each new layout is an independent Jinja2 snippet that slots into the existing `_header_{name}.jinja` convention.

## Analysis

The header layout system works as follows:

1. **Schema validation**: Each template's `schema.json` has a `header` field with `enum: ["standard", "minimal", "none"]`. This controls which values are accepted.
2. **Template include**: Each `.tex.jinja` template includes the header via a Jinja2 line statement:
   ```
   %% include '_header_' ~ data.get('header', 'standard') ~ '.jinja'
   ```
3. **Header snippets**: Files like `_header_standard.jinja` define `\fancyhead` and `\fancyfoot` commands wrapped in `\makeatletter`/`\makeatother`.
4. **Base class**: `klartex-base.cls` sets up `fancyhdr` with empty headers/footers and zero rule widths. The header snippets override these.

Key conventions from existing headers:
- All snippets use `\makeatletter` / `\makeatother` (needed for `\wf@` internal commands)
- Font size: 6pt/9pt for header/footer text
- Colors: `brandsecondary` for text, `brandprimary` for main content
- Footer always includes page numbers via `\wf@page \thepage \wf@of \pageref{LastPage}`
- Logo height: 0.855cm with -0.6cm vertical adjustment
- `\ifdefempty` (from etoolbox) for conditional checks on brand fields

## Implementation Steps

### Phase 1: Create Header Snippets

1. Create `templates/_header_centered.jinja`
   - Center the org name at top
   - Center the logo below (or above) the org name
   - Standard page-number footer
   - Use `\fancyhead[C]{}` for centered positioning

2. Create `templates/_header_banner.jinja`
   - Full-width colored banner using `brandprimary` as background
   - White text for org name
   - Logo on the right side of the banner
   - Uses `\colorbox` or `tikz` for the banner background
   - Standard page-number footer
   - Note: May need `\RequirePackage{tikz}` in the snippet or cls. Prefer `\colorbox` from xcolor (already loaded) to avoid adding a dependency.

3. Create `templates/_header_compact.jinja`
   - Single-line header with org name on the left and page number on the right
   - No footer (page number is in the header)
   - Minimal vertical space

### Phase 2: Update Schemas

4. Update `templates/protokoll/schema.json`
   - Add `"centered"`, `"banner"`, `"compact"` to the `header` enum

5. Update `templates/faktura/schema.json`
   - Same enum update

6. Update `templates/avtal/schema.json`
   - Same enum update

### Phase 3: Add Tests

7. Add test fixtures / parametrized tests in `tests/test_schemas.py`
   - Verify that each new header value passes schema validation for all three templates
   - Optionally add a test that invalid header values are rejected

### Phase 4: Documentation

8. Update the README (Swedish) to document the new layout options
   - Add descriptions and visual guidance for when to use each layout

## Files Summary

| File | Action | Purpose |
|------|--------|---------|
| `templates/_header_centered.jinja` | Create | Centered org name and logo header |
| `templates/_header_banner.jinja` | Create | Full-width colored banner header |
| `templates/_header_compact.jinja` | Create | Single-line compact header |
| `templates/protokoll/schema.json` | Modify | Add new header enum values |
| `templates/faktura/schema.json` | Modify | Add new header enum values |
| `templates/avtal/schema.json` | Modify | Add new header enum values |
| `tests/test_schemas.py` | Modify | Add validation tests for new layouts |
| `README.md` | Modify | Document new header layouts |

## Codebase Areas

- `templates/` (header snippets and schema files)
- `tests/` (schema validation tests)

## Design Decisions

> Non-trivial choices made during planning. Feedback welcome; otherwise implementation proceeds with these.

### 1. Banner Implementation Without tikz
**Options:** Use `tikz` for the banner background vs. `\colorbox` / `\fcolorbox` from xcolor
**Decision:** Use `\colorbox` from xcolor (already a dependency)
**Rationale:** Avoids adding tikz as a dependency, which is heavyweight. A `\colorbox` with `\makebox[\textwidth]` can achieve a full-width colored bar. If more complex gradients or shapes are needed later, tikz can be reconsidered.

### 2. Compact Layout Footer vs Header Page Numbers
**Options:** Keep page numbers in the footer (like other layouts) vs. move to header
**Decision:** Move page number to the header right side, remove footer
**Rationale:** The "compact" layout is described as "single-line header with org name and page number". This implies the page number lives in the header. Having an empty footer saves vertical space, which is the point of "compact".

### 3. No Changes to klartex-base.cls
**Options:** Add new packages to the cls vs. keep changes in snippets only
**Decision:** Keep all changes in Jinja2 snippets, no cls modifications
**Rationale:** The current pattern keeps the cls minimal and generic. Header snippets are self-contained. If banner needs additional packages, use `\RequirePackage` within the snippet (LaTeX allows this in the preamble, and the snippets are included before `\begin{document}`).

## Verification Checklist

- [ ] All three new header snippets render without LaTeX errors
- [ ] Schema validation accepts "centered", "banner", "compact" for all templates
- [ ] Schema validation still rejects invalid header values
- [ ] Centered layout: org name and logo centered, page number in footer
- [ ] Banner layout: colored banner with white text, logo visible, page number in footer
- [ ] Compact layout: single-line header with org name + page number, no footer
- [ ] Existing layouts (standard, minimal, none) still work unchanged
- [ ] Tests pass: `pytest tests/`
- [ ] Each layout degrades gracefully when brand fields are empty (no logo, no org name)
