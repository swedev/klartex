# Plan: Issue #19 — Agent-friendly CLI: full block schema, example command, blocks listing

## Goal

Make the klartex CLI fully self-describing so an agent can go from `klartex schema _block` to valid JSON without reading source code. Three additions: discriminated-union schema, `blocks` listing, and `example` subcommand.

## Approach

All 13 block types already have individual JSON Schemas in `schemas/blocks/` with `"const"` discriminators on the `type` field. The top-level `block_engine.schema.json` just doesn't reference them. The strategy is:

1. Dynamically compose `body.items.oneOf` at startup from existing per-block schemas (no manual sync needed)
2. Add two small CLI subcommands (`blocks`, `example`)
3. Ship a canonical example JSON for `_block`

All changes are additive and non-breaking.

## Steps

### 1. Dynamic `oneOf` assembly in `registry.py` (highest impact)

In `discover_templates()`, after loading `block_engine.schema.json`, iterate `_COMPONENTS` and collect all block schemas via `get_block_schema()`. Replace `block_schema["properties"]["body"]["items"]` with `{"oneOf": [list of block schemas]}`.

**File:** `klartex/registry.py`

```python
from klartex.components import _COMPONENTS

block_schemas = []
for name, spec in sorted(_COMPONENTS.items()):
    s = spec.get_block_schema()
    if s:
        block_schemas.append(s)
if block_schemas:
    import copy
    block_schema = copy.deepcopy(block_schema)
    block_schema["properties"]["body"]["items"] = {"oneOf": block_schemas}
```

This ensures `klartex schema _block` returns a complete, self-describing schema with every block type and its fields inlined.

### 2. `klartex blocks` subcommand

Add a `blocks` command to `cli.py` that lists all block types with descriptions, filtered to those with `block_schema_path` (excludes legacy recipe-only components).

**File:** `klartex/cli.py`

```python
@app.command("blocks")
def list_blocks():
    """List available block types for the block engine."""
    from klartex.components import _COMPONENTS
    for name, spec in sorted(_COMPONENTS.items()):
        if spec.block_schema_path:
            typer.echo(f"  {name:25s} {spec.description}")
```

### 3. `klartex example <template>` subcommand

Add an `example` command that prints a canonical JSON example for a given template.

**File:** `klartex/cli.py`

```python
@app.command("example")
def show_example(template: str = typer.Argument(help="Template name")):
    """Print an example JSON input for a template."""
    ...
```

Store example files alongside schemas:
- `klartex/schemas/block_engine.example.json` — for `_block`
- `klartex/templates/<name>/example.json` — for recipe templates

The example for `_block` should include one instance of each block type with minimal valid data and be renderable to PDF.

**File:** `klartex/schemas/block_engine.example.json` (new)

### 4. Tests

Add tests for:
- `klartex schema _block` returns schema with `oneOf` containing all 13 block types
- `klartex blocks` lists all block types
- `klartex example _block` outputs valid JSON that passes schema validation

**File:** `tests/test_cli.py` (or new `tests/test_agent_cli.py`)

### Files Summary

| File | Change |
|------|--------|
| `klartex/registry.py` | Dynamic `oneOf` assembly in `discover_templates()` |
| `klartex/cli.py` | Add `blocks` and `example` subcommands |
| `klartex/schemas/block_engine.example.json` | New — canonical block engine example |
| `tests/test_cli.py` | Tests for new subcommands and schema completeness |

## Risks

- **Schema size**: The inlined `oneOf` schema will be larger (~200 lines of JSON). This is a feature, not a bug — agents need the complete picture in one request.
- **Import order**: `registry.py` importing from `components.py` — already the case transitively via `block_engine.py`, so no circular import risk.

## Test Plan

- `klartex schema _block | python3 -c "import sys,json; s=json.load(sys.stdin); assert 'oneOf' in s['properties']['body']['items']"` — verify `oneOf` present
- `klartex blocks` — verify output lists 13 block types
- `klartex example _block | python3 -c "import sys,json; json.load(sys.stdin)"` — verify valid JSON
- `klartex example _block | klartex -o /tmp/test.pdf` — verify example renders to PDF (optional, requires xelatex)
- Run existing test suite to confirm no regressions
