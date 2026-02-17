# Implementation Plan: Improve faktura template design

## Summary

Polish the faktura (invoice) template with better spacing, alignment, and typography to produce a more professional-looking Swedish invoice PDF. This is a template-only change -- no Python code, CLI, or API changes needed.

## Triage Info

> Decision-support metadata for this issue.

| Field | Value |
|-------|-------|
| **Blocked by** | None |
| **Blocks** | None |
| **Related issues** | None |
| **Scope** | 1 file: `templates/faktura/faktura.tex.jinja` |
| **Risk** | Low |
| **Complexity** | Low-Medium |
| **Safe for junior** | Yes |
| **Conflict risk** | Low (no other plans exist) |

### Triage Notes
No blockers or dependencies. This is a standalone visual improvement to the faktura Jinja template. The base class (`cls/klartex-base.cls`) should not need changes -- all styling will use existing packages and LaTeX primitives available in the template.

## Analysis

The current `faktura.tex.jinja` is functional but has several areas where visual polish would improve the result:

1. **Title area** -- "FAKTURA" title is right-aligned with `\flushright`, which is unconventional for Swedish invoices. Most Swedish invoices have the title prominently placed at the top-left or center, often with a larger font size.

2. **Recipient/reference block** -- The two-column `minipage` layout (0.45/0.45) works but lacks visual separation. The "Mottagare" label could be more prominent and the reference fields on the right side need better vertical alignment with the recipient block.

3. **Line items table** -- The `tabularx` table with column spec `Xrrrrr` is functional but could benefit from:
   - Better column width ratios (description column too wide relative to numeric columns)
   - Right-aligned currency values are already in place via `r` columns -- verify consistent `{:,.2f}` formatting
   - More breathing room between rows via `\arraystretch`
   - Better horizontal rule usage (already has `\toprule`/`\midrule`/`\bottomrule` from booktabs)

4. **Totals section** -- The right-aligned summary table works but could be visually stronger. The "Att betala" (total to pay) line should stand out more.

5. **Payment info** -- The `tabular` block is plain. Could benefit from a rule separator to set it apart from the rest of the document.

6. **General typography** -- The base class uses 10pt with 1.3 line spacing, which is fine. The invoice could benefit from using `\small` or `\footnotesize` for certain metadata fields to create better visual hierarchy.

## Implementation Steps

### Phase 0: Generate baseline PDF

1. Render the current template to establish a visual baseline
   - Run: `klartex render -t faktura -d tests/fixtures/faktura.json -o /tmp/faktura-before.pdf`
   - Save for side-by-side comparison after changes

### Phase 1: Restructure invoice header area

1. Move "FAKTURA" title to a more prominent position
   - Use a two-column layout: title on the left (large, bold), metadata on the right
   - Put invoice number, date, and due date in a right-aligned `tabular`
   - Files to modify: `templates/faktura/faktura.tex.jinja`

2. Improve the invoice metadata layout
   - Use `brandsecondary` color for metadata labels to create visual hierarchy
   - Keep the title in `brandprimary` or default black for prominence

### Phase 2: Improve recipient and reference blocks

1. Adjust the two-column layout
   - Keep `minipage` approach but improve spacing
   - Make "Mottagare" section header more prominent (slightly larger or colored)
   - Add a thin `\rule` or vertical space to separate from header area
   - Files to modify: `templates/faktura/faktura.tex.jinja`

### Phase 3: Polish line items table

1. Improve table formatting
   - Adjust column spec for better width distribution (e.g., `X@{\hspace{0.6em}}r@{\hspace{0.6em}}r@{\hspace{0.6em}}r@{\hspace{0.6em}}r@{\hspace{0.6em}}r`)
   - Add `\renewcommand{\arraystretch}{1.3}` before the table for row padding
   - Ensure right-alignment of all numeric columns is consistent (already `r` columns)
   - Files to modify: `templates/faktura/faktura.tex.jinja`

2. Format currency values
   - Use consistent `{:,.2f}` formatting (already present, verify rendering)
   - Note: True decimal-point alignment would require `siunitx` package; the existing right-alignment with consistent formatting is sufficient for this issue

### Phase 4: Enhance totals section

1. Make the totals block more prominent
   - Increase font weight or size for the "Att betala" line
   - Add a thicker rule or double rule above the final total
   - Files to modify: `templates/faktura/faktura.tex.jinja`

