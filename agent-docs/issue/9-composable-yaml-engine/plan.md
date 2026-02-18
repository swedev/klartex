# Implementation Plan: Composable Architecture — YAML-recept-engine + .sty-komponenter

## Summary

Transform Klartex from monolithic `.tex.jinja` templates to a composable architecture where templates can be defined as YAML "recipes" that combine reusable LaTeX components (`.sty` files). The existing monolithic templates must continue working (backward compatibility).

## Triage Info

> Decision-support metadata for this issue.

| Field | Value |
|-------|-------|
| **Blocked by** | None |
| **Blocks** | #10 (content layer), #11 (foreningskomponenter), #12 (ekonomikomponenter), #13 (årsmötespaket), #14 (ekonomipaket) |
| **Related issues** | #7 (header layouts), #8 (kvitto template) |
| **Scope** | ~15 files across cls/, templates/, klartex/, schemas/, tests/ |
| **Risk** | Medium |
| **Complexity** | High |
| **Safe for junior** | No |
| **Conflict risk** | Medium (issue #7 touches schemas, #8 adds new template) |

### Triage Notes
- This is a foundational architecture change. Explicitly blocks #10, #11, #12, #13, #14 — all issues that depend on the recipe engine or component pattern.
- Issues #7 (header layouts) and #8 (kvitto) do NOT depend on this — they work with monolithic templates and are independently ready.
- Issue #10 (content layer) is a sibling concern but not a blocker — the two can be built independently once #9 lands.
- No explicit blockers found. This issue is ready to work.

## Analysis

### Current Architecture

The system currently works as follows:
1. **Registry** (`klartex/registry.py`) scans `templates/` for subdirectories containing `schema.json` + `{name}.tex.jinja`
2. **Renderer** (`klartex/renderer.py`) validates data against the schema, renders the Jinja template, compiles with xelatex
3. **Document class** (`cls/klartex-base.cls`) provides base formatting, clause environments, signature blocks
4. **Branding** is loaded from YAML and injected via `_branding_preamble.jinja`
5. **Headers** are selected via Jinja includes (`_header_standard.jinja`, etc.)

Each template (protokoll, faktura, avtal) is a standalone `.tex.jinja` file that hardcodes its entire layout. Shared LaTeX features (clauses, signatures) live in the `.cls` file, not as separate packages.

### Target Architecture (Three Layers)

1. **Document level** — `klartex-base.cls` handles page setup, branding, headers/footers (already exists)
2. **Component level** — Reusable `.sty` packages providing structured LaTeX macros (e.g., `signaturblock.sty`, `klausuler.sty`)
3. **Recipe level** — YAML files that declare which components and content fields to combine, replacing the need for hand-written `.tex.jinja` files

### Key Design Constraints

- **Backward compatibility**: Existing `.tex.jinja` templates MUST continue to work unchanged
- **Incremental adoption**: New templates can use YAML recipes, old ones keep their `.tex.jinja`
- **Schema validation**: Both recipe-based and monolithic templates must have JSON schemas
- **Component data flow**: Components receive structured data and produce LaTeX output

## Implementation Steps

### Phase 1: Extract .sty Components from klartex-base.cls

Extract reusable LaTeX building blocks into standalone `.sty` files that can be loaded independently.

1. Create `cls/klartex-signaturblock.sty`
   - Move `\signatureblock`, `\dottedline`, and related language strings from `klartex-base.cls`
   - The `.sty` file should `\RequirePackage` only what it needs
   - Provide `\usepackage{klartex-signaturblock}` as the public API
   - Files: `cls/klartex-signaturblock.sty` (create)

2. Create `cls/klartex-klausuler.sty`
   - Move clause/subclause counters, list definitions, and `\clause` command from `klartex-base.cls`
   - Files: `cls/klartex-klausuler.sty` (create)

3. Create `cls/klartex-titelsida.sty`
   - Move `\makedoctitle` from `klartex-base.cls`
   - Files: `cls/klartex-titelsida.sty` (create)

4. Update `klartex-base.cls` to load the new `.sty` files via `\RequirePackage`
   - This preserves backward compatibility — existing templates see the same commands
   - Files: `cls/klartex-base.cls` (modify)

5. Verify all existing templates still compile correctly
   - Run existing tests to confirm no regression

### Phase 2: Define YAML Recipe Schema

Design the YAML recipe format and its validation schema.

1. Create `schemas/recipe.schema.json` — JSON Schema for the recipe YAML format
   - Define top-level fields: `template`, `document`, `components`, `content_fields`, `schema`
   - `document` section: `sidhuvud`, `sidfot`, `metadata` list
   - `components` section: ordered list of component names
   - `content_fields`: mapping of field name to type (text, list, etc.)
   - `schema`: path to JSON Schema for the template data
   - Files: `schemas/recipe.schema.json` (create)

2. Create a sample recipe for `protokoll` as proof-of-concept
   - This is a YAML equivalent of the existing `protokoll.tex.jinja`
   - Files: `templates/protokoll/recipe.yaml` (create)
   - Note: the existing `protokoll.tex.jinja` stays — the recipe is an alternative path

### Phase 3: Build the Recipe Engine

Implement the Python code that reads a YAML recipe and generates LaTeX.

1. Create `klartex/recipe.py` — Recipe loader and orchestration
   - `load_recipe(path: Path) -> Recipe` — parse YAML, validate against recipe schema
   - `Recipe` dataclass with fields matching the YAML structure
   - `prepare_recipe_context(recipe: Recipe, data: dict, brand: Branding) -> dict` — build a template context dict for the Jinja meta-template (component list, data mappings, branding)
   - Note: This module does NOT generate LaTeX strings. LaTeX generation is handled entirely by the Jinja meta-template (`_recipe_base.tex.jinja`). This module only loads/validates recipes and prepares data for Jinja.
   - Files: `klartex/recipe.py` (create)

2. Define component-to-LaTeX mapping
   - Each component name (e.g., `signaturblock`) maps to:
     - A `.sty` package to load
     - A LaTeX macro/environment to invoke
     - A data extraction function (which keys from `data` to pass)
   - This mapping lives in `klartex/components.py`
   - Files: `klartex/components.py` (create)

3. Create a Jinja2 "meta-template" for recipe-based rendering
   - A single `.tex.jinja` that takes a recipe definition and renders the full document
   - This is the ONLY LaTeX generation path for recipes — no Python string building
   - The meta-template receives the recipe structure and data context from `prepare_recipe_context()`, iterating over components to produce the final `.tex`
   - Files: `templates/_recipe_base.tex.jinja` (create)

### Phase 4: Integrate Recipe Engine into Renderer

Update the existing rendering pipeline to support both monolithic and recipe-based templates.

1. Update `klartex/registry.py`
   - Extend `discover_templates()` to also detect `recipe.yaml` in template directories
   - Add a `recipe` field to `TemplateInfo` (optional, `None` for monolithic templates)
   - A template with both `recipe.yaml` and `.tex.jinja` defaults to `.tex.jinja` for backward compat
   - Files: `klartex/registry.py` (modify)

2. Update `klartex/renderer.py`
   - Add an `engine` parameter to `render()`: `engine: str = "auto"` (values: `auto`, `legacy`, `recipe`)
   - Engine selection contract:
     - `auto` (default): Use `.tex.jinja` if it exists (backward compat), otherwise use `recipe.yaml` if it exists, otherwise error
     - `legacy`: Force `.tex.jinja` path. Error if `.tex.jinja` does not exist.
     - `recipe`: Force recipe path. Error if `recipe.yaml` does not exist.
   - For recipe path: call `prepare_recipe_context()` then render `_recipe_base.tex.jinja`
   - Escaping contract: Data is escaped via `escape_data()` before being passed to recipe context, same as the monolithic path. The meta-template must NOT double-escape.
   - Ensure `.sty` files are available in temp dir alongside `.cls` (see step 3)
   - Files: `klartex/renderer.py` (modify)

3. Update temp directory setup
   - Current code symlinks only `klartex-base.cls` as a single file (`renderer.py:108`). With multiple `.sty` files this must change.
   - New strategy: symlink the entire `cls/` directory into the temp dir (instead of individual files). This is simpler and future-proof as new `.sty` files are added.
   - Files: `klartex/renderer.py` (modify, same change as above)

4. Expose `engine` parameter in CLI and API
   - Add `--engine` option to `klartex render` CLI command (default: `auto`)
   - Add `engine` field to `RenderRequest` Pydantic model (default: `"auto"`)
   - Pass through to `render()` call
   - Files: `klartex/cli.py` (modify), `klartex/main.py` (modify)

### Phase 5: Tests

1. Add unit tests for recipe loading and validation
   - Test valid recipe parsing
   - Test invalid recipe rejection
   - Files: `tests/test_recipe.py` (create)

2. Add unit tests for component registry
   - Test component-to-LaTeX mapping
   - Files: `tests/test_components.py` (create)

3. Add integration test: recipe-based protokoll renders same as monolithic
   - Render with both paths, compare PDF output (at minimum, both should produce valid PDFs)
   - Files: `tests/test_renderer.py` (modify)

4. Add discovery and precedence tests
   - Test that a recipe-only template (no `.tex.jinja`) is discovered by registry
   - Test that a template with both `.tex.jinja` and `recipe.yaml` defaults to `.tex.jinja` in `auto` mode
   - Test explicit `engine="recipe"` selects recipe path even when `.tex.jinja` exists
   - Test explicit `engine="legacy"` errors when no `.tex.jinja` exists
   - Test explicit `engine="recipe"` errors when no `recipe.yaml` exists
   - Files: `tests/test_renderer.py` (modify), `tests/test_recipe.py` (create)

5. Add escaping/safety tests for recipe rendering
   - Test that LaTeX special characters in data (e.g., `$`, `%`, `&`, `_`, `#`, `{`, `}`) are properly escaped in recipe output
   - Test that injection-like input (e.g., `\input{/etc/passwd}`) is escaped and rendered as literal text
   - Files: `tests/test_recipe.py` (create)

6. Add API/CLI engine selection tests
   - Test `/render` with `engine` field set to each valid value
   - Test CLI `--engine` option
   - Files: `tests/test_api.py` (modify)

7. Ensure existing tests pass unchanged
   - Run full test suite

### Phase 6: Documentation and Migration Guide

1. Update README with composable architecture overview
   - Explain the three-layer model
   - Show how to create a new template via YAML recipe
   - Document the `engine` parameter (CLI and API)
   - Files: `README.md` (modify), `README.en.md` (modify)

2. Add a recipe authoring guide
   - YAML recipe format reference
   - Available components and their data requirements
   - Files: can be added as a section in README or as comments in the recipe schema

## Files Summary

| File | Action | Purpose |
|------|--------|---------|
| `cls/klartex-signaturblock.sty` | Create | Extracted signature block LaTeX component |
| `cls/klartex-klausuler.sty` | Create | Extracted clause/subclause LaTeX component |
| `cls/klartex-titelsida.sty` | Create | Extracted title page LaTeX component |
| `cls/klartex-base.cls` | Modify | Load extracted .sty files via RequirePackage |
| `schemas/recipe.schema.json` | Create | JSON Schema for validating recipe YAML format |
| `templates/protokoll/recipe.yaml` | Create | Sample recipe (proof of concept) |
| `templates/_recipe_base.tex.jinja` | Create | Meta-template for recipe-based rendering |
| `klartex/recipe.py` | Create | Recipe loader and context preparation |
| `klartex/components.py` | Create | Component name to LaTeX mapping |
| `klartex/registry.py` | Modify | Support recipe.yaml discovery |
| `klartex/renderer.py` | Modify | Dual-path rendering with engine selection |
| `klartex/cli.py` | Modify | Add --engine option |
| `klartex/main.py` | Modify | Add engine field to RenderRequest |
| `tests/test_recipe.py` | Create | Recipe loading, validation, and escaping tests |
| `tests/test_components.py` | Create | Component mapping tests |
| `tests/test_renderer.py` | Modify | Add recipe integration and precedence tests |
| `tests/test_api.py` | Modify | Add engine selection API tests |
| `README.md` | Modify | Composable architecture overview |
| `README.en.md` | Modify | English version of architecture docs |

## Codebase Areas

- `cls/` (LaTeX class and style files)
- `klartex/` (Python engine — renderer, registry, recipe, components, CLI, API)
- `templates/` (Jinja templates, recipe YAML, template data schemas — `schema.json` per template)
- `schemas/` (new — recipe format schema only, NOT template data schemas)
- `tests/` (unit and integration tests)
- Root docs (`README.md`, `README.en.md`)

### Schema Convention

Two distinct types of schemas serve different purposes:
- **Template data schemas** (`templates/<name>/schema.json`) — validate user-provided JSON data. One source of truth per template. Used by registry, CLI, and API.
- **Recipe format schema** (`schemas/recipe.schema.json`) — validates the structure of `recipe.yaml` files. This is a meta-schema for the recipe format itself, NOT for user data.

## Design Decisions

> Non-trivial choices made during planning. Feedback welcome; otherwise implementation proceeds with these.

### 1. .sty Files Live in `cls/` Directory
**Options:** Separate `sty/` directory vs keep in `cls/`
**Decision:** Keep in `cls/` directory
**Rationale:** The `cls/` directory already holds the document class. Currently `renderer.py` symlinks only `klartex-base.cls` as a single file (`renderer.py:108` — `(tmp / "klartex-base.cls").symlink_to(CLS_DIR / "klartex-base.cls")`). With multiple `.sty` files, this individual-file symlink approach won't scale. Phase 4 step 3 changes this to symlink the entire `cls/` directory instead, making all `.cls` and `.sty` files available to xelatex automatically.

### 2. Jinja Meta-Template Instead of Python String Building
**Options:** Generate LaTeX strings in Python (`recipe_to_tex()`) vs use a Jinja meta-template
**Decision:** Use a Jinja meta-template (`_recipe_base.tex.jinja`) exclusively
**Rationale:** Keeping LaTeX generation in Jinja is consistent with the existing approach, easier to read and maintain, and avoids mixing LaTeX syntax with Python string manipulation. The Python side (`recipe.py`) only loads/validates recipes and prepares data context — it never produces LaTeX strings. This is a single, unambiguous rendering path.

### 3. Backward-Compatible Dual-Path Rendering
**Options:** Migrate all templates to recipes vs keep both paths
**Decision:** Keep both paths — `.tex.jinja` takes precedence when both exist
**Rationale:** The issue explicitly requires backward compatibility. Existing monolithic templates should not break. A template directory can contain both a `.tex.jinja` (legacy) and a `recipe.yaml` (new), with the monolithic template winning by default. A flag or config option could later switch preference.

### 4. Component Mapping in Separate Module
**Options:** Inline component logic in recipe.py vs separate `components.py`
**Decision:** Separate `components.py` module
**Rationale:** Each component needs a mapping from name to: (a) .sty package, (b) LaTeX macro, (c) data extraction. This is a natural registry pattern. Keeping it separate makes it easy to add new components without touching the recipe engine, and enables future auto-discovery of components.

### 5. Escaping Contract for Recipe Rendering
**Options:** (A) Escape in Python before passing to Jinja, (B) Escape in Jinja via filters, (C) Both
**Decision:** A — Escape in Python before passing to Jinja (same as monolithic path)
**Rationale:** The current renderer calls `escape_data()` on user data before Jinja rendering (`renderer.py:86`). The recipe path must do the same: data is escaped once via `escape_data()` before `prepare_recipe_context()` builds the template context. The meta-template must NOT apply additional escaping. This keeps the contract simple and consistent across both paths. Tests must verify that LaTeX special characters and injection-like input are properly neutralized.

### 6. Recipe Schema as JSON Schema (Not YAML Schema)
**Options:** JSON Schema vs custom validation vs Pydantic model only
**Decision:** JSON Schema (same as template data schemas)
**Rationale:** The project already uses JSON Schema for template data validation via `jsonschema` library. Using the same approach for recipe validation maintains consistency and allows recipes to be validated both at load time and via tooling.

## Verification Checklist

- [ ] All three existing templates (protokoll, faktura, avtal) compile without changes
- [ ] New `.sty` files load correctly when used via `\usepackage`
- [ ] `klartex-base.cls` backward compatible — no command changes
- [ ] YAML recipe for protokoll loads and validates
- [ ] Recipe-based rendering produces a valid PDF
- [ ] Recipe-based PDF contains expected content (signature blocks, clauses, etc.)
- [ ] Engine selection: `auto` mode uses `.tex.jinja` when both exist
- [ ] Engine selection: `recipe` mode forces recipe path
- [ ] Engine selection: `legacy` mode forces monolithic path
- [ ] Recipe-only template (no `.tex.jinja`) is discovered by registry
- [ ] CLI `klartex render --engine` works with all three values
- [ ] API `/render` with `engine` field works with all three values
- [ ] `klartex templates` lists recipe-based templates correctly
- [ ] LaTeX special characters in data are properly escaped in recipe output
- [ ] Injection-like input is neutralized in recipe output
- [ ] All existing tests pass
- [ ] New tests cover recipe loading, component mapping, escaping, precedence, and integration
- [ ] Both README.md and README.en.md updated
