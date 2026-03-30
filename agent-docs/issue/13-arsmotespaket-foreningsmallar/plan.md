# Plan: Issue #13 — Annual meeting package: 8 association documents via block engine

## Goal

Verify and demonstrate that all 8 annual meeting document types can be composed using the block engine. Provide example fixtures and documentation. No new recipe templates needed — the issue body states: "the agent selects and orders block types to create each document. No separate template per document type needed."

## Approach

The block engine already supports most block types needed. Once #12 (financial components) lands, all 8 document types can be composed from existing blocks:

| Document | Blocks used |
|----------|------------|
| Kallelse + dagordning | heading, metadata_table, agenda |
| Verksamhetsberättelse | heading, name_roster, text, signatures |
| Ekonomisk årsredovisning | heading, text, resultatrakning*, notapparat*, signatures |
| Revisionsberättelse | heading, text, signatures |
| Budget | heading, budgettabell* |
| Valberedningens förslag | heading, name_roster, signatures |
| Motion | heading, text, clause, signatures |
| Styrelsens svar på motion | heading, text, signatures |

*From #12 (financial components).

All other block types (heading, text, metadata_table, agenda, name_roster, clause, signatures) already exist.

## Steps

### 1. Verify block type coverage

After #12 lands, confirm all required block types exist by running `klartex blocks`. Expected types for annual meeting documents:
- `heading` ✅, `text` ✅, `metadata_table` ✅, `agenda` ✅, `name_roster` ✅, `clause` ✅, `signatures` ✅
- `resultatrakning` (from #12), `budgettabell` (from #12), `notapparat` (from #12)

### 2. Create example fixtures for all 8 document types

Create block engine JSON fixtures for each document type, all using the same fictional association ("Ekbackens Koloniförening") for consistency.

**Files:**
- `tests/fixtures/block_kallelse.json`
- `tests/fixtures/block_verksamhetsberattelse.json`
- `tests/fixtures/block_arsredovisning.json`
- `tests/fixtures/block_revisionsberattelse.json`
- `tests/fixtures/block_budget.json`
- `tests/fixtures/block_valberedning.json`
- `tests/fixtures/block_motion.json`
- `tests/fixtures/block_styrelseyttrande.json`

Each fixture uses `template: "_block"` and composes `body[]` from the appropriate block types. Running text is written directly using `text` blocks.

### 3. Add render tests

**File:** `tests/test_block_engine.py`

Add parametrized render test for all 8 fixtures:
```python
@pytest.mark.parametrize("fixture", [
    "block_kallelse", "block_verksamhetsberattelse", ...
])
def test_arsmotespaket_renders(fixture):
    data = load_fixture(fixture)
    pdf = render("_block", data)
    assert pdf[:5] == b"%PDF-"
```

### 4. Update block engine example

**File:** `klartex/schemas/block_engine.example.json`

Add the new financial block types (resultatrakning, budgettabell, notapparat) to the example — this was already partially addressed by #19 but needs updating after #12 lands.

### 5. Update README

**File:** `README.md`, `README.en.md`

Add a section describing the annual meeting package use case:
- List the 8 document types and which blocks they use
- Show the agent workflow: `klartex blocks` → compose body[] → `klartex render`
- Reference the example fixtures

## Files Summary

| File | Action |
|------|--------|
| `tests/fixtures/block_kallelse.json` | Create |
| `tests/fixtures/block_verksamhetsberattelse.json` | Create |
| `tests/fixtures/block_arsredovisning.json` | Create |
| `tests/fixtures/block_revisionsberattelse.json` | Create |
| `tests/fixtures/block_budget.json` | Create |
| `tests/fixtures/block_valberedning.json` | Create |
| `tests/fixtures/block_motion.json` | Create |
| `tests/fixtures/block_styrelseyttrande.json` | Create |
| `tests/test_block_engine.py` | Modify — add render tests |
| `klartex/schemas/block_engine.example.json` | Modify — add financial blocks |
| `README.md` | Modify — add annual meeting section |
| `README.en.md` | Modify — add annual meeting section |

## Risks

- **#12 dependency** — Financial block types (resultatrakning, budgettabell, notapparat) must land first. Without them, 2 of the 8 documents (årsredovisning, budget) cannot be composed.
- **Text formatting** — Running prose in text blocks is plain text only (no markdown → LaTeX). The agent can use `latex` blocks for formatted content if needed. This is acceptable per the issue body: "Running text fields are written as LaTeX directly by the agent."

## Test Plan

- All 8 fixtures validate against the block engine schema
- All 8 fixtures render to valid PDFs
- `klartex blocks` lists all required block types
- Existing tests still pass
