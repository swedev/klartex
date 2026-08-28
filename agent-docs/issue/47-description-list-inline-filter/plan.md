# Plan: Issue #47 — `description_list` renders `value` without the inline filter

## Goal

Make `description_list` treat its text like every other text-bearing block: `entry.value` **and** `entry.label` (the issue's "check while you are in there" — confirmed to have the same gap) must go through the inline-markup filter so `**bold**`, `*italic*`, backticks, smart quotes, and the change markers `{+…+}` / `[-…-]` render instead of appearing as literal characters in the PDF. (The issue predates #52 — the removed-marker notation is now `[-…-]`, not `{-…-}`.) The fix must cover both surfaces that use the block: the block engine (`description_list` block) and the recipe path (document metadata rendered through the same macro).

## Approach

The rendering lives in one place — `render_description_list` in `klartex/templates/_block_macros.tex.jinja` — shared by `_block_engine.tex.jinja` (line 317) and `_recipe_base.tex.jinja` (line 78, protokoll/kvitto metadata). Applying the filters inside the macro fixes both paths at once, which is also how `render_heading` in the same file already does it (`\VAR{text | inline}`).

The block renders as a `tabularx` with an `l` label column and an `X` value column, so the plain `inline` filter is wrong here — the codebase has cell-specific variants for exactly this (`renderer.py`), and the `fields` block arm at `_block_engine.tex.jinja:284` is the established pattern to mirror:

- `entry.label` (LR-mode `l` column, no in-cell line break exists) → `| inline_flat` (`\n` collapses to a space)
- `entry.value` (paragraph-mode `X` column) → `| inline_cell` (`\n` becomes `\newline`; a bare `\\` would end the table row)

**Latent bug found during exploration, fixed as part of this change:** the three inline filters are `@jinja2.pass_context` and read `ctx.get("lang", "sv")`, but `_block_macros.tex.jinja` is imported *without* `with context` in both `_block_engine.tex.jinja:2` and `_recipe_base.tex.jinja:2`. Inside an imported macro the filter therefore never sees the document `lang` and always falls back to `"sv"`. Verified empirically: a `lang: "en"` document renders Swedish smart quotes (`”hello”`) in headings (via `render_heading`'s existing `| inline`) while the `text` block in the same document correctly renders English quotes (`“hello”`). Without this fix the new filters in `render_description_list` would carry the same defect, so both templates' imports gain `with context` in this change. *Provenance: agent judgment* — the decision to bundle the import fix here (rather than land `description_list` with the known-wrong `sv` fallback and file the import bug separately) is mine; flag it in the PR body.

Nothing else in the pipeline needs to change: `description_list` nests no blocks and has no raw-LaTeX field, so `_restore_block_types` is untouched, and the `inline` filters operate on pre-escaped text, which is what both paths hand them (`render()` escapes before Jinja; the recipe path receives `escaped_data`).

Out of scope, noted for follow-up: `render_agenda` in the same macro file has the identical gap (`item.title`, `item.discussion`, `item.decision`, `subItems` render without any inline filter). That is a separate block with its own test surface — propose filing a follow-up issue rather than widening this fix.

## Steps

1. **`klartex/templates/_block_macros.tex.jinja`** — in `render_description_list`, change the row emission to:
   ```
   \textbf{\VAR{entry.label | inline_flat}} & \VAR{entry.value | inline_cell} \\
   ```
2. **`klartex/templates/_block_engine.tex.jinja`** and **`klartex/templates/_recipe_base.tex.jinja`** — add `with context` to the `_block_macros.tex.jinja` import line so the `pass_context` inline filters see the document `lang`:
   ```
   \BLOCK{from '_block_macros.tex.jinja' import render_agenda, render_heading, render_description_list with context}
   ```
   (Leave the `_financial_macros` / `_footer_macros` imports alone — verified they use no context filters.)
3. **`klartex/schemas/blocks/description_list.schema.json`** — document the new behavior for agent introspection (`klartex schema _block`): note on the block or the `label`/`value` fields that inline markup applies, mirroring `table.schema.json` ("Cells pass through inline markup.") / the Swedish field-level wording in `text.schema.json`. Schema descriptions are user-facing → Swedish for field descriptions, consistent with the file's existing style (its top-level description is English; follow whichever style the surrounding text uses per field).
4. **`tests/fixtures/block_stadgeandring.json`** — put inline markup back into the `description_list` entries that had to drop it during #40/#45, e.g. give one entry a change-marked value (`"Beslutsform:"` → `"Två stämmor, {+enkel majoritet+}"` or similar) so the canonical fixture demonstrates and compile-tests the behavior.
5. **`tests/test_block_engine.py`** — tex-level tests using the module-level `_render_tex` helper (line 1067), no xelatex needed:
   - change markers in a `description_list` value → `\kxadded{…}` / `\kxremoved{…}` in tex, no literal `\{+` / `[-` left;
   - `**bold**` in a value → `\textbf{…}`; `**bold**` in a label → assert the *nested* form `\textbf{\textbf{bold}}` and that no literal `**` remains (the label already has an outer `\textbf`, so a bare `\textbf`-in-tex assertion would pass even without the fix);
   - `\n` in a value → `\newline` (cell mode), and no bare `\\` inside the cell (extend `TestCellSafeLineBreaks`);
   - `\n` in a label → collapses to a space (flat mode);
   - `lang: "en"` + `"quoted"` in a `description_list` value → English smart quotes `“…”` in tex — locks the `with context` fix on the block-engine template; a sibling assert on a heading in the same document locks the heading half.
6. **Recipe-path tests** (`tests/test_renderer.py` via the existing `_render_recipe_tex` helper, and/or `tests/test_recipe.py` which already builds synthetic recipes in `tmp_path`):
   - a kvitto/protokoll payload with a change marker or bold in a metadata-mapped field → `\kxadded{…}` / `\textbf{…}` in tex — proves the recipe surface got the filter;
   - a synthetic `lang: en` recipe (built via `load_recipe` from a tmp YAML, since all shipped recipes are `sv`) with a `"quoted"` metadata value → English smart quotes — locks `with context` on `_recipe_base.tex.jinja` specifically; marker/bold assertions alone cannot, because they are lang-independent and `sv`-fallback would mask a missing `with context`.
7. Run the focused new tests by node ID (they are pure tex-level, no xelatex), then the full `pytest` suite including the fixture compile tests.

## Risks

- **Behavior change for existing payloads.** Any producer already sending literal `**`, backticks, `"`, `{+…+}` or `[-…-]` in `description_list` values/labels (or recipe metadata such as protokoll `location`/`attendees`) will see them interpreted after this change — straight quotes become typographic quotes in every value. This is precisely the intended alignment ("the divergence is silent" is the bug), and it matches what every other text block already does, but it belongs in the CHANGELOG `Fixes` entry at the next release.
- **`with context` widens the blast radius slightly**: `render_heading`'s smart quotes start honoring `lang` for non-Swedish documents (a bugfix, but a visible rendering change for any existing `lang: "en"` document with quotes in headings). `render_agenda` uses no filters, so it is unaffected.
- **Table-cell safety**: `\kxadded`/`\kxremoved`/`\textbf` inside `tabularx` cells are already exercised by the `table` block's marker test (`test_markers_work_in_table_cells`), and `inline_cell`/`inline_flat` exist specifically for cell contexts — low residual risk, covered by the compile test on the updated fixture.
- **Recipe labels come from `recipe.yaml`, not user data**, and are not escaped — they are repo-authored plain strings (`"Datum:"`), and `inline_flat` on them is a no-op in practice. No recipe ships markup in labels today.

## Test Plan

- New tex-level assertions in `tests/test_block_engine.py` (markers, bold in value, nested-`\textbf` label assertion, `\n` handling in both columns, `lang: en` smart-quote propagation) — pure source-level tests, runnable without xelatex by node ID, e.g. `pytest tests/test_block_engine.py::TestChangeMarking tests/test_block_engine.py::TestCellSafeLineBreaks` (note: `-k "not xelatex"` filters names, not `skipif` markers, so it is not a reliable "fast only" selector — rely on node IDs for the focused pass and let `skipif` handle machines without xelatex).
- New recipe-path tests: marker/bold through `_render_recipe_tex`, plus a synthetic `lang: en` recipe asserting English smart quotes in metadata.
- Updated `tests/fixtures/block_stadgeandring.json` compiles through the existing xelatex fixture tests. The PDF text-layer round-trip suite (`tests/test_pdf_text_layer.py`) currently exercises `text` blocks only — it stays green; a `description_list` round-trip case is optional hardening, not claimed coverage.
- Full `pytest` green locally with xelatex on PATH; CI runs the same suite and fails if any xelatex test is skipped.
