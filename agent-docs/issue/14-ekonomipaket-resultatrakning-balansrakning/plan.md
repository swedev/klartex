# Implementation Plan: Ekonomipaket -- resultatrakning, balansrakning, budgetrapport

## Summary

Create four new financial document templates (resultatrakning, balansrakning, budgetrapport, SIE-exportrapport) as YAML recipes using the composable architecture from #9 and the economic components from #12. Each template combines existing economic components (e.g., `klartex-resultatrakning.sty`, `klartex-budgettabell.sty` — exact names TBD per #12) with standard document structure to produce standalone financial PDF reports.

## Triage Info

> Decision-support metadata for this issue.

| Field | Value |
|-------|-------|
| **Blocked by** | #9 Composable architecture (OPEN), #12 Ekonomikomponenter (OPEN) |
| **Blocks** | None |
| **Related issues** | #1 (faktura), #8 (kvitto), #11 (foreningskomponenter) |
| **Scope** | ~18 files across `templates/`, `tests/`, docs |
| **Risk** | Medium -- depends on two unfinished prerequisites |
| **Complexity** | Medium |
| **Safe for junior** | Yes (once #9 and #12 are done and patterns are established) |
| **Conflict risk** | Medium -- #9 defines recipe format, #12 creates components; overlaps with #11 on `tests/test_renderer.py`, `tests/test_schemas.py` |

### Triage Notes

This issue has two explicit blockers:

1. **#9 (Composable architecture)** -- Defines the YAML recipe engine and `.sty` component pattern. Without this, templates cannot be defined as recipes.
2. **#12 (Ekonomikomponenter)** -- Creates `resultatrakning.sty`, `budgettabell.sty`, and `notapparat.sty`. Without these components, the templates have nothing to compose.

Both blockers are currently OPEN. This plan assumes the architecture and component interfaces from #9 and #12 respectively. The plan should be reviewed and potentially updated once those issues are resolved.

The issue also mentions relevance to [OpenVera](https://github.com/swedev/openvera) for structured accounting data to PDF conversion. This is informational context -- no direct code dependency.

Issue #11 (foreningskomponenter) is a sibling issue also blocked by #9, touching similar areas (`cls/`, recipe YAML). While #11 creates different components (dagordning, namnrollista), both plans modify `tests/test_renderer.py` and `tests/test_schemas.py`. Whichever lands second should rebase on top of the other. The merge conflicts will be trivial (additive test assertions).

## Analysis

### Templates to Create

The issue defines four templates, each as a YAML recipe + JSON schema:

1. **Resultatrakning** (Income Statement) -- Financial table with comparison years, group subtotals, and note references. Uses the `resultatrakning` component from #12.
2. **Balansrakning** (Balance Sheet) -- Same table format as resultatrakning but organized as assets/liabilities/equity. Also uses the `resultatrakning` component (same tabular structure).
3. **Budgetrapport** (Budget Report) -- Budget table with account codes, budgeted amounts, actuals, and percentages. Uses the `budgettabell` component from #12. May include commentary sections.
4. **SIE-exportrapport** (SIE Export Report) -- Readable PDF representation of SIE4 accounting data. Uses the `resultatrakning` component plus export metadata display.

### Architecture Assumptions (from #9)

Based on the plan for #9:
- Templates can be defined as YAML recipes in `templates/{name}/recipe.yaml`
- Each recipe declares `components` (ordered list), `content_fields`, and references a `schema`
- The recipe engine assembles LaTeX by loading `.sty` packages and calling their macros
- JSON Schema validation happens before rendering (same as current templates)
- The registry auto-discovers recipe-based templates alongside monolithic ones

### Component Interfaces (from #12)

Based on issue #12's specification:

**resultatrakning.sty** expects:
- `rubrik_ar1`, `rubrik_ar2` (column headers, e.g., "2025", "2024")
- `grupper` array with `rubrik`, `poster` (each with optional `notref`, `post`, `belopp_ar1`, `belopp_ar2`), and `summa`

**budgettabell.sty** expects:
- `rubrik_budget`, `rubrik_ar1`, `rubrik_ar2` (column headers)
- `poster` array with optional `konto`, `post`, `budget`, `utfall_ar1`, `utfall_ar2`, optional `procent`

**notapparat.sty** expects:
- `noter` array with `notnr` and `text`

### Template Structure Pattern

Each financial template follows a consistent pattern:
1. Header with document title and period
2. One or more financial table components
3. Optional notes section
4. Optional commentary/metadata

## Implementation Steps

### Phase 0: Dependency Sync Gate

Before starting implementation, verify that both blockers have landed and confirm the actual interfaces.

1. Verify #9 (composable architecture) is merged
   - Confirm `recipe.yaml` discovery works in `klartex/registry.py`
   - Confirm the recipe rendering path exists in `klartex/renderer.py` (engine selection: `auto`/`legacy`/`recipe`)
   - Note the actual recipe YAML format (fields, structure)
   - Note the actual component naming convention (e.g., `klartex-resultatrakning.sty` vs `resultatrakning.sty`)
   - Note the escaping contract (data escaped before Jinja rendering, per #9 design decision)

2. Verify #12 (ekonomikomponenter) is merged
   - Confirm `resultatrakning.sty`, `budgettabell.sty`, and `notapparat.sty` exist
   - Note their actual file locations (e.g., `cls/` vs `cls/komponenter/`)
   - Note their actual LaTeX macro names and input data keys
   - Note the component mapping entries in `klartex/components.py`

3. Update this plan if interfaces differ from assumptions
   - The component interfaces documented below are based on issue #12's specification, which has no local plan yet. Actual implementation may differ.
   - Update schema field names, recipe component IDs, and file paths as needed.

### Phase 1: JSON Schemas

Create the data validation schemas for each template.

1. Create `templates/resultatrakning/schema.json`
   - Required fields: `title`, `period`, `grupper`
   - `grupper` follows the structure from #12's resultatrakning component
   - Optional: `header`, `rubrik_ar1`, `rubrik_ar2`, `noter`, `note`
   - Files: `templates/resultatrakning/schema.json` (create)

2. Create `templates/balansrakning/schema.json`
   - Required fields: `title`, `period`, `tillgangar` (assets), `skulder_eget_kapital` (liabilities + equity)
   - Each section uses the same group/post structure as resultatrakning
   - Optional: `header`, `rubrik_ar1`, `rubrik_ar2`, `noter`, `note`
   - Balance check: The template renders a final "Summa" row showing total assets vs total liabilities+equity. If they do not balance, the template still renders (no validation error) but displays the difference as a visual warning row. This is informational -- balance enforcement is the caller's responsibility.
   - Files: `templates/balansrakning/schema.json` (create)

3. Create `templates/budgetrapport/schema.json`
   - Required fields: `title`, `period`, `poster`
   - `poster` follows the structure from #12's budgettabell component
   - Optional: `header`, `rubrik_budget`, `rubrik_ar1`, `rubrik_ar2`, `kommentarer`, `note`
   - Files: `templates/budgetrapport/schema.json` (create)

4. Create `templates/sie-exportrapport/schema.json`
   - Required fields: `title`, `period`, `grupper`
   - Additional metadata: `sie_version`, `program`, `gen_date`, `org_number`, `org_name`
   - Optional: `header`, `rubrik_ar1`, `rubrik_ar2`, `noter`, `note`
   - Files: `templates/sie-exportrapport/schema.json` (create)

### Phase 2: YAML Recipes

Create the recipe definitions for each template. These follow the format established by #9.

1. Create `templates/resultatrakning/recipe.yaml`
   - Document: title section with period
   - Components: `resultatrakning` (the financial table)
   - Optional: `notapparat` (if noter data provided)
   - Files: `templates/resultatrakning/recipe.yaml` (create)

2. Create `templates/balansrakning/recipe.yaml`
   - Document: title section with period
   - Components: two `resultatrakning` instances (one for tillgangar, one for skulder/eget kapital)
   - A final balance sum row
   - Optional: `notapparat`
   - Files: `templates/balansrakning/recipe.yaml` (create)

3. Create `templates/budgetrapport/recipe.yaml`
   - Document: title section with period
   - Components: `budgettabell`
   - Optional: commentary section (free text)
   - Files: `templates/budgetrapport/recipe.yaml` (create)

4. Create `templates/sie-exportrapport/recipe.yaml`
   - Document: title section with period and export metadata block
   - Components: `resultatrakning` for the financial data
   - Metadata display: SIE version, program, generation date, org info
   - Files: `templates/sie-exportrapport/recipe.yaml` (create)

### Phase 3: Test Fixtures

Create sample data files for testing each template.

1. Create `tests/fixtures/resultatrakning.json`
   - Sample income statement with two groups (Intakter, Kostnader), comparison years, note references
   - Files: `tests/fixtures/resultatrakning.json` (create)

2. Create `tests/fixtures/balansrakning.json`
   - Sample balance sheet with tillgangar and skulder/eget kapital sections (balanced)
   - Files: `tests/fixtures/balansrakning.json` (create)

2b. Create `tests/fixtures/balansrakning_imbalanced.json`
   - Sample balance sheet where assets != liabilities+equity (for warning row test)
   - Files: `tests/fixtures/balansrakning_imbalanced.json` (create)

3. Create `tests/fixtures/budgetrapport.json`
   - Sample budget report with account codes, budget vs actuals
   - Files: `tests/fixtures/budgetrapport.json` (create)

4. Create `tests/fixtures/sie-exportrapport.json`
   - Sample SIE export with metadata and financial data
   - Files: `tests/fixtures/sie-exportrapport.json` (create)

### Phase 4: Test Updates

Update existing test files to include the new templates.

1. Update `tests/test_schemas.py`
   - Add all four template names to `test_discover_all_templates` assertions
   - Add all four to the `@pytest.mark.parametrize` list in `test_fixture_validates`
   - Files: `tests/test_schemas.py` (modify)

2. Update `tests/test_api.py`
   - Add all four template names to `test_list_templates` assertions
   - Files: `tests/test_api.py` (modify)

3. Add integration tests for recipe-based rendering
   - Test that each template renders a valid PDF from its fixture data (requires xelatex)
   - Test schema validation rejects invalid data (missing required fields)
   - Test balansrakning renders with balanced data (assets == liabilities+equity)
   - Test balansrakning renders with imbalanced data (warning row, no error)
   - Test resultatrakning with note references
   - Test branding integration (templates render with custom branding YAML)
   - Test header layout selection (standard/minimal/none) for at least one template
   - Files: `tests/test_renderer.py` (modify)

### Phase 5: Documentation

1. Update `README.md`
   - Add resultatrakning, balansrakning, budgetrapport, and SIE-exportrapport to the template table
   - Files: `README.md` (modify)

2. Update `README.en.md`
   - Add English descriptions for the four templates
   - Files: `README.en.md` (modify)

### Phase 6: Manual Verification

1. Render each template with CLI:
   ```bash
   klartex render -t resultatrakning -d tests/fixtures/resultatrakning.json -o test-resultatrakning.pdf
   klartex render -t balansrakning -d tests/fixtures/balansrakning.json -o test-balansrakning.pdf
   klartex render -t budgetrapport -d tests/fixtures/budgetrapport.json -o test-budgetrapport.pdf
   klartex render -t sie-exportrapport -d tests/fixtures/sie-exportrapport.json -o test-sie-exportrapport.pdf
   ```
2. Verify:
   - All templates appear in `klartex templates` listing
   - Schemas accessible via `klartex schema {name}`
   - PDFs render correctly with financial tables, proper formatting, note references
   - All tests pass with `pytest tests/`

## Files Summary

| File | Action | Purpose |
|------|--------|---------|
| `templates/resultatrakning/schema.json` | Create | JSON Schema for income statement data |
| `templates/resultatrakning/recipe.yaml` | Create | YAML recipe for income statement template |
| `templates/balansrakning/schema.json` | Create | JSON Schema for balance sheet data |
| `templates/balansrakning/recipe.yaml` | Create | YAML recipe for balance sheet template |
| `templates/budgetrapport/schema.json` | Create | JSON Schema for budget report data |
| `templates/budgetrapport/recipe.yaml` | Create | YAML recipe for budget report template |
| `templates/sie-exportrapport/schema.json` | Create | JSON Schema for SIE export report data |
| `templates/sie-exportrapport/recipe.yaml` | Create | YAML recipe for SIE export report template |
| `tests/fixtures/resultatrakning.json` | Create | Sample income statement test data |
| `tests/fixtures/balansrakning.json` | Create | Sample balance sheet test data (balanced) |
| `tests/fixtures/balansrakning_imbalanced.json` | Create | Sample imbalanced balance sheet for warning test |
| `tests/fixtures/budgetrapport.json` | Create | Sample budget report test data |
| `tests/fixtures/sie-exportrapport.json` | Create | Sample SIE export test data |
| `tests/test_schemas.py` | Modify | Add new templates to discovery/validation tests |
| `tests/test_api.py` | Modify | Add new templates to API listing test |
| `tests/test_renderer.py` | Modify | Add recipe-based rendering integration tests |
| `README.md` | Modify | Add new templates to Swedish template table |
| `README.en.md` | Modify | Add new templates to English template table |

## Codebase Areas

- `templates/resultatrakning/` (new template directory)
- `templates/balansrakning/` (new template directory)
- `templates/budgetrapport/` (new template directory)
- `templates/sie-exportrapport/` (new template directory)
- `tests/` (fixtures and test assertions)
- Root docs (`README.md`, `README.en.md`)

## Design Decisions

> Non-trivial choices made during planning. Feedback welcome; otherwise implementation proceeds with these.

### 1. Balansrakning Reuses resultatrakning Component

**Options:** (A) Create a dedicated `balansrakning.sty` component, (B) Reuse `resultatrakning.sty` twice (once for assets, once for liabilities/equity)
**Decision:** B -- Reuse resultatrakning.sty
**Rationale:** The issue explicitly states "resultatrakning (samma tabellformat)" for balansrakning. The table structure (groups, posts, subtotals, comparison years) is identical. Creating a separate component would duplicate code. The recipe can invoke the same component twice with different data sections, adding a final balance-check row.

### 2. All Templates Use Recipe Format (No .tex.jinja)

**Options:** (A) Create monolithic `.tex.jinja` files like existing templates, (B) Use YAML recipes exclusively
**Decision:** B -- YAML recipes only
**Rationale:** The issue states "Varje mall = YAML-recept + JSON Schema." These templates are designed specifically for the composable architecture (#9). Since they depend on #9 anyway, there is no backward-compatibility concern. Using recipes demonstrates the new architecture and keeps the templates declarative.

### 3. SIE Export Metadata as Structured Fields

**Options:** (A) Free-text metadata block, (B) Structured fields in schema (sie_version, program, gen_date, etc.)
**Decision:** B -- Structured fields
**Rationale:** SIE4 has well-defined metadata fields. Structuring them in the schema enables validation and consistent formatting. The recipe renders these in a metadata table at the top of the document, followed by the financial data in resultatrakning format.

### 4. Budget Commentary as Optional Free-Text

**Options:** (A) Structured commentary with per-line notes, (B) Single free-text commentary block, (C) No commentary
**Decision:** B -- Single optional free-text block
**Rationale:** The issue mentions "Kommentarer" for budgetrapport. A free-text block is simple and flexible. Per-line notes would require changes to the budgettabell component interface (which is defined in #12). A single commentary section below the table is the pragmatic choice.

### 5. Template Naming Convention

**Options:** (A) Swedish names matching the issue (resultatrakning, balansrakning), (B) English names (income-statement, balance-sheet), (C) Abbreviated (rr, br)
**Decision:** A -- Swedish names
**Rationale:** All existing templates use Swedish names (protokoll, faktura, avtal). The issue uses Swedish names. Consistency with the existing codebase is important. The component column in the issue table also uses Swedish names.

## Verification Checklist

- [ ] All four templates auto-discovered by registry
- [ ] Schemas validate correctly (required fields enforced, optional fields accepted)
- [ ] Resultatrakning PDF renders with grouped financial rows, comparison years, subtotals
- [ ] Balansrakning PDF renders with assets and liabilities/equity sections, balance check
- [ ] Balansrakning renders with imbalanced data (warning row, no crash)
- [ ] Budgetrapport PDF renders with budget vs actuals table and optional commentary
- [ ] SIE-exportrapport PDF renders with metadata header and financial data
- [ ] Note references work correctly (resultatrakning and balansrakning)
- [ ] All templates render with default branding
- [ ] All templates render with custom branding
- [ ] Header layout selection works for all templates
- [ ] Test fixtures validate against their schemas
- [ ] `pytest tests/` passes with all four templates added
- [ ] README template tables include all four new entries
- [ ] Swedish number formatting works (spaces as thousands separator)