### Phase 5: Improve payment information block

1. Visually separate payment info
   - Add a horizontal rule above the payment section
   - Make "Betalningsinformation" header slightly larger or use `brandsecondary` color
   - Files to modify: `templates/faktura/faktura.tex.jinja`

### Phase 6: Final typography and verification

1. Review overall visual hierarchy
   - Ensure consistent use of `\textbf`, `\textit`, font sizes
   - Verify spacing between sections is balanced (`\vspace` values)
   - Check that the note at the bottom has appropriate styling
   - Files to modify: `templates/faktura/faktura.tex.jinja`

2. Test with fixture data across configurations
   - Render with default branding: `klartex render -t faktura -d tests/fixtures/faktura.json -o /tmp/faktura-after-default.pdf`
   - Render with example branding: `klartex render -t faktura -d tests/fixtures/faktura.json -b example -o /tmp/faktura-after-example.pdf`
   - Compare `/tmp/faktura-before.pdf` with the after versions side-by-side

3. Test edge cases
   - Verify all three header modes work: `header=standard`, `header=minimal`, `header=none`
   - Test with minimal data (no reference, no payment terms, no payment method fields)
   - Test with long description text and many line items (page-break behavior)
   - Test with note absent

## Files Summary

| File | Action | Purpose |
|------|--------|---------|
| `templates/faktura/faktura.tex.jinja` | Modify | Main template -- all visual changes |
| `tests/fixtures/faktura.json` | No change | Test data for verifying output |

## Codebase Areas

- `templates/faktura/`

## Design Decisions

> Non-trivial choices made during planning. Feedback welcome; otherwise implementation proceeds with these.

### 1. Keep changes within the template only
**Options:** (A) Modify only `faktura.tex.jinja` vs (B) Also modify `cls/klartex-base.cls` with invoice-specific commands
**Decision:** A -- template only
**Rationale:** The base class is shared across all document types. Invoice-specific layout belongs in the template. If reusable patterns emerge, they can be extracted to the cls later.

### 2. Use subtle color accents from branding
**Options:** (A) Pure black/white invoice vs (B) Use `brandsecondary`/`brandaccent` for labels and separators
**Decision:** B -- use brand colors where appropriate
**Rationale:** The branding system already provides colors. Using them for section headers and labels makes the invoice look more professional and consistent with the brand. Keep it subtle -- avoid heavy color usage.

### 3. No additional LaTeX packages
**Options:** (A) Add packages like `siunitx` for decimal alignment or `colortbl` for row coloring vs (B) Use only packages already in `klartex-base.cls`
**Decision:** B -- stick with existing packages
**Rationale:** The base class already includes `xcolor`, `booktabs`, `tabularx`, `fancyhdr`, etc. Right-aligned `r` columns with consistent `{:,.2f}` formatting provide good-enough numeric alignment without `siunitx`. Row shading is not needed -- clean rules from `booktabs` are sufficient for a professional invoice look. Adding packages increases complexity and potential conflicts.

### 4. Title placement: left-aligned with right metadata
**Options:** (A) Centered title vs (B) Left title + right metadata vs (C) Keep right-aligned
**Decision:** B -- left title with right-aligned metadata
**Rationale:** Most Swedish invoices follow this pattern. It creates a natural reading flow and pairs well with the branding header.

## Verification Checklist

- [ ] Baseline PDF generated before changes
- [ ] "FAKTURA" title is prominently placed with clear visual hierarchy
- [ ] Invoice metadata (number, date, due date) is well-structured
- [ ] Recipient and reference blocks are clearly separated and aligned
- [ ] Line items table has good column spacing and row padding
- [ ] Numeric values are right-aligned with consistent formatting
- [ ] Totals section clearly highlights the amount to pay
- [ ] Payment information is visually distinct from the rest
- [ ] Note section renders correctly when present and absent
- [ ] Template renders correctly with default (empty) branding
- [ ] Template renders correctly with example branding
- [ ] Template renders correctly with all three header modes (standard, minimal, none)
- [ ] Template handles missing optional fields (no reference, no payment terms, no payment methods)
- [ ] Template handles long descriptions and many line items without layout breakage
- [ ] No LaTeX compilation errors
- [ ] Side-by-side comparison confirms visual improvement over baseline
