# Implementation Plan: Template: kvitto (receipt)

## Summary

Add a new `kvitto` (receipt) template to klartex. The kvitto template is simpler than the existing faktura template -- no VAT breakdown, fewer fields, lighter layout. Suitable for foreningar and small businesses.

## Triage Info

> Decision-support metadata for this issue.

| Field | Value |
|-------|-------|
| **Blocked by** | None |
| **Blocks** | None |
| **Related issues** | #1 (faktura design improvements), #7 (more header layouts) |
| **Scope** | 6 files across `templates/`, `tests/`, docs |
| **Risk** | Low |
| **Complexity** | Low |
| **Safe for junior** | Yes |
| **Conflict risk** | Low -- #7 will add header enum values to all schema.json files, but since kvitto creates a new schema.json, no merge conflict expected |

### Triage Notes

No blockers or dependencies. The kvitto template follows the exact same pattern as the existing faktura, protokoll, and avtal templates. The registry auto-discovers templates via `discover_templates()`, so no Python code changes are needed -- just adding the template directory with `schema.json` and `kvitto.tex.jinja`.

Issue #7 (more header layouts) will add new values to the `header` enum in all schemas. When kvitto is created, it should include the current three values (`standard`, `minimal`, `none`). If #7 lands first, the new values should be added to kvitto's schema as well, but this is a trivial follow-up.

## Analysis

The existing template system works as follows:

1. **Auto-discovery**: `klartex/registry.py` scans `templates/*/schema.json` for subdirectories containing a schema and matching `.tex.jinja` file. No registration code needed.
2. **Schema validation**: Data is validated against `schema.json` before rendering.
3. **Template rendering**: Jinja2 with LaTeX-safe delimiters renders the `.tex.jinja` file.
4. **Branding/headers**: Templates include `_branding_preamble.jinja` and a `_header_{layout}.jinja` snippet via Jinja2 line statements.
5. **Base class**: All templates use `\documentclass{klartex-base}` which provides A4 layout, fonts, packages (tabularx, booktabs, etc.), and utility commands.

A kvitto is significantly simpler than a faktura:
- No line items with quantity/unit/unit_price breakdown
- No VAT calculation
- Single total amount
- Fewer metadata fields (no due_date, no payment_terms)
- Payment confirmation rather than payment request

Key design choices for the kvitto:
- **Total amount** is a single field (no line-item computation needed)
- **Items** are a simple list of descriptions (optionally with amounts) -- not the full quantity/unit/price model
- **Payment method** is a simple string (e.g., "Kontant", "Swish", "Kort")
- No VAT breakdown (as stated in the issue)
- Receipt number instead of invoice number

## Implementation Steps

### Phase 1: Create schema.json

1. Create `templates/kvitto/schema.json`
   - Required fields: `receipt_number`, `date`, `total_amount`, `items`
   - Optional fields: `header`, `currency`, `payment_method`, `paid_by` (customer name), `seller` (seller info), `note`
   - Items are simplified: just `description` and optional `amount`
   - Follow the same JSON Schema draft-07 pattern as other templates

### Phase 2: Create kvitto.tex.jinja

1. Create `templates/kvitto/kvitto.tex.jinja`
   - Use `\documentclass{klartex-base}` base class
   - Include branding preamble and header layout (same pattern as faktura)
   - Lighter layout than faktura:
     - Centered "KVITTO" title
     - Receipt number and date
     - Simple items table (description + optional amount)
     - Total amount prominently displayed
     - Payment method
     - Optional seller info and buyer name
     - Optional note

### Phase 3: Test fixture and test updates

1. Create `tests/fixtures/kvitto.json` -- a sample kvitto with all fields populated
   - Follow the pattern of existing fixtures (`faktura.json`, `protokoll.json`, `avtal.json`)
2. Update `tests/test_schemas.py`:
   - Add `"kvitto"` to `test_discover_all_templates` assertions
   - Add `"kvitto"` to the `@pytest.mark.parametrize` list in `test_fixture_validates`
