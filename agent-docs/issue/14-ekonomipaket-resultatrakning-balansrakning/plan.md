# Plan: Issue #14 — Financial package: resultaträkning, balansräkning, budgetrapport

## Goal

Create standalone financial document templates as YAML recipes. The issue states: "These documents have fixed layouts with calculations and structured tables — they are **specific templates**, not block-engine documents."

Four templates:
1. **Resultaträkning** — income statement with comparison years, note references
2. **Balansräkning** — balance sheet (assets / liabilities+equity), same table format
3. **Budgetrapport** — budget vs actuals with account codes
4. **SIE-exportrapport** — human-readable PDF of SIE4 accounting data

## Approach

Each template = `recipe.yaml` + `schema.json` in `klartex/templates/{name}/`, following the established pattern from `protokoll` and `faktura`. The recipes compose #12's financial components (resultatrakning, budgettabell, notapparat) via the recipe engine.

The recipe rendering template (`_recipe_base.tex.jinja`) needs new branches for the financial component types. These may already be added by #12 (if #12 adds them for both block engine and recipe paths), but if not, this issue adds them.

## Steps

### 1. Verify #12 components are available

Before implementation, confirm that `resultatrakning`, `budgettabell`, and `notapparat` are registered in `components.py` and their `.sty` files exist in `klartex/cls/`.

### 2. Add financial component rendering to `_recipe_base.tex.jinja`

If #12 only adds rendering to `_block_engine.tex.jinja`, add corresponding branches to `_recipe_base.tex.jinja` for:
- `resultatrakning` — iterate groups, emit `\rrgrupp`, `\rrpost`, `\rrsumma`, `\rrresultat`
- `budgettabell` — iterate posts, emit `\budgetpost`
- `notapparat` — iterate notes, emit `\notentry`

**File:** `klartex/templates/_recipe_base.tex.jinja`

### 3. Create `resultatrakning` template

**Files:**
- `klartex/templates/resultatrakning/schema.json` — requires `title`, `period`, `rubrik_ar1`, `rubrik_ar2`, `grupper`; optional `resultat`, `noter`
- `klartex/templates/resultatrakning/recipe.yaml` — heading + resultatrakning component + optional notapparat

### 4. Create `balansrakning` template

Reuses the `resultatrakning` component twice (once for assets, once for liabilities/equity). The table format is identical per the issue description.

**Files:**
- `klartex/templates/balansrakning/schema.json` — requires `title`, `period`, `rubrik_ar1`, `rubrik_ar2`, `tillgangar` (asset groups), `skulder_eget_kapital` (liability groups); optional `noter`
- `klartex/templates/balansrakning/recipe.yaml` — heading + two resultatrakning instances + optional notapparat

Design note: if assets ≠ liabilities+equity, the template still renders but displays the difference. No validation error — balance enforcement is the caller's responsibility.

### 5. Create `budgetrapport` template

**Files:**
- `klartex/templates/budgetrapport/schema.json` — requires `title`, `period`, `rubrik_budget`, `rubrik_ar1`, `rubrik_ar2`, `poster`; optional `kommentar`
- `klartex/templates/budgetrapport/recipe.yaml` — heading + budgettabell component + optional commentary text

### 6. Create `sie-exportrapport` template

**Files:**
- `klartex/templates/sie-exportrapport/schema.json` — requires `title`, `period`, `grupper`, plus SIE metadata (`sie_version`, `program`, `gen_date`, `org_number`, `org_name`)
- `klartex/templates/sie-exportrapport/recipe.yaml` — metadata table with SIE info + resultatrakning component

### 7. Test fixtures

All using a consistent fictional association ("Ekbackens Koloniförening").

**Files:**
- `tests/fixtures/resultatrakning.json` — income statement with two groups and notes
- `tests/fixtures/balansrakning.json` — balanced balance sheet
- `tests/fixtures/budgetrapport.json` — budget with account codes
- `tests/fixtures/sie-exportrapport.json` — SIE export with metadata

### 8. Tests

**Files:**
- `tests/test_schemas.py` — add 4 templates to discovery and validation parametrize lists
- `tests/test_renderer.py` — add render tests for all 4 fixtures (requires xelatex)

### 9. Documentation

**Files:**
- `README.md` — add 4 templates to the template table
- `README.en.md` — add English descriptions

## Files Summary

| File | Action |
|------|--------|
| `klartex/templates/_recipe_base.tex.jinja` | Modify — add financial component rendering (if not done by #12) |
| `klartex/templates/resultatrakning/schema.json` | Create |
| `klartex/templates/resultatrakning/recipe.yaml` | Create |
| `klartex/templates/balansrakning/schema.json` | Create |
| `klartex/templates/balansrakning/recipe.yaml` | Create |
| `klartex/templates/budgetrapport/schema.json` | Create |
| `klartex/templates/budgetrapport/recipe.yaml` | Create |
| `klartex/templates/sie-exportrapport/schema.json` | Create |
| `klartex/templates/sie-exportrapport/recipe.yaml` | Create |
| `tests/fixtures/resultatrakning.json` | Create |
| `tests/fixtures/balansrakning.json` | Create |
| `tests/fixtures/budgetrapport.json` | Create |
| `tests/fixtures/sie-exportrapport.json` | Create |
| `tests/test_schemas.py` | Modify |
| `tests/test_renderer.py` | Modify |
| `README.md` | Modify |
| `README.en.md` | Modify |

## Risks

- **#12 dependency** — Financial components must exist first. If #12's component interfaces differ from what's documented in the issue, recipe data_maps need adjusting.
- **Balansräkning with two resultatrakning instances** — The recipe engine supports multiple components of the same type (already works for protokoll's multiple components). But the data_map needs to point to different data paths (`tillgangar` vs `skulder_eget_kapital`).
- **SIE-exportrapport scope** — This template is less standard than the others. Could be deferred to a separate issue if it adds too much complexity.

## Test Plan

- All 4 templates discovered by `klartex templates`
- All 4 fixtures validate against their schemas
- All 4 render to valid PDFs
- Schema validation rejects missing required fields
- Swedish number formatting (from `klartex-numformat.sty`) works in all tables
- Existing tests still pass
