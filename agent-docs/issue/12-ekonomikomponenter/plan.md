# Plan: Issue #12 — Financial components: resultaträkning, budgettabell, notapparat

## Goal

Add three financial block types to the block engine: `resultatrakning` (income statement), `budgettabell` (budget table), and `notapparat` (numbered notes). These are the building blocks for #13 (annual meeting package) and #14 (financial reports).

## Approach

Follow the established pattern from existing components (agenda, name_roster, etc.):

1. `.sty` file in `klartex/cls/` — LaTeX environments and macros
2. Block schema in `klartex/schemas/blocks/` — JSON Schema with `const` discriminator
3. `ComponentSpec` entry in `klartex/components.py`
4. Rendering logic inline in `klartex/templates/_block_engine.tex.jinja`
5. `.sty` loaded in `klartex/cls/klartex-base.cls` via `\RequirePackage`

A shared `klartex-numformat.sty` provides Swedish number formatting via `siunitx`.

## Steps

### 1. Create `klartex-numformat.sty` (shared utility)

**File:** `klartex/cls/klartex-numformat.sty`

Both `resultatrakning` and `budgettabell` need Swedish number formatting (space as thousand separator, comma as decimal separator). Use `siunitx`:

```latex
\NeedsTeXFormat{LaTeX2e}
\ProvidesPackage{klartex-numformat}[2026/03/29 Klartex Number Formatting]
\RequirePackage{siunitx}
\sisetup{
  group-separator = {\,},
  group-minimum-digits = 4,
  output-decimal-marker = {,},
  round-mode = places,
  round-precision = 0
}
\newcommand{\klartexnum}[1]{\num{#1}}
```

Load in `klartex-base.cls` before the financial components.

### 2. Create `klartex-resultatrakning.sty`

**File:** `klartex/cls/klartex-resultatrakning.sty`

Income statement table with grouped rows, subtotals, note references, and comparison years.

LaTeX macros:
- `\begin{resultatrakning}{year1}{year2}` — full-width tabularx
- `\rrgrupp{name}` — bold group header row
- `\rrpost[notref]{name}{amount1}{amount2}` — data row with optional superscript note
- `\rrsumma{label}{amount1}{amount2}` — subtotal with rule above
- `\rrresultat{label}{amount1}{amount2}` — final result row, bold with double rule

### 3. Create `resultatrakning` block schema

**File:** `klartex/schemas/blocks/resultatrakning.schema.json`

```json
{
  "type": { "const": "resultatrakning" },
  "rubrik_ar1": "string (required)",
  "rubrik_ar2": "string (required)",
  "grupper": [{
    "rubrik": "string",
    "poster": [{ "post": "string", "belopp_ar1": "number", "belopp_ar2": "number", "notref": "integer?" }],
    "summa": { "label": "string", "belopp_ar1": "number", "belopp_ar2": "number" }
  }],
  "resultat": { "label": "string", "belopp_ar1": "number", "belopp_ar2": "number" } (optional)
}
```

### 4. Create `klartex-budgettabell.sty`

**File:** `klartex/cls/klartex-budgettabell.sty`

Budget table with account code, description, budget, two outcome columns, and percentage.

LaTeX macros:
- `\begin{budgettabell}{budget_header}{year1_header}{year2_header}` — full-width tabularx
- `\budgetpost{konto}{post}{budget}{utfall1}{utfall2}{procent}` — all positional, empty string for unused

### 5. Create `budgettabell` block schema

**File:** `klartex/schemas/blocks/budgettabell.schema.json`

```json
{
  "type": { "const": "budgettabell" },
  "rubrik_budget": "string (required)",
  "rubrik_ar1": "string (required)",
  "rubrik_ar2": "string (required)",
  "poster": [{
    "post": "string",
    "budget": "number",
    "utfall_ar1": "number",
    "utfall_ar2": "number",
    "konto": "string?",
    "procent": "number?"
  }]
}
```

### 6. Create `klartex-notapparat.sty`

**File:** `klartex/cls/klartex-notapparat.sty`

Numbered notes linked to financial tables by convention (matching note numbers).

