# Implementation Plan: Universal Block Engine and Self-Describing Components

## Summary

Replace the current "template per document type" model with a **universal block engine** where the agent composes `body[]` freely from typed blocks. The document type emerges from what blocks the agent places in the body, not from which template it selects. This also introduces **page templates** (replacing the `header` enum) and a **self-describing block registry** accessible via API.

## Triage Info

> Decision-support metadata for this issue.

| Field | Value |
|-------|-------|
| **Blocked by** | None (#9 composable architecture is closed) |
| **Blocks** | #11 (dagordning/namnrollista become block types), #12 (financial tables become block types), #13 (association templates use block engine), #14 (financial reports may use specific templates or block engine) |
| **Related issues** | #7 (header layouts become page templates), #11, #12, #13, #14 |
| **Scope** | ~15 files across klartex/, templates/, cls/, schemas/, tests/ |
| **Risk** | Medium (fundamental rendering architecture change; must preserve backward compat for avtal/protokoll/faktura) |
| **Complexity** | High |
| **Safe for junior** | No |
| **Conflict risk** | Medium (plans for #11, #12, #13 all touch `klartex/components.py`, `templates/_recipe_base.tex.jinja`, and `cls/`) |

### Triage Notes

This issue is the architectural foundation that #11, #12, #13, and #14 build upon. It should be implemented before those issues. The avtal template already demonstrates the block-based `body[]` pattern in its `.tex.jinja` — this plan generalizes that pattern into the recipe/component engine so it works universally without per-template Jinja files.

Issue #7 (more header layouts) is subsumed: the `header` enum becomes `page_template` with richer definitions.

## Analysis

### Current State

The codebase has two rendering paths:
1. **Legacy** (`.tex.jinja`): Monolithic Jinja templates. The avtal template uses a `body[]` block loop with inline block-type dispatch (title_page, heading, parties, clause, etc.).
2. **Recipe** (`recipe.yaml`): Declarative YAML recipes that list fixed component sequences. The protokoll template uses this. Components are rendered by `_recipe_base.tex.jinja` with a big `if/elif` chain.

The avtal template already proves the block engine concept: its `body[]` array contains typed blocks that the agent composes freely. But the implementation lives in a template-specific `.tex.jinja` file, not in the shared recipe engine.

### Key Gaps

1. **Recipe components are fixed-sequence**: The current recipe format lists components in a static order. There is no way for the agent to compose `body[]` dynamically at render time.
2. **No page templates**: Headers are selected by a simple enum string (`standard`, `minimal`, `none`). There is no concept of a page template that bundles header, footer, margins, etc.
3. **No block registry API**: The agent has no way to discover available block types or their schemas.
4. **Block rendering is split**: Some block types (heading, metadata_table, attendees) are rendered inline in `_recipe_base.tex.jinja`. Others (klausuler, signaturblock, titelsida) delegate to `.sty` packages. The avtal template handles its own block dispatch entirely in Jinja.

### Design Approach

The block engine is a **new rendering mode** alongside legacy and recipe. When the agent sends `{ "page_template": "formal", "body": [...] }` (or `{ "page_template": { "name": "formal", "page_numbers": false }, "body": [...] }`), the engine:
1. Looks up the page template definition
2. Iterates over `body[]` blocks
3. For each block, dispatches to the correct component renderer (Jinja macro or LaTeX `.sty` command)

This can be implemented as an extension of the existing recipe engine — essentially a "dynamic recipe" where `components` comes from the user data instead of a static YAML file.

## Implementation Steps

### Phase 1: Page Template System

Replace the `header` enum with a page template system.

1. Create page template definition format
   - Files: `page_templates/formal.yaml`, `page_templates/clean.yaml`, `page_templates/branded.yaml`
   - Each defines: header/footer include file, margins (optional override), page numbering style, and defaults for overridable options
   - **Note:** The existing `_header_*.jinja` includes already define both header AND footer layout (e.g. `_header_standard.jinja` sets `\fancyhead` and `\fancyfoot`). Page templates wrap these existing includes rather than splitting header/footer into separate files.
   - Example:
     ```yaml
     name: formal
     description: "Logo top-left, org name in header, page numbers in footer"
     include: _header_standard.jinja   # existing include that sets both header + footer
     defaults:
       page_numbers: true
       first_page_header: true
     ```
   - `page_template` in the data model accepts either a string (shorthand) or an object with overrides:
     ```json
     "page_template": "formal"
     ```
     ```json
     "page_template": {
       "name": "formal",
       "page_numbers": false,
       "first_page_header": false
     }
     ```
   - Object form merges overrides on top of the template's defaults.

2. Create page template loader
   - File: `klartex/page_templates.py`
   - Function `load_page_template(name: str) -> PageTemplate`
   - Discovers `.yaml` files in `page_templates/` directory
   - Returns structured data for the meta-template to use

3. Update `_recipe_base.tex.jinja` to use page templates
   - Replace `%% include '_header_' ~ header ~ '.jinja'` with page-template-driven include
   - For backward compat, map legacy `header` values to page templates: `standard` -> `formal`, `minimal` -> `clean`, `none` -> `none`

4. Add `GET /page-templates` API endpoint
   - File: `klartex/main.py`
   - Returns list of available page templates with descriptions

### Phase 2: Block Type Registry with Self-Description

Extend the component registry to be self-describing with JSON Schema per block type.

1. Add JSON Schema to ComponentSpec
   - File: `klartex/components.py`
   - Add `block_schema: dict | None` field to `ComponentSpec`
   - Each component defines the JSON Schema for its block in `body[]`

2. Create block schema definitions
   - Either inline in the component registry or as separate `.schema.json` files per block type
   - Cover all existing block types: `title_page`, `heading`, `parties`, `preamble`/`text`, `clause`, `signatures`, `metadata`, `attendees`, `klausuler`, `signaturblock`, `titelsida`, `adjuster_signatures`
   - Add new block types: `metadata` (key-value table), `latex` (raw LaTeX passthrough)

3. Add `GET /blocks` and `GET /blocks/{name}/schema` API endpoints
   - File: `klartex/main.py`
   - `GET /blocks` returns list of block types with name and description
   - `GET /blocks/{name}/schema` returns the JSON Schema for a specific block type

### Phase 3: Universal Block Engine Rendering

Implement the core block engine that renders `body[]` dynamically.

1. Create the block engine renderer
   - File: `klartex/block_engine.py`
   - Function `render_block_document(data: dict, brand: Branding) -> str`
   - Accepts data with `page_template`, `lang`, and `body[]`
   - Iterates over `body[]`, dispatches each block to the appropriate renderer
   - Returns complete LaTeX source

2. Create the block engine Jinja meta-template
   - File: `templates/_block_engine.tex.jinja`
   - Similar to `_recipe_base.tex.jinja` but driven by `body[]` from data
   - Uses page template system for page chrome
   - Block dispatch via `if/elif` chain on `block.type`
   - Consolidates all block rendering from both avtal.tex.jinja and _recipe_base.tex.jinja

3. Create a universal JSON Schema for block engine documents
   - File: `schemas/block_engine.schema.json`
   - Top-level: `{ page_template, lang, body[] }`
   - `body[]` items use `oneOf` with discriminator on `type`
   - Reuse block schemas from the registry

4. Register the block engine in the renderer
   - File: `klartex/renderer.py`
   - When `template_name` is `"_block"` (or a special sentinel), use the block engine path
   - Alternatively, detect block-engine-style data (has `body[]` + `page_template`, no template-specific fields)

5. Add block engine to POST /render
   - Allow `template: "_block"` or introduce a separate endpoint `POST /render-blocks`
   - Validate against `block_engine.schema.json`

### Phase 4: Migrate Avtal to Block Engine

Convert the avtal template to use the block engine, proving that the block engine can replace template-specific Jinja files.

1. Ensure all avtal block types work in the block engine
   - `title_page`, `heading`, `parties`, `preamble`/`text`, `clause`, `signatures`
   - Party data moves into the `parties` and `signatures` blocks (no top-level `party1`/`party2`)
   - `title_page` receives its own data (party names, title) as block properties

2. Update avtal fixture to block engine format:
   ```json
   {
     "lang": "sv",
     "page_template": "formal",
     "body": [
       { "type": "title_page", "party1": "Uppdragsgivaren AB", "party2": "Erik Eriksson", "title": "Konsultavtal" },
       { "type": "heading", "text": "Konsultavtal" },
       { "type": "parties", "party1": { "name": "...", ... }, "party2": { "name": "...", ... } },
       { "type": "clause", "title": "Uppdrag", "items": ["..."] },
       { "type": "signatures", "parties": [{ "name": "...", "signatory": "..." }, ...], "new_page": false }
     ]
   }
   ```

3. Keep existing `avtal.tex.jinja` as legacy fallback during migration

4. Update tests to verify avtal renders correctly via block engine

### Phase 5: Tests and Documentation

1. Unit tests for page template loading
   - File: `tests/test_page_templates.py`

2. Unit tests for block registry API
   - File: `tests/test_components.py` (extend)

3. Integration tests for block engine rendering
   - File: `tests/test_block_engine.py`
   - Test: heading + text + signatures produces valid PDF
   - Test: full avtal-style document via block engine matches legacy output

4. API tests for new endpoints
   - File: `tests/test_api.py` (extend)
   - Test: `GET /blocks`, `GET /blocks/{name}/schema`, `GET /page-templates`

5. Update existing test fixtures if needed

## Files Summary

| File | Action | Purpose |
|------|--------|---------|
| `page_templates/formal.yaml` | Create | Formal page template (standard header, page numbers) |
| `page_templates/clean.yaml` | Create | Clean page template (no header, page numbers only) |
| `page_templates/branded.yaml` | Create | Branded page template (full org header, colored footer) |
| `klartex/page_templates.py` | Create | Page template loader and registry |
| `klartex/components.py` | Modify | Add `block_schema` to ComponentSpec, add new block types (metadata, latex) |
| `klartex/block_engine.py` | Create | Core block engine: data -> LaTeX via block dispatch |
| `klartex/renderer.py` | Modify | Add block engine rendering path alongside legacy/recipe |
| `klartex/main.py` | Modify | Add `/blocks`, `/blocks/{name}/schema`, `/page-templates` endpoints |
| `templates/_block_engine.tex.jinja` | Create | Meta-template for block engine rendering |
| `templates/_recipe_base.tex.jinja` | Modify | Update to use page template system (backward compat) |
| `schemas/block_engine.schema.json` | Create | JSON Schema for block engine documents |
| `schemas/recipe.schema.json` | Modify | Add optional page_template field |
| `schemas/blocks/heading.schema.json` | Create | Block schema for heading type |
| `schemas/blocks/clause.schema.json` | Create | Block schema for clause type |
| `schemas/blocks/` (etc.) | Create | Block schemas for all block types |
| `klartex/recipe.py` | Modify | Support page_template field in recipe context preparation |
| `klartex/registry.py` | Modify | Register `_block` as a virtual template for the block engine |
| `klartex/cli.py` | Modify | Ensure CLI works with `--template _block` |
| `tests/test_page_templates.py` | Create | Tests for page template loading |
| `tests/test_recipe.py` | Modify | Update tests for page_template backward compat in recipes |
| `tests/test_block_engine.py` | Create | Integration tests for block engine |
| `tests/test_components.py` | Modify | Tests for block registry and schemas |
| `tests/test_api.py` | Modify | Tests for new API endpoints |

## Codebase Areas

- `klartex/` (new modules: block_engine, page_templates; modified: components, renderer, main)
- `templates/` (new block engine meta-template; modified recipe base)
- `page_templates/` (new directory for page template definitions)
- `schemas/` (new block engine schema; modified recipe schema)
- `cls/` (no changes in this phase; new .sty files come from #11, #12)
- `tests/` (new and modified test files)

## Design Decisions

> Non-trivial choices made during planning. Feedback welcome; otherwise implementation proceeds with these.

### 1. Block Engine as a Separate Rendering Path (Not Replacing Recipe)
**Options:** (A) New rendering path alongside legacy/recipe, (B) Extend recipe format to support dynamic body, (C) Replace recipe entirely
**Decision:** A — New rendering path
**Rationale:** The recipe engine serves a different use case: templates with fixed component order defined by the template author. The block engine serves the use case where the agent composes freely. Keeping them separate avoids complicating the recipe format and lets template authors choose the right model. Recipe templates can still exist for domain-specific documents (faktura, resultatrakning) with rigid layouts.

### 2. Page Templates as YAML Files (Not Code)
**Options:** (A) YAML definitions in `page_templates/`, (B) Jinja includes with naming convention, (C) Python classes
**Decision:** A — YAML definitions
**Rationale:** Page templates are configuration, not logic. YAML keeps them accessible to non-developers and consistent with the recipe YAML pattern. The existing `_header_*.jinja` includes remain as the underlying implementation; page templates just provide a higher-level abstraction that bundles header + footer + options.

### 3. Block Engine Accessed via `template: "_block"` Sentinel
**Options:** (A) Special template name `_block`, (B) Separate endpoint `POST /render-blocks`, (C) Auto-detect from data shape
**Decision:** A — Special template name
**Rationale:** Using the existing `/render` endpoint with a sentinel template name keeps the API surface small and the client SDK simple. Auto-detection (C) is fragile. A separate endpoint (B) adds unnecessary API surface for the same operation.

### 4. Data Lives in Blocks, Not Top-Level
**Options:** (A) Top-level fields like `party1`/`party2` remain alongside `body[]`, (B) Everything goes inside blocks, (C) A `context` object for shared data
**Decision:** B — Everything goes inside blocks
**Rationale:** The block engine should be generic — not tied to two-party agreements. Party data belongs in the `parties` block. Signature data belongs in the `signatures` block. If multiple blocks need the same data (e.g. party names in both `parties` and `signatures`), the agent includes it in each block. This keeps blocks self-contained and the engine document-type-agnostic. The only top-level fields are `page_template`, `lang`, and `body[]`.

### 5. Block Schemas Defined Inline in Python (Not Separate Files)
**Options:** (A) Inline in `components.py` as dict literals, (B) Separate `.schema.json` per block type, (C) Auto-generated from dataclass
**Decision:** B — Separate `.schema.json` files in a `schemas/blocks/` directory
**Rationale:** Block schemas will be served via API and are useful for documentation. Separate files are easier to review and edit than inline dicts. They also allow validation tooling to consume them directly. The component registry references them by path.

## Verification Checklist

- [ ] Block engine renders a simple document (heading + text + signatures) to valid PDF
- [ ] Block engine renders full avtal-style document with all data in blocks (no top-level party1/party2)
- [ ] Page template system resolves `formal`, `clean`, `branded` correctly
- [ ] Page template as object with overrides works (`{ "name": "formal", "page_numbers": false }`)
- [ ] Legacy `header: standard/minimal/none` still works (backward compat)
- [ ] `GET /blocks` returns all registered block types
- [ ] `GET /blocks/{name}/schema` returns valid JSON Schema per block type
- [ ] `GET /page-templates` returns available page templates
- [ ] `POST /render` with `template: "_block"` and `body[]` produces correct PDF
- [ ] Existing avtal and protokoll and faktura templates still render correctly (no regression)
- [ ] Recipe-based templates (protokoll) unaffected by block engine changes
- [ ] Legacy `header` enum values in existing template schemas (avtal, protokoll, faktura) continue to work
- [ ] Block schemas validate correctly — invalid blocks are rejected with clear errors
