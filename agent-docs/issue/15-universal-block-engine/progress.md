# Implementation Progress: Issue #15

**Started:** 2026-02-22
**Last updated:** 2026-02-22
**Status:** Completed

## Completed Steps

- [x] Phase 1, Step 1: Create page template YAML definitions (formal, clean, branded, none)
- [x] Phase 1, Step 2: Create page template loader (klartex/page_templates.py)
- [x] Phase 1, Step 3: Update _recipe_base.tex.jinja for page template include (backward compat)
- [x] Phase 1, Step 4: Add GET /page-templates API endpoint
- [x] Phase 2, Step 1: Add block_schema_path to ComponentSpec
- [x] Phase 2, Step 2: Create block schema JSON files (schemas/blocks/*.schema.json)
- [x] Phase 2, Step 3: Register new block types (text, preamble, title_page, parties, clause, signatures, metadata_table, attendees, latex)
- [x] Phase 2, Step 4: Add GET /blocks and GET /blocks/{name}/schema API endpoints
- [x] Phase 3, Step 1: Create block engine module (klartex/block_engine.py)
- [x] Phase 3, Step 2: Create block engine Jinja meta-template (_block_engine.tex.jinja)
- [x] Phase 3, Step 3: Create universal JSON Schema (schemas/block_engine.schema.json)
- [x] Phase 3, Step 4: Register _block virtual template in registry
- [x] Phase 3, Step 5: Add block engine rendering path in renderer.py
- [x] Phase 3, Step 6: Update CLI for block engine template listing
- [x] Phase 4, Step 1: Create block-engine-format avtal fixture (avtal_block.json)
- [x] Phase 4, Step 2: Verify all avtal block types work in block engine
- [x] Phase 4, Step 3: Verify legacy avtal still works
- [x] Phase 5, Step 1: Unit tests for page template loading (test_page_templates.py)
- [x] Phase 5, Step 2: Unit tests for block registry (extended test_components.py)
- [x] Phase 5, Step 3: Integration tests for block engine (test_block_engine.py)
- [x] Phase 5, Step 4: API tests for new endpoints (extended test_api.py)
- [x] Phase 5, Step 5: Regression tests for existing templates

## Test Results

110 tests passed (up from 63 baseline), 0 failures.

## Post-Completion: Page Template Source Injection Refactor

**Date:** 2026-02-23

Simplified the page template system from path-based include to source injection:

- Removed `_is_external_path()`, `include_path` from `PageTemplate`
- Removed `_get_jinja_env()` and `_resolve_extra_dirs()` from renderer (external path machinery)
- Added `read_page_template_source()` — reads `.tex.jinja` file content by name
- Both rendering paths (block engine + recipe) read template file content and inject it as `page_template_source` in the Jinja context
- Meta-templates changed from `%% include page_template_include` to `\VAR{page_template_source}`
- Added `--page-template` CLI flag with stdin support (`-`)
- Added `page_template_source` field to API `RenderRequest`
- Added caller's `cwd` to `TEXINPUTS` so relative asset paths (logos etc.) work
- 111 tests pass

## Notes

- All block types render correctly through the block engine
- Legacy avtal, protokoll (both engines), and faktura continue to work
- Page templates are now injected as source content, not resolved via filesystem paths
- Block engine is accessed via template: "_block" sentinel
