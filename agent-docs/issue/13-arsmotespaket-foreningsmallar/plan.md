# Implementation Plan: Arsmotespaket -- 8 foreningsmallar som YAML-recept

## Summary

Create a complete annual meeting document package ("arsmotespaket") consisting of 8 YAML recipe templates for Swedish associations (colony associations, housing cooperatives, sports clubs, etc.). Each template is a YAML recipe file + JSON schema, using the composable architecture from #9 and reusable components from #10, #11, and #12. The package enables an AI agent to generate all 8 PDFs from a single data set with unified branding.

## Triage Info

> Decision-support metadata for this issue.

| Field | Value |
|-------|-------|
| **Blocked by** | #9 Composable architecture (OPEN), #10 Content layer (OPEN), #11 Foreningskomponenter (OPEN), #12 Ekonomikomponenter (OPEN) |
| **Blocks** | None |
| **Related issues** | #14 Ekonomipaket (shares economic components from #12), #15 Self-describing metadata |
| **Scope** | ~32 files across `templates/`, `tests/`, `schemas/`, docs |
| **Risk** | Medium -- depends on four unfinished prerequisites |
| **Complexity** | Medium (individual templates are straightforward once dependencies land) |
| **Safe for junior** | Yes (once #9, #10, #11, #12 are done and patterns are established) |
| **Conflict risk** | Medium -- #14 also creates recipe-based templates using the same components; shares `tests/test_schemas.py`, `tests/test_api.py`, `tests/test_renderer.py`, `README.md` |

### Triage Notes

This issue has **four explicit blockers**, all currently OPEN:

1. **#9 (Composable architecture)** -- Defines the YAML recipe engine and `.sty` component extraction pattern. Without this, templates cannot be defined as recipes.
2. **#10 (Content layer)** -- Provides the `| content` Jinja2 filter for rendering markdown-like text (verksamhetsberattelse, motions, revisionsberattelse all have "loptext" / running prose).
3. **#11 (Foreningskomponenter)** -- Creates `klartex-dagordning.sty` (agenda with paragraph-sign numbering) and `klartex-namnrollista.sty` (name/role table). Used by kallelse, verksamhetsberattelse, valberedningens forslag.
4. **#12 (Ekonomikomponenter)** -- Creates `klartex-resultatrakning.sty`, `klartex-budgettabell.sty`, and `klartex-notapparat.sty`. Used by ekonomisk arsredovisning and budget templates.

**Recommendation:** Wait for all four blockers to land before starting implementation. This plan aligns with the architecture decisions in the dependency plans and should be reviewed if those decisions change during implementation.

**Conflict with #14:** Issue #14 (Ekonomipaket) also creates recipe-based templates that use economic components. The two issues touch overlapping test/doc files but create different template directories. Coordination on test assertions and README updates is needed.

## Analysis

### The 8 Templates

The issue defines 8 templates for a complete annual meeting package:

| # | Template | Components Used | Content Fields |
|---|----------|----------------|----------------|
| 1 | **Kallelse + dagordning** | dagordning (#11) | Meeting metadata (date, time, location) |
| 2 | **Verksamhetsberattelse** | namnrollista (#11), signaturblock | Running prose with headings, activity lists (#10 content) |
| 3 | **Ekonomisk arsredovisning** | resultatrakning (#12), notapparat (#12) | Running prose (general about operations), resultatdisposition (#10 content) |
| 4 | **Revisionsberattelse** | signaturblock | Running prose (#10 content) |
| 5 | **Budget** | budgettabell (#12) | Budget commentary text (#10 content) |
| 6 | **Valberedningens forslag** | namnrollista (#11), signaturblock | -- |
| 7 | **Motion** | signaturblock | Running prose (background), numbered "att-satser" list (#10 content) |
| 8 | **Styrelsens svar pa motion** | signaturblock | Running prose (motivation), yrkande, argument list (#10 content) |

### Component Dependencies

From the dependency plans, the components available will be:

**From #9 (composable architecture):**
- Recipe engine (`klartex/recipe.py`) -- loads YAML recipes and generates LaTeX
- Component registry (`klartex/components.py`) -- maps component names to `.sty` packages
- Meta-template (`templates/_recipe_base.tex.jinja`) -- renders recipe-based documents
- Extracted `.sty` files: `klartex-signaturblock.sty`, `klartex-klausuler.sty`, `klartex-titelsida.sty`

**From #10 (content layer):**
- `| content` Jinja2 filter -- converts markdown subset to LaTeX
- `raw` data context in templates for rich text fields

**From #11 (foreningskomponenter):**
- `klartex-dagordning.sty` -- paragraph-numbered agenda lists
- `klartex-namnrollista.sty` -- formatted name/role/note tables
- Jinja2 macros: `_dagordning.jinja`, `_namnrollista.jinja`

**From #12 (ekonomikomponenter):**
- `klartex-resultatrakning.sty` -- financial table with comparison years and subtotals
- `klartex-budgettabell.sty` -- budget table with account codes and actuals
- `klartex-notapparat.sty` -- numbered notes section

### Template Structure Pattern

Each of the 8 templates follows the same pattern:
1. **YAML recipe** (`templates/{name}/recipe.yaml`) -- declares components and content fields
2. **JSON schema** (`templates/{name}/schema.json`) -- validates input data
3. **Test fixture** (`tests/fixtures/{name}.json`) -- sample data for testing

All templates use the recipe format (not monolithic `.tex.jinja`), as they are designed specifically for the composable architecture.

### Naming Convention

Template names follow Swedish convention consistent with existing templates (protokoll, faktura, avtal):
- `kallelse` (summons/invitation)
- `verksamhetsberattelse` (annual report)
- `arsredovisning` (annual financial report)
- `revisionsberattelse` (audit report)
- `budget` (budget)
- `valberedning` (nomination committee proposal)
- `motion` (motion/proposal)
- `styrelseyttrande` (board response to motion)

## Implementation Steps

### Phase 1: JSON Schemas (8 schemas)

Create data validation schemas for all 8 templates. All schemas should be consistent in style with existing schemas (see `templates/protokoll/schema.json` for reference).

1. Create `templates/kallelse/schema.json`
   - Required fields: `title`, `association_name`, `date`, `time`, `location`, `agenda_items`
   - `agenda_items`: array of `{ title: string }` (simple list, no discussion/decision)
   - Optional: `header`, `note` (extra info like "Valborjer med fika kl 17:30")
   - Files: `templates/kallelse/schema.json` (create)

2. Create `templates/verksamhetsberattelse/schema.json`
   - Required fields: `title`, `period`, `board_members` (array with name, role)
   - `sections`: array of `{ heading: string, body: string }` -- running prose (rendered via `| content`)
   - Optional: `header`, `activities` (array of strings), `signatories` (array with name, role)
   - Files: `templates/verksamhetsberattelse/schema.json` (create)

3. Create `templates/arsredovisning/schema.json`
   - Required fields: `title`, `period`, `grupper` (financial groups per #12 interface)
   - `general_text`: string -- running prose about operations (via `| content`)
   - `resultatdisposition`: string -- running prose about result disposition (via `| content`)
   - Optional: `header`, `rubrik_ar1`, `rubrik_ar2`, `noter`, `signatories`
   - Files: `templates/arsredovisning/schema.json` (create)

4. Create `templates/revisionsberattelse/schema.json`
   - Required fields: `title`, `association_name`, `period`, `body` (running prose via `| content`)
   - Optional: `header`, `signatories` (auditor names and roles)
   - Files: `templates/revisionsberattelse/schema.json` (create)

5. Create `templates/budget/schema.json`
   - Required fields: `title`, `period`, `poster` (budget items per #12 budgettabell interface)
   - Optional: `header`, `rubrik_budget`, `rubrik_ar1`, `rubrik_ar2`, `commentary` (via `| content`)
   - Files: `templates/budget/schema.json` (create)

6. Create `templates/valberedning/schema.json`
   - Required fields: `title`, `association_name`, `nominees` (array with name, role, note)
   - Optional: `header`, `signatories` (nominating committee members)
   - Files: `templates/valberedning/schema.json` (create)

7. Create `templates/motion/schema.json`
   - Required fields: `title`, `background` (running prose via `| content`), `proposals` (array of "att-satser")
   - Optional: `header`, `signatories` (motion authors)
   - Files: `templates/motion/schema.json` (create)

8. Create `templates/styrelseyttrande/schema.json`
   - Required fields: `title`, `motion_title`, `motivation` (running prose via `| content`), `recommendation` (yrkande string)
   - Optional: `header`, `arguments` (array of strings), `signatories`
   - Files: `templates/styrelseyttrande/schema.json` (create)

### Phase 2: YAML Recipes (8 recipes)

Create recipe definitions following the format established by #9.

1. Create `templates/kallelse/recipe.yaml`
   - Document: association name, meeting title, date/time/location
   - Components: `dagordning`
   - Content fields: optional note text
   - Files: `templates/kallelse/recipe.yaml` (create)

2. Create `templates/verksamhetsberattelse/recipe.yaml`
   - Document: title, period
   - Components: `namnrollista` (board members), `signaturblock`
   - Content fields: sections array (each with heading + body via content filter)
   - Files: `templates/verksamhetsberattelse/recipe.yaml` (create)

3. Create `templates/arsredovisning/recipe.yaml`
   - Document: title, period
   - Components: `resultatrakning`, `notapparat` (optional), `signaturblock`
   - Content fields: `general_text`, `resultatdisposition` (both via content filter)
   - Files: `templates/arsredovisning/recipe.yaml` (create)

4. Create `templates/revisionsberattelse/recipe.yaml`
   - Document: title, association name, period
   - Components: `signaturblock`
   - Content fields: `body` (running prose via content filter)
   - Files: `templates/revisionsberattelse/recipe.yaml` (create)

5. Create `templates/budget/recipe.yaml`
   - Document: title, period
   - Components: `budgettabell`
   - Content fields: optional `commentary` (via content filter)
   - Files: `templates/budget/recipe.yaml` (create)

6. Create `templates/valberedning/recipe.yaml`
   - Document: title, association name
   - Components: `namnrollista` (nominees), `signaturblock`
   - Content fields: none
   - Files: `templates/valberedning/recipe.yaml` (create)

7. Create `templates/motion/recipe.yaml`
   - Document: title
   - Components: `signaturblock`
   - Content fields: `background` (via content filter), `proposals` (numbered "att-satser" list)
   - Files: `templates/motion/recipe.yaml` (create)

8. Create `templates/styrelseyttrande/recipe.yaml`
   - Document: title, references motion_title
   - Components: `signaturblock`
   - Content fields: `motivation` (via content filter), `recommendation`, `arguments` list
   - Files: `templates/styrelseyttrande/recipe.yaml` (create)

### Phase 3: Test Fixtures (8 fixtures)

Create realistic sample data files based on a fictional colony association ("Ekbackens Koloniforening") for consistent cross-template testing.

1. Create `tests/fixtures/kallelse.json` -- Annual meeting summons with 10+ agenda items
2. Create `tests/fixtures/verksamhetsberattelse.json` -- Annual report with board list, activity sections
3. Create `tests/fixtures/arsredovisning.json` -- Financial report with income/expense groups, notes
4. Create `tests/fixtures/revisionsberattelse.json` -- Audit report with auditor signatures
5. Create `tests/fixtures/budget.json` -- Budget with budget vs actual columns
6. Create `tests/fixtures/valberedning.json` -- Nomination list with candidates and roles
7. Create `tests/fixtures/motion.json` -- Motion with background and 3 "att-satser"
8. Create `tests/fixtures/styrelseyttrande.json` -- Board response with motivation and recommendation

All fixtures should use the same association name, period, and consistent board member names to simulate a real annual meeting package.

### Phase 4: Test Updates

1. Update `tests/test_schemas.py`
   - Add all 8 template names to `test_discover_all_templates` assertions
   - Add all 8 to the `@pytest.mark.parametrize` list in `test_fixture_validates`
   - Files: `tests/test_schemas.py` (modify)

2. Update `tests/test_api.py`
   - Add all 8 template names to `test_list_templates` assertions
   - Files: `tests/test_api.py` (modify)

3. Add recipe-based rendering integration tests
   - Test that each of the 8 templates renders a valid PDF from its fixture data
   - Test schema validation rejects invalid data (missing required fields)
   - Files: `tests/test_renderer.py` (modify)

### Phase 5: Documentation

1. Update `README.md`
   - Add all 8 templates to the Swedish template table
   - Add a section describing the arsmotespaket concept and agent use case
   - Files: `README.md` (modify)

2. Update `README.en.md`
   - Add English descriptions for the 8 templates
   - Files: `README.en.md` (modify)

### Phase 6: Manual Verification

1. Render all 8 templates with CLI:
   ```bash
   klartex render -t kallelse -d tests/fixtures/kallelse.json -o test-kallelse.pdf
   klartex render -t verksamhetsberattelse -d tests/fixtures/verksamhetsberattelse.json -o test-verksamhetsberattelse.pdf
   klartex render -t arsredovisning -d tests/fixtures/arsredovisning.json -o test-arsredovisning.pdf
   klartex render -t revisionsberattelse -d tests/fixtures/revisionsberattelse.json -o test-revisionsberattelse.pdf
   klartex render -t budget -d tests/fixtures/budget.json -o test-budget.pdf
   klartex render -t valberedning -d tests/fixtures/valberedning.json -o test-valberedning.pdf
   klartex render -t motion -d tests/fixtures/motion.json -o test-motion.pdf
   klartex render -t styrelseyttrande -d tests/fixtures/styrelseyttrande.json -o test-styrelseyttrande.pdf
   ```

2. Verify:
   - All 8 templates appear in `klartex templates` listing
   - Schemas accessible via `klartex schema {name}`
   - PDFs render correctly with appropriate components and content
   - Unified branding applies consistently across all 8 documents
   - All tests pass with `pytest tests/`

## Files Summary

| File | Action | Purpose |
|------|--------|---------|
| `templates/kallelse/schema.json` | Create | JSON Schema for annual meeting summons |
| `templates/kallelse/recipe.yaml` | Create | YAML recipe for summons template |
| `templates/verksamhetsberattelse/schema.json` | Create | JSON Schema for annual report |
| `templates/verksamhetsberattelse/recipe.yaml` | Create | YAML recipe for annual report template |
| `templates/arsredovisning/schema.json` | Create | JSON Schema for financial annual report |
| `templates/arsredovisning/recipe.yaml` | Create | YAML recipe for financial report template |
| `templates/revisionsberattelse/schema.json` | Create | JSON Schema for audit report |
| `templates/revisionsberattelse/recipe.yaml` | Create | YAML recipe for audit report template |
| `templates/budget/schema.json` | Create | JSON Schema for budget |
| `templates/budget/recipe.yaml` | Create | YAML recipe for budget template |
| `templates/valberedning/schema.json` | Create | JSON Schema for nomination committee proposal |
| `templates/valberedning/recipe.yaml` | Create | YAML recipe for nomination proposal template |
| `templates/motion/schema.json` | Create | JSON Schema for motion/proposal |
| `templates/motion/recipe.yaml` | Create | YAML recipe for motion template |
| `templates/styrelseyttrande/schema.json` | Create | JSON Schema for board response to motion |
| `templates/styrelseyttrande/recipe.yaml` | Create | YAML recipe for board response template |
| `tests/fixtures/kallelse.json` | Create | Sample summons test data |
| `tests/fixtures/verksamhetsberattelse.json` | Create | Sample annual report test data |
| `tests/fixtures/arsredovisning.json` | Create | Sample financial report test data |
| `tests/fixtures/revisionsberattelse.json` | Create | Sample audit report test data |
| `tests/fixtures/budget.json` | Create | Sample budget test data |
| `tests/fixtures/valberedning.json` | Create | Sample nomination proposal test data |
| `tests/fixtures/motion.json` | Create | Sample motion test data |
| `tests/fixtures/styrelseyttrande.json` | Create | Sample board response test data |
| `tests/test_schemas.py` | Modify | Add 8 templates to discovery/validation tests |
| `tests/test_api.py` | Modify | Add 8 templates to API listing test |
| `tests/test_renderer.py` | Modify | Add recipe-based rendering integration tests |
| `README.md` | Modify | Add 8 templates to Swedish template table |
| `README.en.md` | Modify | Add 8 templates to English template table |

## Codebase Areas

- `templates/kallelse/` (new template directory)
- `templates/verksamhetsberattelse/` (new template directory)
- `templates/arsredovisning/` (new template directory)
- `templates/revisionsberattelse/` (new template directory)
- `templates/budget/` (new template directory)
- `templates/valberedning/` (new template directory)
- `templates/motion/` (new template directory)
- `templates/styrelseyttrande/` (new template directory)
- `tests/` (fixtures and test assertions)
- Root docs (`README.md`, `README.en.md`)

## Design Decisions

> Non-trivial choices made during planning. Feedback welcome; otherwise implementation proceeds with these.

### 1. All Templates Use Recipe Format (No .tex.jinja)

**Options:** (A) Create monolithic `.tex.jinja` files like existing templates, (B) Use YAML recipes exclusively
**Decision:** B -- YAML recipes only
**Rationale:** The issue explicitly states "Varje mall = en YAML-fil + JSON Schema." These templates are designed for the composable architecture from #9. Since they depend on #9 anyway, there is no backward-compatibility concern. Using recipes demonstrates the new architecture and keeps templates declarative.

### 2. Template Naming: Swedish, Simplified

**Options:** (A) Full compound names (e.g., `kallelse-dagordning`, `styrelsens-svar-pa-motion`), (B) Short Swedish names (e.g., `kallelse`, `styrelseyttrande`), (C) English names
**Decision:** B -- Short Swedish names
**Rationale:** Existing templates use short Swedish names (protokoll, faktura, avtal). Long compound names make CLI usage cumbersome. `kallelse` is clear enough without appending `-dagordning` since the dagordning is an integral part of a kallelse. `styrelseyttrande` is the standard Swedish term for a board response to a motion. The schema descriptions provide full context.

### 3. Shared Fixture Association for Cross-Template Testing

**Options:** (A) Independent fixture data per template, (B) Consistent fictional association across all fixtures
**Decision:** B -- All fixtures use "Ekbackens Koloniforening" with consistent names and period
**Rationale:** Using the same fictional association across all 8 fixtures simulates the real use case (generating a complete arsmotespaket). It enables end-to-end testing of the full package generation workflow and makes the sample data feel realistic and coherent.

### 4. Content Fields Use `| content` Filter from #10

**Options:** (A) Plain text only (no formatting in running prose), (B) Use #10's content filter for rich text, (C) Pre-format in LaTeX within JSON data
**Decision:** B -- Use `| content` filter
**Rationale:** The issue specifies "loptext" (running prose) with headings and lists for verksamhetsberattelse, motions, and revisionsberattelse. The content layer (#10) provides exactly this capability. Templates access `raw.field | content` for rich text fields, enabling AI agents to write natural markdown-like text without LaTeX knowledge.

### 5. Signaturblock Reuses Existing Component from klartex-base.cls (Later #9)

**Options:** (A) Create a new simplified signature component per template, (B) Reuse the `signaturblock` from klartex-base.cls (extracted to `klartex-signaturblock.sty` by #9)
**Decision:** B -- Reuse extracted signaturblock
**Rationale:** The existing `\signatureblock` command (and related `\dottedline`) in `klartex-base.cls` will be extracted to `klartex-signaturblock.sty` by #9. Several arsmotespaket templates need signature blocks (verksamhetsberattelse, revisionsberattelse, valberedning, motion, styrelseyttrande). Reusing the standard component ensures consistent signature formatting across all documents.

### 6. Arsredovisning vs Separate Resultatrakning Template

**Options:** (A) Combine arsredovisning as a comprehensive document (text + financial tables + notes), (B) Make arsredovisning just a wrapper pointing to a separate resultatrakning template from #14
**Decision:** A -- Arsredovisning as a comprehensive document
**Rationale:** In the arsmotespaket context, the "Ekonomisk arsredovisning" is a full document with introductory text about operations, the income statement (resultatrakning component), result disposition text, and optionally notes. This is different from #14's standalone resultatrakning template which is just the financial table. The arsredovisning recipe composes the resultatrakning component with surrounding content, which is the power of the recipe system.

## Verification Checklist

- [ ] All 8 templates auto-discovered by registry via recipe.yaml + schema.json
- [ ] All 8 schemas validate correctly (required fields enforced, optional fields accepted)
- [ ] Kallelse PDF renders with meeting metadata and paragraph-numbered dagordning
- [ ] Verksamhetsberattelse PDF renders with board namnrollista, prose sections, and signatures
- [ ] Arsredovisning PDF renders with general text, resultatrakning table, notes, and signatures
- [ ] Revisionsberattelse PDF renders with prose body and auditor signatures
- [ ] Budget PDF renders with budgettabell and optional commentary
- [ ] Valberedning PDF renders with nominee namnrollista and signatures
- [ ] Motion PDF renders with background prose, numbered att-satser, and signatures
- [ ] Styrelseyttrande PDF renders with motivation, recommendation, and signatures
- [ ] Content fields render markdown-like text correctly (headings, bold, lists)
- [ ] All 8 templates render with default and custom branding
- [ ] Header layout selection works for all templates
- [ ] Test fixtures validate against their schemas
- [ ] Consistent association data across fixtures (Ekbackens Koloniforening)
- [ ] `pytest tests/` passes with all 8 templates added
- [ ] README template tables include all 8 new entries (both Swedish and English)
- [ ] Swedish characters render correctly in all templates
