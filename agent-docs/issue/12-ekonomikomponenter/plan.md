# Implementation Plan: Ekonomikomponenter -- resultatrakning, budgettabell, notapparat

## Summary

Create three reusable LaTeX component packages for financial documents: `klartex-resultatrakning.sty` (income statement with comparison years, note references, subtotals), `klartex-budgettabell.sty` (budget table with account codes, actuals, and percentages), and `klartex-notapparat.sty` (numbered footnotes linked to financial tables). These components handle complex tabular layouts with structured YAML/JSON data and produce publication-quality financial tables.

## Triage Info

> Decision-support metadata for this issue.

| Field | Value |
|-------|-------|
| **Blocked by** | #9 Composable architecture -- YAML-recept-engine + .sty-komponenter (OPEN) |
| **Blocks** | #13 (arsmotespaket), #14 (ekonomipaket) |
| **Related issues** | #11 Foreningskomponenter (sibling -- also blocked by #9), #15 Self-describing metadata (meta.yaml format) |
| **Scope** | ~16 files across `cls/`, `templates/`, `klartex/`, `tests/` |
| **Risk** | Medium -- depends on #9 architecture decisions; financial tables have strict formatting requirements |
| **Complexity** | High -- three components with complex tabular layouts, grouped rows, subtotals, cross-referencing (notes) |
| **Safe for junior** | No (complex LaTeX table construction, cross-referencing between components) |
| **Conflict risk** | Medium -- shares `klartex/components.py` and `tests/test_components.py` with #9 and #11 |

### Triage Notes

This issue explicitly depends on #9 (composable architecture). The issue body states: "Beror pa #9 (composable architecture)." Issue #9 establishes the component pattern (`.sty` files in `cls/`, component registry in `klartex/components.py`, Jinja2 bridge macros, YAML recipe engine).

Issue #11 (foreningskomponenter) is a sibling issue also blocked by #9. Both issues create new `.sty` components following the same pattern. If #11 lands first, this issue can follow its established patterns. There is no direct dependency between #11 and #12 -- they touch different components but share the same infrastructure files (`components.py`).

Issue #15 (self-describing metadata) defines the `.meta.yaml` format. This plan uses a provisional `.meta.yaml` schema consistent with the patterns established in #11's plan. If #15 changes the format, the `.meta.yaml` files should be updated accordingly.

Issues #13 and #14 are downstream dependents that explicitly list #12 as a blocker. #14 (ekonomipaket) directly uses the components created here as building blocks for full financial document templates.

**Recommendation:** Wait for #9 to land first. The component registry, renderer symlink strategy, and recipe engine must be in place before these financial components can be registered and used. This plan aligns with #9's architecture decisions and should be updated if those decisions change.

## Analysis

### Current State

There are no existing financial table components in the codebase. The existing templates (faktura, protokoll, avtal) use inline Jinja2 loops with `tabularx` and `booktabs` for their tables (see `faktura.tex.jinja` lines 48-56). However, financial statements require substantially more complex table structures:

- **Grouped rows** with section headers (e.g., "Intakter", "Kostnader")
- **Subtotals** per group with visual separation
- **Note references** (superscript numbers linking to the notapparat)
- **Comparison columns** (current year vs previous year)
- **Account codes** (optional, used in budget tables)
- **Percentage columns** (optional, used in budget tables)

These cannot be achieved with simple Jinja2 loops -- they need dedicated LaTeX environments that handle the formatting logic.

### Key Design Considerations