LaTeX macros:
- `\begin{notapparat}` — starts with a "Noter" heading
- `\notentry{number}{text}` — bold superscript number + note text

### 7. Create `notapparat` block schema

**File:** `klartex/schemas/blocks/notapparat.schema.json`

```json
{
  "type": { "const": "notapparat" },
  "noter": [{ "notnr": "integer", "text": "string" }]
}
```

### 8. Register components in `components.py`

**File:** `klartex/components.py`

Add three entries:
- `resultatrakning` → `sty_package="klartex-resultatrakning"`, `block_schema_path="resultatrakning.schema.json"`
- `budgettabell` → `sty_package="klartex-budgettabell"`, `block_schema_path="budgettabell.schema.json"`
- `notapparat` → `sty_package="klartex-notapparat"`, `block_schema_path="notapparat.schema.json"`

### 9. Add rendering to `_block_engine.tex.jinja`

**File:** `klartex/templates/_block_engine.tex.jinja`

Add `elif` branches for the three block types, following the pattern of existing blocks (close clause env if open, emit LaTeX). The Jinja loops iterate over groups/posts/notes and emit the macros defined in the `.sty` files.

### 10. Load packages in `klartex-base.cls`

**File:** `klartex/cls/klartex-base.cls`

Add:
```latex
\RequirePackage{klartex-numformat}
\RequirePackage{klartex-resultatrakning}
\RequirePackage{klartex-budgettabell}
\RequirePackage{klartex-notapparat}
```

### 11. Update block engine example

**File:** `klartex/schemas/block_engine.example.json`

Add one example of each new block type so `klartex example _block` covers them.

### 12. Tests

**Files:**
- `tests/fixtures/block_resultatrakning.json` — income statement with two groups + notes + result
- `tests/fixtures/block_budgettabell.json` — budget with account codes and percentages
- `tests/fixtures/block_notapparat.json` — notes matching the resultaträkning
- `tests/test_block_engine.py` — add render tests + validation error tests
- `tests/test_components.py` — verify component registration and schema loading

## Files Summary

| File | Action |
|------|--------|
| `klartex/cls/klartex-numformat.sty` | Create — shared number formatting |
| `klartex/cls/klartex-resultatrakning.sty` | Create — income statement LaTeX |
| `klartex/cls/klartex-budgettabell.sty` | Create — budget table LaTeX |
| `klartex/cls/klartex-notapparat.sty` | Create — numbered notes LaTeX |
| `klartex/cls/klartex-base.cls` | Modify — load new packages |
| `klartex/schemas/blocks/resultatrakning.schema.json` | Create |
| `klartex/schemas/blocks/budgettabell.schema.json` | Create |
| `klartex/schemas/blocks/notapparat.schema.json` | Create |
| `klartex/components.py` | Modify — register 3 components |
| `klartex/templates/_block_engine.tex.jinja` | Modify — add rendering |
| `klartex/schemas/block_engine.example.json` | Modify — add examples |
| `tests/fixtures/block_resultatrakning.json` | Create |
| `tests/fixtures/block_budgettabell.json` | Create |
| `tests/fixtures/block_notapparat.json` | Create |
| `tests/test_block_engine.py` | Modify — render + validation tests |
| `tests/test_components.py` | Modify — registration tests |

## Risks

- **`siunitx` availability** — Part of standard TeX Live. Should be available on all systems that can run klartex. The GitHub Actions CI uses `texlive-xetex` which includes it.
- **Number formatting edge cases** — Negative numbers, zero, very large numbers. The `siunitx` package handles these well, but should be tested.
- **Table width** — Financial tables with many columns can be tight on A4. The `tabularx` `X` column for the description field handles this.

## Test Plan

- All three block types render valid PDFs via `render("_block", data)`
- Schema validation rejects missing required fields
- Number formatting: positive, negative, zero, large numbers
- Note references appear as superscripts
- Empty optional fields (konto, procent, notref, resultat) handled gracefully
- Existing tests still pass (no regressions)
- `klartex blocks` lists the three new types
- `klartex schema _block` includes them in `oneOf`