3. Update `tests/test_api.py`:
   - Add `assert "kvitto" in names` to `test_list_templates`

### Phase 4: Documentation

1. Update `README.md` -- add kvitto row to the template table
2. Update `README.en.md` -- add kvitto row to the English template table

### Phase 5: Manual verification

1. Render with the CLI:
   ```bash
   klartex render -t kvitto -d tests/fixtures/kvitto.json -o test-kvitto.pdf
   ```
2. Run tests:
   ```bash
   pytest tests/
   ```
3. Verify:
   - Template appears in `klartex templates` listing
   - Schema is accessible via `klartex schema kvitto`
   - PDF renders correctly with default branding
   - All tests pass

## Files Summary

| File | Action | Purpose |
|------|--------|---------|
| `templates/kvitto/schema.json` | Create | JSON Schema for kvitto data validation |
| `templates/kvitto/kvitto.tex.jinja` | Create | LaTeX/Jinja2 template for receipt rendering |
| `tests/fixtures/kvitto.json` | Create | Sample data fixture for testing |
| `tests/test_schemas.py` | Modify | Add kvitto to discovery and validation tests |
| `tests/test_api.py` | Modify | Add kvitto to API template listing test |
| `README.md` | Modify | Add kvitto to template table |
| `README.en.md` | Modify | Add kvitto to English template table |

## Codebase Areas

- `templates/kvitto/` (new template directory)
- `tests/` (fixtures and test assertions)
- Root docs (`README.md`, `README.en.md`)

## Design Decisions

> Non-trivial choices made during planning. Feedback welcome; otherwise implementation proceeds with these.

### 1. Simple items list vs. line-item breakdown

**Options:** (A) Full line items with quantity/unit/price like faktura, (B) Simple list of description + optional amount
**Decision:** B -- Simple list
**Rationale:** The issue explicitly states "lighter layout, fewer fields, no VAT breakdown needed." A receipt confirms what was paid, not an itemized commercial document. If someone needs full itemization, they should use the faktura template.

### 2. Items with optional individual amounts vs. descriptions only

**Options:** (A) Each item has a required amount, (B) Each item has an optional amount, (C) Items are just strings
**Decision:** B -- Optional amounts per item
**Rationale:** Some receipts list items with prices, others just describe what was purchased with a single total. Optional amounts provide flexibility. When individual amounts are provided, they serve as informational context -- the `total_amount` field is the authoritative total (no auto-sum).

### 3. Total amount as single field vs. computed from items

**Options:** (A) Compute total from item amounts, (B) Explicit total_amount field
**Decision:** B -- Explicit total_amount
**Rationale:** Since item amounts are optional and there is no VAT breakdown, computing the total would be unreliable. An explicit total is simpler and always correct. This also matches the "lighter" philosophy.

### 4. Seller info structure

**Options:** (A) Detailed seller object with name/org_number/address, (B) Simple seller name string, (C) Rely entirely on branding for seller identity
**Decision:** C with optional override -- Branding provides the seller identity (org name, logo, etc. in the header). An optional `seller_note` string field allows adding extra seller info (e.g., "Kassör: Anna Andersson") if needed beyond what branding provides.
**Rationale:** Avoids duplicating branding info. The header layout already shows the organization. A free-text note covers edge cases.

## Verification Checklist

- [ ] Template auto-discovered by registry (appears in `klartex templates`)
- [ ] Schema validates correctly (required fields enforced, optional fields work)
- [ ] PDF renders with minimal data (only required fields)
- [ ] PDF renders with full data (all optional fields populated)
- [ ] PDF renders with default branding
- [ ] PDF renders with custom branding
- [ ] Header layout selection works (standard/minimal/none)
- [ ] LaTeX special characters in data are escaped properly
- [ ] Receipt looks clean and professional -- lighter than faktura
- [ ] Test fixture `tests/fixtures/kvitto.json` validates against schema
- [ ] `pytest tests/` passes with kvitto added to test assertions
- [ ] README template table includes kvitto