1. **Number formatting**: Financial amounts need thousand-separator formatting and right-alignment. The chosen approach is to format numbers in LaTeX via a shared `\klartexnum` macro using `siunitx` (see Design Decision #2).

2. **Note cross-referencing**: The `resultatrakning` component emits plain `\textsuperscript{N}` for note references. The `notapparat` component independently displays numbered notes. There is no LaTeX `\label`/`\ref` coupling -- the semantic link is maintained by convention (matching note numbers in data). This means `resultatrakning` can be used without `notapparat` and vice versa.

3. **Table width**: Financial tables often need full-page width. `tabularx` (already loaded) handles this well with `X` columns for text and fixed-width columns for numbers.

4. **Group subtotals**: Each group in resultatrakning has a subtotal row with a horizontal rule above it. This needs careful `\cmidrule` or `\addlinespace` usage.

5. **Swedish number formatting**: Amounts should use space as thousand separator (e.g., "1 234 567") and comma as decimal separator per Swedish convention.

### Component Interaction

```
resultatrakning.sty  ----(convention)----> notapparat.sty
     (superscript N)                        (note N definitions)
     No package-level dependency. Linked by matching note numbers in data.

budgettabell.sty     (standalone, no cross-references)
```

The resultatrakning and notapparat are used together in arsredovisning (annual report) documents. The budgettabell is standalone, used in budget documents.

## Implementation Steps

### Phase 1: Create klartex-numformat.sty (Shared Number Formatting Utility)

This phase comes first because both `resultatrakning` and `budgettabell` depend on the number formatting utility.

1. Create the shared number formatting package
   - File: `cls/klartex-numformat.sty`
   - Provide `\klartexnum{amount}` macro that formats numbers with:
     - Space as thousand separator (Swedish convention)
     - Comma as decimal separator
     - Negative numbers displayed with minus sign
   - Implementation: Use `siunitx` with Swedish locale configuration:
     ```latex
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
   - Provide `\klartexnumdec{amount}` variant with 2 decimal places for when decimals are needed

### Phase 2: Create klartex-resultatrakning.sty

1. Create the component package file
   - File: `cls/klartex-resultatrakning.sty`
   - `\RequirePackage{klartex-numformat}` for number formatting
   - Provide `\usepackage{klartex-resultatrakning}` as the public API
   - Define a `resultatrakning` environment producing a full-width financial table
   - LaTeX interface:
     ```latex
     \usepackage{klartex-resultatrakning}
     ...
     \begin{resultatrakning}{2025}{2024}
       \rrgrupp{Intakter}
         \rrpost{Medlemsavgifter}{150000}{140000}
         \rrpost[1]{Bidrag och anslag}{50000}{45000}
       \rrsumma{Summa intakter}{200000}{185000}
       \rrgrupp{Kostnader}
         \rrpost[2]{Lokalhyra}{-60000}{-55000}
         \rrpost{Ovriga kostnader}{-30000}{-28000}
       \rrsumma{Summa kostnader}{-90000}{-83000}
       \rrresultat{Arets resultat}{110000}{102000}
     \end{resultatrakning}
     ```
   - Implementation details:
     - Use `tabularx` with columns: `X` (post name), `r` (year 1 amount), `r` (year 2 amount)
     - `\rrgrupp{name}` emits a bold group header row spanning all columns
     - `\rrpost[notref]{name}{amount1}{amount2}` emits a data row with optional superscript note reference (plain `\textsuperscript`, no `\label`/`\ref`)
     - `\rrsumma{label}{amount1}{amount2}` emits a subtotal row with `\midrule` above
     - `\rrresultat{label}{amount1}{amount2}` emits the final result row with `\toprule` above and bold formatting
     - All amounts rendered via `\klartexnum{amount}` from the shared utility
     - Column headers show the year labels passed as environment arguments

2. Create the metadata file
   - File: `cls/klartex-resultatrakning.meta.yaml`
   - Define inputs matching the issue specification:
     ```yaml
     name: resultatrakning
     description: "Finansiell tabell med notreferenser, grupperingar, subtotaler och jamforelseaar"
     inputs:
       - name: rubrik_ar1
         type: string
         required: true
         description: "Kolumnrubrik for ar 1 (t.ex. '2025')"
       - name: rubrik_ar2
         type: string
         required: true
         description: "Kolumnrubrik for ar 2 (t.ex. '2024')"
       - name: grupper
         type: array
         required: true
         items:
           rubrik: string
           poster:
             type: array
             items:
               notref: integer (optional)
               post: string
               belopp_ar1: number
               belopp_ar2: number
           summa:
             label: string
             belopp_ar1: number
             belopp_ar2: number
         description: "Grupper med poster och subtotaler"
       - name: resultat
         type: object
         required: false
         properties:
           label: string
           belopp_ar1: number
           belopp_ar2: number
         description: "Slutresultatrad (t.ex. 'Arets resultat'). Renderas med fetstil och toppstreck."
     used_in:
       - arsredovisning
     ```

### Phase 3: Create klartex-budgettabell.sty

1. Create the component package file
   - File: `cls/klartex-budgettabell.sty`
   - `\RequirePackage{klartex-numformat}` for number formatting
   - Provide `\usepackage{klartex-budgettabell}` as the public API
   - Define a `budgettabell` environment for budget vs actuals tables
   - LaTeX interface (using `xparse` for clean optional argument handling):
     ```latex
     \usepackage{klartex-budgettabell}
     ...
     \begin{budgettabell}{Budget 2026}{Utfall 2025}{Utfall 2024}
       \budgetpost{3010}{Medlemsavgifter}{160000}{150000}{140000}{107}
       \budgetpost{3020}{Bidrag}{55000}{50000}{45000}{}
       \budgetpost{}{Ovriga intakter}{10000}{8000}{7000}{}
     \end{budgettabell}
     ```
   - Implementation details:
     - Use `xparse` (`\RequirePackage{xparse}`) for clean macro definition
     - Use `tabularx` with columns: `l` (account code), `X` (description), `r` (budget), `r` (actual yr1), `r` (actual yr2), `r` (percentage)
     - `\budgetpost{konto}{post}{budget}{utfall1}{utfall2}{procent}` -- all 6 arguments are positional; empty string for unused fields
     - Account code column is always visible (empty cells when no code provided)
     - Percentage column is always visible; when `procent` is non-empty, displayed with `%` suffix
     - Amounts rendered via `\klartexnum{amount}` from the shared utility
     - Column headers from the three environment arguments

2. Create the metadata file
   - File: `cls/klartex-budgettabell.meta.yaml`
   - Define inputs matching the issue specification:
     ```yaml
     name: budgettabell
     description: "Budget med kontokod, post, budgeterat belopp, utfall och procent"
     inputs:
       - name: rubrik_budget
         type: string
         required: true
         description: "Kolumnrubrik for budget (t.ex. 'Budget 2026')"
       - name: rubrik_ar1
         type: string
         required: true
         description: "Kolumnrubrik for utfall ar 1"
       - name: rubrik_ar2
         type: string
         required: true
         description: "Kolumnrubrik for utfall ar 2"
       - name: poster
         type: array
         required: true
         items:
           konto: string (optional)
           post: string
           budget: number
           utfall_ar1: number
           utfall_ar2: number
           procent: number (optional)
         description: "Budgetposter med valfri kontokod och procentkolumn"
     used_in:
       - budget
     ```

### Phase 4: Create klartex-notapparat.sty

1. Create the component package file
   - File: `cls/klartex-notapparat.sty`
   - Provide `\usepackage{klartex-notapparat}` as the public API
   - Define a `notapparat` environment for numbered footnotes
   - LaTeX interface:
     ```latex
     \usepackage{klartex-notapparat}
     ...
     \begin{notapparat}
       \notentry{1}{Medlemsavgifter har hojts med 5\% fran foregaende ar.}
       \notentry{2}{Lokalhyran inkluderar el och vatten.}
     \end{notapparat}
     ```
   - Implementation details:
     - Uses a description-list or custom list with note numbers as labels
     - `\notentry{number}{text}` emits a labeled paragraph: bold superscript number followed by note text
     - Numbers match the `notref` values used in `resultatrakning` (linked by convention, not by `\label`/`\ref`)
     - A `\section*{Noter}` heading is automatically inserted at the start of the environment
     - Note: `\notentry` is used as the macro name (not `\not_entry`) since LaTeX macro names cannot contain underscores

2. Create the metadata file
   - File: `cls/klartex-notapparat.meta.yaml`
   - Define inputs matching the issue specification:
     ```yaml
     name: notapparat
     description: "Numrerade noter lankade till finansiella tabeller"
     inputs:
       - name: noter
         type: array
         required: true
         items:
           notnr: integer
           text: string
         description: "Numrerade noter med forklarande text"
     used_in:
       - arsredovisning
     ```

### Phase 5: Register Components in components.py

1. Update `klartex/components.py` (created by #9)
   - Add `resultatrakning` entry mapping to:
     - Package: `klartex-resultatrakning`
     - Environment: `resultatrakning`
     - Macros: `\rrgrupp`, `\rrpost`, `\rrsumma`, `\rrresultat`
     - Data keys: `rubrik_ar1`, `rubrik_ar2`, `grupper` array, `resultat` object (optional)
   - Add `budgettabell` entry mapping to:
     - Package: `klartex-budgettabell`
     - Environment: `budgettabell`
     - Macro: `\budgetpost`
     - Data keys: `rubrik_budget`, `rubrik_ar1`, `rubrik_ar2`, `poster` array
   - Add `notapparat` entry mapping to:
     - Package: `klartex-notapparat`
     - Environment: `notapparat`
     - Macro: `\notentry`
     - Data keys: `noter` array

### Phase 6: Create Jinja2 Component Macros

1. Create Jinja2 bridge macros that transform JSON data into LaTeX commands

2. `templates/_resultatrakning.jinja`:
   ```jinja
   \begin{resultatrakning}{\VAR{data.rubrik_ar1}}{\VAR{data.rubrik_ar2}}
   \BLOCK{for grupp in data.grupper}
     \rrgrupp{\VAR{grupp.rubrik}}
     \BLOCK{for post in grupp.poster}
       \rrpost\BLOCK{if post.notref is defined and post.notref is not none}[\VAR{post.notref}]\BLOCK{endif}{\VAR{post.post}}{\VAR{post.belopp_ar1}}{\VAR{post.belopp_ar2}}
     \BLOCK{endfor}
     \rrsumma{\VAR{grupp.summa.label}}{\VAR{grupp.summa.belopp_ar1}}{\VAR{grupp.summa.belopp_ar2}}
   \BLOCK{endfor}
   \BLOCK{if data.resultat is defined and data.resultat is not none}
     \rrresultat{\VAR{data.resultat.label}}{\VAR{data.resultat.belopp_ar1}}{\VAR{data.resultat.belopp_ar2}}
   \BLOCK{endif}
   \end{resultatrakning}
   ```

3. `templates/_budgettabell.jinja`:
   ```jinja
   \begin{budgettabell}{\VAR{data.rubrik_budget}}{\VAR{data.rubrik_ar1}}{\VAR{data.rubrik_ar2}}
   \BLOCK{for post in data.poster}
     \budgetpost{\VAR{post.get('konto', '')}}{\VAR{post.post}}{\VAR{post.budget}}{\VAR{post.utfall_ar1}}{\VAR{post.utfall_ar2}}{\VAR{post.get('procent', '') if post.procent is defined and post.procent is not none else ''}}
   \BLOCK{endfor}
   \end{budgettabell}
   ```

4. `templates/_notapparat.jinja`:
   ```jinja
   \begin{notapparat}
   \BLOCK{for item in data.noter}
     \notentry{\VAR{item.notnr}}{\VAR{item.text}}
   \BLOCK{endfor}
   \end{notapparat}
   ```

### Phase 7: Tests

1. Create test fixtures (namespaced to avoid collision with #14 template-level fixtures)
   - File: `tests/fixtures/component_resultatrakning.json` -- sample income statement with two groups, note references, and result row
   - File: `tests/fixtures/component_budgettabell.json` -- sample budget with account codes and percentages
   - File: `tests/fixtures/component_notapparat.json` -- sample notes matching the resultatrakning references

2. Add unit tests for all three components
   - File: `tests/test_components.py` (extend, created by #9)
   - Test resultatrakning: grouped rows, subtotals, note references, result row, number formatting
   - Test budgettabell: account codes, optional fields, percentage column, empty percentage handling
   - Test notapparat: numbered notes, special character handling
   - Test edge cases: empty groups, zero amounts, negative amounts, missing optional fields, `procent` as 0 vs absent

3. Integration test
   - Verify a sample arsredovisning-style document renders with resultatrakning + notapparat
   - Verify a budget document renders with budgettabell
   - File: `tests/test_renderer.py` (add test cases)

### Phase 8: Documentation

1. Update README with component descriptions
   - Add resultatrakning, budgettabell, notapparat to the component list
   - Show example YAML data for each

## Files Summary

| File | Action | Purpose |
|------|--------|---------|
| `cls/klartex-numformat.sty` | Create | Shared number formatting utility (Swedish convention via siunitx) |
| `cls/klartex-resultatrakning.sty` | Create | Income statement table with groups, subtotals, note refs |
| `cls/klartex-resultatrakning.meta.yaml` | Create | Self-describing metadata for resultatrakning |
| `cls/klartex-budgettabell.sty` | Create | Budget table with account codes, actuals, percentages |
| `cls/klartex-budgettabell.meta.yaml` | Create | Self-describing metadata for budgettabell |
| `cls/klartex-notapparat.sty` | Create | Numbered notes linked to financial tables |
| `cls/klartex-notapparat.meta.yaml` | Create | Self-describing metadata for notapparat |
| `klartex/components.py` | Modify | Register three financial components in mapping |
| `templates/_resultatrakning.jinja` | Create | Jinja2 macro bridging JSON to resultatrakning LaTeX |
| `templates/_budgettabell.jinja` | Create | Jinja2 macro bridging JSON to budgettabell LaTeX |
| `templates/_notapparat.jinja` | Create | Jinja2 macro bridging JSON to notapparat LaTeX |
| `tests/fixtures/component_resultatrakning.json` | Create | Test fixture for income statement component |
| `tests/fixtures/component_budgettabell.json` | Create | Test fixture for budget table component |
| `tests/fixtures/component_notapparat.json` | Create | Test fixture for notes component |
| `tests/test_components.py` | Modify | Unit tests for three financial components |
| `tests/test_renderer.py` | Modify | Integration tests for financial document rendering |

## Codebase Areas

- `cls/` (LaTeX style files -- new financial components and shared utility)
- `templates/` (Jinja2 bridge macros for data-to-LaTeX conversion)
- `klartex/` (component registry updates)
- `tests/` (test files and fixtures)

## Design Decisions

> Non-trivial choices made during planning. Feedback welcome; otherwise implementation proceeds with these.

### 1. Number Formatting: Shared Utility via siunitx
**Options:** (A) Each component handles its own number formatting, (B) Shared `klartex-numformat.sty` using `siunitx`, (C) Pre-format numbers in Jinja2
**Decision:** B -- Shared utility package using `siunitx`
**Rationale:** Both `resultatrakning` and `budgettabell` need identical number formatting (Swedish convention: space as thousand separator, comma as decimal separator). `siunitx` is a well-maintained, widely available LaTeX package that handles all number formatting edge cases (negative numbers, large numbers, decimal precision). A shared `klartex-numformat.sty` wraps `siunitx` with `\klartexnum` for clean API. This avoids duplicating formatting logic and allows the `.sty` components to work standalone without Jinja2. The `siunitx` dependency is acceptable since it is part of standard TeX Live distributions.

### 2. Note Reference Coupling: Loose (Convention-Based)
**Options:** (A) `resultatrakning` directly depends on `notapparat` package with `\label`/`\ref`, (B) Note references are plain superscripts with no package coupling
**Decision:** B -- Loose coupling via plain superscripts
**Rationale:** The `\rrpost[notref]` command simply emits `\textsuperscript{notref}`. The `notapparat` component independently displays numbered notes. There is no `\label`/`\ref` coupling. This keeps the components independent: `resultatrakning` can be used without `notapparat` (the superscripts still appear), and `notapparat` can be used with any table that uses matching numbers. The semantic link is maintained by matching note numbers in the data.

### 3. Account Code and Percentage Columns: Always Visible
**Options:** (A) Always show account code and percentage columns, (B) Conditionally hide columns when unused
**Decision:** A -- Always show both columns
**Rationale:** Hiding columns conditionally is complex in LaTeX (requires two-pass or environment argument). The simpler approach is to always reserve both columns -- empty cells when no data is provided. This keeps the LaTeX implementation straightforward. A "compact" variant can be added later as a separate environment option if needed.

### 4. budgetpost API: All Positional Arguments
**Options:** (A) Mix of optional `[]` and mandatory `{}` arguments, (B) All 6 arguments as mandatory `{}` positional (empty string for unused)
**Decision:** B -- All positional arguments
**Rationale:** Mixing optional `[arg1]` with mandatory `{arg2}` in LaTeX macros creates ambiguity and fragile parsing, especially when optional args appear in non-standard positions. Using 6 positional `{}` arguments with empty strings for unused fields is unambiguous, easy to generate from Jinja2, and avoids `xparse` complexity for this specific macro. The Jinja2 bridge handles the empty-string logic.

### 5. Jinja2 Template Variable Naming
**Options:** (A) Use `not` as loop variable in notapparat Jinja2 template, (B) Use `item` as loop variable
**Decision:** B -- Use `item` as loop variable
**Rationale:** `not` is a reserved keyword in Python/Jinja2. Using `item` avoids potential parser issues.

## Verification Checklist

- [ ] `klartex-numformat.sty` correctly formats numbers with Swedish convention
- [ ] `klartex-resultatrakning.sty` renders grouped financial table with correct column alignment
- [ ] Resultatrakning supports multiple groups with per-group subtotals
- [ ] Resultatrakning renders final `\rrresultat` row when `resultat` data is provided
- [ ] Note references appear as plain superscripts on the correct rows
- [ ] Comparison year columns display correctly
- [ ] `klartex-budgettabell.sty` renders budget table with account codes
- [ ] Percentage column displays correctly (with `%` suffix when non-empty)
- [ ] Budget table handles rows with empty account codes and empty percentages
- [ ] All `\budgetpost` arguments are positional -- no parsing ambiguity
- [ ] `klartex-notapparat.sty` renders numbered notes with correct formatting (using `\notentry` macro)
- [ ] Number formatting uses Swedish convention (space thousand separator) via `siunitx`
- [ ] Negative amounts display correctly (with minus sign)
- [ ] Zero amounts display as "0" consistently
- [ ] All three components have `.meta.yaml` with correct input schemas
- [ ] All three components are registered in `klartex/components.py`
- [ ] Jinja2 bridge macros correctly transform JSON data to LaTeX commands
- [ ] Jinja2 handles `procent` as 0 vs absent correctly (0 is displayed, absent is empty)
- [ ] Integration test: sample arsredovisning with resultatrakning + notapparat renders valid PDF
- [ ] Integration test: sample budget with budgettabell renders valid PDF
- [ ] Special characters (Swedish characters, &, %, etc.) handled via `tex_escape`
- [ ] Components are discoverable by the renderer (symlinked `cls/` directory)
- [ ] Existing templates (protokoll, faktura, avtal) unaffected
- [ ] Test fixture names namespaced (`component_*`) to avoid collision with #14 template-level fixtures
