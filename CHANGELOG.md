# Changelog

## 0.2.1 — 2026-04-02

### Fixes
- **API:** Schema validation errors now return 400 instead of 500
- **Page template override:** `--page-template` / `page_template_source` no longer fails when `data.page_template` is missing or unknown
- **CLI:** `klartex example <template>` now works for all recipe templates (example.json files were missing)

## 0.2.0 — 2026-04-02

### New templates
- **resultaträkning** — Income statement with multi-year comparison and note references
- **balansräkning** — Balance sheet with assets/liabilities/equity structure
- **budgetrapport** — Budget vs. actuals report with variance percentages
- **sie-exportrapport** — SIE file export documentation with verification details

### New features
- **Annual meeting package** — 8 ready-made document fixtures (kallelse, verksamhetsberättelse, årsredovisning, revisionsberättelse, budget, valberedning, motion, styrelseyttrande)
- **Agent-friendly CLI** — `oneOf` JSON schema, `klartex blocks` listing, `--example` flag for quick starts
- **Financial components** — Reusable resultaträkning, budgettabell, and notapparat blocks for the block engine
- **Financial macros** — Shared Jinja macros (`_financial_macros.tex.jinja`) to DRY up financial rendering

### Improvements
- Swedish character fixes in protokoll template (Närvarande, Mötesprotokoll, Ordförande)
- Comprehensive test fixtures for all templates and block types (150 tests)

## 0.1.0 — 2026-02-17

Initial release.

- Core rendering engine (JSON + YAML recipe → LaTeX → PDF)
- Composable YAML recipe system with JSON Schema validation
- Templates: protokoll, faktura, avtal (via block engine)
- Universal block engine with clause, signature, attendees, party, and LaTeX blocks
- Configurable page templates and header layouts
- FastAPI HTTP service and Typer CLI
- GitHub Actions CI with xelatex verification
