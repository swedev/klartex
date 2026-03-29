# Research: Agent-friendly CLI (#19)

## Summary

The block engine has full per-block JSON Schemas in `klartex/schemas/blocks/` (13 files), but the top-level `block_engine.schema.json` does not reference them. An agent calling `klartex schema _block` sees a generic `body.items` with no indication of available block types or their fields. All the data needed for a discriminated-union schema already exists — it just needs to be assembled.

## Findings

### Current state

- **13 block schemas** exist in `schemas/blocks/`, one per block type. Each schema uses `const` on the `type` field and declares all properties with `additionalProperties: false`.
- `block_engine.schema.json` defines `body.items` as a generic `{"type": "object", "required": ["type"]}` — no `oneOf`, no `$ref`.
- The renderer (`renderer.py:82-101`) already validates each block against its individual schema at runtime. The schemas are correct and complete — they're just invisible to CLI consumers.
- `components.py:_COMPONENTS` maps block names to `ComponentSpec` with `description` and `block_schema_path`. Only entries with `block_schema_path` are valid block types (13 of them; 3 legacy recipe-only components lack schemas).
- Test fixtures (`tests/fixtures/`) contain 4 block-engine examples that could seed the `example` subcommand.

### Block types available (13)

| Block | Description | Required fields (beyond `type`) |
|-------|-------------|--------------------------------|
| `heading` | Section heading | `text`; optional `level` (1-3) |
| `text` / `preamble` | Free-form paragraph | `text` |
| `title_page` | Full-page title | all optional (`party1`, `party2`, `title`) |
| `parties` | Side-by-side party display | `party1`, `party2` (objects with `name` required) |
| `clause` | Numbered legal clause | `title`, `items` (strings or nested objects) |
| `signatures` | Signature block | `parties` (array, exactly 2); optional `new_page` |
| `metadata_table` | Key-value table | `entries` (array of `{label, value}`) |
| `attendees` | Attendee/adjuster list | `attendees` (string array); optional `adjusters` |
| `agenda` | §-numbered agenda | `items` (objects with `title`, optional `discussion`/`decision`) |
| `name_roster` | Name/role table | `title`, `people` (objects with `name`, `role`) |
| `page_break` | Force page break | none |
| `latex` | Raw LaTeX passthrough | `source` |
| `adjuster_signatures` | Adjuster signature lines | `adjusters` (string array); optional `label` |

### Implementation approach for each proposed change

#### 1. Discriminated-union schema

Two options:

- **A. Build at startup** — modify `registry.py:discover_templates` to dynamically compose `body.items.oneOf` from all `ComponentSpec.get_block_schema()` results when registering the `_block` template. Keeps the static `block_engine.schema.json` minimal and avoids schema drift.
- **B. Static file** — inline all block schemas into `block_engine.schema.json`. Simpler to read, but must be kept in sync manually.

**Recommendation: Option A** (dynamic assembly). The per-block schemas already exist and are authoritative. Building the union at startup guarantees it's always in sync. The static file can keep its current shape (or even be removed) since the registry overwrites `.schema`.

Rough implementation:
```python
# In registry.py, after loading block_schema
from klartex.components import _COMPONENTS
block_schemas = []
for name, spec in sorted(_COMPONENTS.items()):
    s = spec.get_block_schema()
    if s:
        block_schemas.append(s)
if block_schemas:
    block_schema["properties"]["body"]["items"] = {"oneOf": block_schemas}
```

#### 2. `klartex example <template>` subcommand

- For `_block`: assemble a hardcoded or generated example JSON showing one instance of each block type with minimal valid data. Can be stored as `schemas/block_engine.example.json` or generated from the schemas' defaults/examples.
- For recipe templates: use existing test fixtures (`tests/fixtures/protokoll.json`, `faktura.json`) or store canonical examples alongside each template.
- Storing static `.example.json` files is simplest and most readable.

#### 3. `klartex blocks` subcommand

Trivial — iterate `_COMPONENTS`, filter to those with `block_schema_path`, print name + description. ~10 lines in `cli.py`.

### Risk / constraints

- The `oneOf` discriminated union relies on `type: {"const": "heading"}` etc. in each block schema. All 13 schemas already use this pattern — no changes needed.
- JSON Schema `oneOf` with `const` discriminators is well-supported by OpenAI/Anthropic structured output and by standard validators.
- Adding `oneOf` changes the schema output but not validation behavior (runtime already validates per-block). No breaking change.

## Recommendation

Implement in this order:

1. **`klartex blocks`** — lowest effort, immediately useful, ~10 LOC.
2. **Dynamic `oneOf` assembly** — medium effort (~20 LOC in `registry.py`), highest impact. This is the core deliverable.
3. **`klartex example _block`** — store a canonical example JSON, add CLI subcommand. Nice complement to the schema.

All three changes are additive and non-breaking. Can ship in a single PR.

## Open Questions

1. Should `klartex schema _block` include the full `oneOf` inline, or use `$ref` pointers to separate block schema files? Inline is simpler for agents (one JSON blob, no dereferencing needed).
2. Should example JSON files live alongside schemas or in a separate `examples/` directory?
3. Should the `example` subcommand output be valid for rendering (i.e., actually produce a PDF), or is a structural-only example sufficient?

## Sources

- `klartex/schemas/block_engine.schema.json` — current top-level schema
- `klartex/schemas/blocks/*.schema.json` — 13 per-block schemas
- `klartex/components.py` — component registry with descriptions
- `klartex/registry.py` — template discovery and schema loading
- `klartex/renderer.py:82-101` — runtime per-block validation
- `tests/fixtures/avtal_block.json` — most comprehensive block engine example
