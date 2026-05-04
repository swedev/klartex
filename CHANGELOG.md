# Changelog

## 0.6.0 — 2026-05-04

### Breaking changes
- **`list` block: nested-items shorthand replaced with `content[]`.** A list item that previously expressed a sub-list as `{"text": "...", "items": [...]}` now uses `{"text": "...", "content": [{"type": "list", "items": [...]}]}`. The `content[]` array accepts nested blocks of types `text`, `list`, `callout`, `quote`, `table`, and `latex` — not just sub-lists. Top-only block types (`heading`, `signatures`, `title_page`, `parties`, `agenda`, `metadata_table`, `name_roster`, `clause`, `page_break`, financial blocks) are rejected at validation. This lets a numbered list item carry a continuation paragraph, suggested wording, embedded callout, etc., without introducing `(a)`-style sub-numbering.

### Typography
- **Widow and orphan protection.** `klartex-base.cls` now sets `\widowpenalties 2 10000 10000` and `\clubpenalties 2 10000 10000`, forbidding 1- and 2-line widows (last lines of a paragraph stranded on a new page) and orphans (first lines stranded at the bottom).
- **Heading-orphan protection.** Headings in the block engine call `\kxneedspace{6/4/3 \baselineskip}` (H1/H2/H3) so a heading cannot land alone at the bottom of a page — if the heading plus a few lines of body text doesn't fit, the page breaks before the heading. `\kxneedspace` is implemented inline in `klartex-base.cls` (no `needspace.sty` dependency).

### Internal
- Block-dispatch in `_block_engine.tex.jinja` is now a single `render_block` macro called both from the top-level body loop and recursively from `render_list` for items with `content[]`. The top-level loop continues to own the lazily-opened `clauses` environment around runs of `clause` blocks.

## 0.5.0 — 2026-05-03

### Breaking changes
- **Removed `preamble` block.** It was a pure alias for `text`; use `{"type": "text", ...}` instead. The recipe schema for `avtal` no longer accepts `"preamble"` either.
- **Removed `attendees` block.** The `protokoll` recipe still accepts `attendees` and `adjusters` in its input data and now surfaces them as `Närvarande:` / `Justerare:` rows in the metadata table — no input-data change is required for `protokoll`. Block-engine documents that previously used `{"type": "attendees", ...}` should switch to plain `text` blocks with bold inline labels.

### Spacing
- **Heading rhythm:** trailing `\vspace` now cancels the surrounding `\parskip` locally so H1/H2/H3 produce visibly distinct gaps below them (~1.2 / 0.5 / 0.15 em). Previously the parskip drowned the level differences.
- **`metadata_table`:** 2em above and below.
- **`parties`:** 3em above and below.
- **`table`:** symmetric 1em above and below (was 0/1).
- **`name_roster`, `resultatrakning`, `budgettabell`, `notapparat`:** explicit top/bottom margins so they no longer klistra mot brödtext.
- **`callout`:** `before/after skip` raised to 1em — consecutive callouts no longer touch.

### Quote block
- 2em vertical breathing room above and below.
- Wrapped in curly typographic quotes (`“…”`).
- The opening `“` is set at 36pt and hung into the left margin via a zero-width right-aligned box (classic hanging quote).

### Tests
- New comprehensive fixture `tests/fixtures/block_spacing_all.json` exercising every block type with realistic prose, useful for visual spacing inspection.

## 0.4.0 — 2026-05-02

### Breaking changes
- **Removed `adjuster_signatures` block.** The `protokoll` recipe still surfaces adjusters via the `attendees` label; for dedicated adjuster signature lines, use the `signatures` block.
- **Renamed `klartex-signaturblock` → `klartex-signatureblock`** (both the `.sty` package and the recipe component type). Update `\usepackage{klartex-signaturblock}` and any recipe `type: signaturblock` references.

### New features
- **`signatures` flexibility:** party `name` is now optional (omit to suppress the bold header above a signature pane); new block-level `show_location_date` flag (default `true`) hides the "Ort och datum" line and its dotted entry.

### Improvements
- **`table` block:** thin row lines (0.2pt `\cmidrule` between data rows) and a default `1em` bottom margin so following content breathes.
- **`signatures` block:** tighter pane spacing — reduced gaps above dotted lines (`0.8cm → 0.6cm`), shorter pane internals, and smaller inter-row/intro vspaces.
- **README:** previously-missing v0.3.0 blocks (`list`, `table`, `callout`, `quote`) now listed.

## 0.3.0 — 2026-04-30

### New blocks
- **`list`** — bullet/numbered, nestable (#24)
- **`table`** — simple data table with `tabularx` + `booktabs`, configurable column widths (#26)
- **`callout`** — visually distinct notice box with five variants (info/tip/warning/danger/note), backed by new `klartex-callout.sty` (#27)
- **`quote`** — typographic blockquote with optional em-dash attribution (#28)

### New features
- **Inline markup** in text-bearing fields: `**bold**`, `*italic*`, `` `code` ``, locale-aware smart quotes (sv: ”…”, en: “…”). Implemented as a Jinja `inline` filter; runs post-escape so existing escaping stays intact. (#25)
- **CLI:** `--version` / `-V` flag

### Fixes
- **External page templates** are now treated as self-contained — `--page-template` no longer loses the page-1 header from spurious `\thispagestyle{plain}` overrides applied on top of the user's template
- **Heading typography:** moved `\vspace` from after to before headings with asymmetric magnitudes; headings now visually belong to their following content. Removed redundant `\vspace{1em}` before text blocks (parskip handles it)
- **`metadata_table`** gets a default `\vspace{1em}` after, so it breathes before body content

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
