# Plan: Issue #70 — Protokoll recipe: `subItems` on `agenda_items[]` is accepted and rendered but undocumented

## Goal

Make the protokoll recipe's contract explicit about `subItems` on `agenda_items[]`, and lock the chosen behaviour with a test through `_render_recipe_tex("protokoll", …)`.

The issue's claim was verified against `main` before planning (tex-level, no xelatex): with `tests/fixtures/protokoll.json` plus `agenda_items[2].subItems = ["Intäkter **ökade**", "Kostnader"]`, `jsonschema.validate` passes against both `get_validation_schema()` and `.schema` of the `protokoll` registry entry, and `_render_recipe` emits

```
\noindent \makebox[1.0cm][l]{\textbf{3.1.}}Intäkter \textbf{ökade}\par
\noindent \makebox[1.0cm][l]{\textbf{3.2.}}Kostnader\par
```

So the sub-items render with decimal sub-numbering and (since #60) through the inline filter, but `klartex schema protokoll` does not show the field. Also verified, and relevant for the decision: an unknown key at item level (`bogus`) and at top level (`toplevel_bogus`) passes validation too. The protokoll schema is open everywhere except the `page_template` object, so "accepts undocumented keys" is not specific to `subItems` — it is how the whole recipe schema is built today.

## Approach

**Decision: document `subItems` in the protokoll schema (the issue's first option), do not tighten.** *Provenance: agent judgment* — the issue leaves the direction open, and nothing in it is a user decision. Flag in the PR body as open to challenge. The reasons, each traceable:

1. *Existing convention — recipe schemas leave item arrays open.* `faktura` `lines[]` (`klartex/templates/faktura/schema.json:108-121`), `kvitto` `items[]` (`kvitto/schema.json:97-108`) and protokoll `agenda_items[]` all lack `additionalProperties: false`; the flag is used only on nested configuration objects (`page_template`, `footer`, `logo_offset`) and the financial report structures. Closing `agenda_items[]` alone would make one array stricter than its own document's top level, which still accepts any key. A consistent "reject" is a recipe-wide schema-tightening change — a separate, breaking issue, not this one.
2. *Existing convention — the recipe's `agenda` is the block engine's `agenda`.* `README.md` ("Block-motsvarigheterna … renderas via samma delade makron som block-engine-vägen") and `CLAUDE.md` ("Block-engine equivalents exist for almost every recipe component") establish that recipe components share the block macros. `recipe.yaml` configures the component with `numberingStyle: decimal`, which is exactly the style where the block schema says `subItems` is meaningful ("Only meaningful with `numberingStyle: "decimal"`"). The rendering is the shared component's documented behaviour, not an accident of the macro — the recipe schema is what lags.
3. *Additive for well-formed payloads.* A producer sending an array of strings keeps working; rejecting would break exactly those producers. What the schema addition does tighten is the *shape*: today `"subItems": "text"`, `[123]` or `{"x": 1}` pass as unknown keys (and then crash or misrender in the macro), after the change they fail validation with a readable message. That is formalising a field that already renders, not a new restriction on a supported input. Minutes with sub-points under an item ("3. Ekonomisk rapport — 3.1 Intäkter, 3.2 Kostnader") are a plausible domain shape for a protokoll.
4. *Same move as #60.* PR #68 already put the inline-markup note into `klartex/templates/protokoll/schema.json` for `title`/`discussion`/`decision`; adding `subItems` with the same wording is the same kind of change in the same file.

**The alternative (reject), for the record.** If the user prefers a closed recipe contract, the steps below become: step 1 — a test in `tests/test_renderer.py` that a payload with `subItems` raises `jsonschema.ValidationError` against `get_validation_schema()`, with no render assertions; step 2 — a schema test asserting `agenda_items.items["additionalProperties"] is False` instead of the presence of `subItems`; step 3 — add `"additionalProperties": false` to `agenda_items.items` in the protokoll schema instead of the field; step 4 — omitted (no example/fixture change). Its costs: breaking for producers sending `subItems`, and inconsistent with every other recipe item array and with the protokoll top level until a recipe-wide tightening follows.

**What does not change.** `klartex/templates/_block_macros.tex.jinja` (`render_agenda`, decimal branch lines 88-98 already render `subItems`), `klartex/templates/protokoll/recipe.yaml`, `klartex/components.py`, `klartex/recipe.py`: `extract_component_data` maps `items: agenda_items` and passes the whole item dicts through, so `subItems` already reaches the macro — verified by the tex output above. No `$id` to bump (the protokoll schema has none). No README change: the README documents recipe fields via `klartex schema <name>`, not inline, and the block-engine section already lists `agenda`.

**Schema wording.** Swedish, matching what #60 wrote in the same file, plus the two rendering facts a producer needs: decimal sub-numbering under the parent, and placement after the parent's discussion and decision (macro order: title → discussion → decision → subItems). The description carries technical facts only; the "why document rather than reject" reasoning stays in the PR body.

**Release note.** An additive contract addition on a recipe schema goes into the next release's CHANGELOG (`New features` or `Fixes`, at the release-time author's call), written at release time per the repo's release flow — not in this branch.

## Steps

Red first where the behaviour is new. The render behaviour already exists, so the red/green pair here is the *contract* test (step 2 fails until step 3); step 1 is green from the start and exists to lock the behaviour the issue asks to lock.

1. **`tests/test_renderer.py`** — add `test_recipe_agenda_sub_items_render_with_decimal_numbering` directly after `test_recipe_agenda_items_pass_through_inline_markup` (line 516). Load `FIXTURES / "protokoll.json"`, set `data["agenda_items"][2]["subItems"] = ["Intäkter **ökade**", "Kostnader"]`, then:
   - `jsonschema.validate(data, get_registry()["protokoll"].get_validation_schema())` — the payload is accepted (this is the single assertion that flips under the reject alternative). `tests/test_renderer.py` has no module-level `jsonschema` import; import it inside the test, as `test_faktura_missing_currency_defaults_to_sek` (line 426) does;
   - `tex = _render_recipe_tex("protokoll", data)`;
   - assert `r"\makebox[1.0cm][l]{\textbf{3.1.}}Intäkter \textbf{ökade}\par" in tex` and `r"\makebox[1.0cm][l]{\textbf{3.2.}}Kostnader\par" in tex` — decimal sub-numbering under the third item, inline filter applied (`"**" not in tex`);
   - assert `tex.index("3.1.") > tex.index("Styrelsen godkände den ekonomiska rapporten")` — sub-items come after the parent's decision, the placement the schema text will promise.
   Docstring: one sentence stating that protokoll renders `decimal`, so `subItems` get sub-numbering via the shared `render_agenda` (#70).
2. **`tests/test_schemas.py`** — two tests after `test_protokoll_missing_required` (line 37), both red before step 3:
   - `test_protokoll_schema_documents_sub_items`: read `get_registry()["protokoll"].schema["properties"]["agenda_items"]["items"]["properties"]["subItems"]` and assert `type == "array"`, `items == {"type": "string"}`, and that the description carries the three promises as stable fragments — `"numrerade decimalt"`, `"diskussion och beslut"`, `"Inline-markup"`. Then validate `klartex/templates/protokoll/example.json` (path via `Path(__file__).resolve().parent.parent / "klartex" / "templates" / "protokoll" / "example.json"`, the pattern `tests/test_agent_cli.py:50` uses for the block example) against the same schema — no existing test validates recipe example files, and this one gains `subItems` in step 4. Fails with `KeyError` before step 3.
   - `test_protokoll_sub_items_must_be_strings`: `agenda_items[0].subItems = [123]` and `= "text"` each raise `jsonschema.ValidationError` against the full schema. Both values are accepted today (unknown key), so the test is red before step 3 and makes the shape-tightening the schema addition introduces deliberate.
3. **`klartex/templates/protokoll/schema.json`** — under `agenda_items.items.properties`, after `decision`, add:

   ```json
   "subItems": {
     "type": "array",
     "items": { "type": "string" },
     "description": "Valfria underpunkter, numrerade decimalt under punkten (1.1., 1.2., …) och renderade efter punktens diskussion och beslut. Inline-markup gäller: **fet**, *kursiv*, `kod`, \"citat\", samt ändringsmarkering {+tillagd text+} (grön) och [-struken text-] (röd genomstruken). Radbrytning blir radbrytning."
   }
   ```

   Do not add `additionalProperties`. Re-run step 2: green.
4. **`klartex/templates/protokoll/example.json`** and **`tests/fixtures/protokoll.json`** (identical files today; keep them identical) — give the "Ekonomisk rapport" item `"subItems": ["Intäkter", "Kostnader", "Prognos för 2026"]`. The example is what `klartex example protokoll` shows agents, so the documented field should appear there; the fixture change routes `subItems` through `test_fixture_validates[protokoll]` and the xelatex compile in `test_render_pdf[protokoll]` / `TestRecipeEscaping` without a new compile test. No existing test asserts on the fixture's item content beyond equality with itself (`tests/test_recipe.py::test_component_data_extracted`), and `tests/test_pdf_text_layer.py` does not read it. *Provenance: agent judgment* — #60 left the fixture alone as a scope choice; here the field is the subject of the issue, which is why the canonical example should carry it. Flag in the PR body.
5. Run the targeted tests by node ID — `-k` is a single global expression, so two `-k` flags would keep only the last one:

   ```bash
   pytest tests/test_renderer.py::test_recipe_agenda_sub_items_render_with_decimal_numbering \
          tests/test_schemas.py::test_protokoll_schema_documents_sub_items \
          tests/test_schemas.py::test_protokoll_sub_items_must_be_strings \
          "tests/test_schemas.py::test_fixture_validates[protokoll]"
   ```

   then the full suite with xelatex on PATH (`pytest -n auto`). CI fails on any skipped xelatex test, so no `pytest.skip` shortcuts.
6. PR body: state the direction as an agent judgment open to challenge (with the reject alternative), note the fixture/example change, the release-note item including the shape-tightening for malformed `subItems`, and the out-of-scope observation that the recipe schema is open at every level (a candidate for a separate recipe-wide issue if a strict contract is wanted). End with `Closes #70`.

## Risks

- **Contract widening is one-way.** Once `subItems` is in the protokoll schema, removing it is a breaking change. Low — the behaviour ships already and the block schema carries the same field.
- **Direction may be wrong for the user.** If a strict recipe contract is wanted, the flip is small and described above; but tightening `agenda_items[]` alone leaves the schema inconsistent (open top level, open sibling recipes), so a "reject" answer likely wants a follow-up issue for recipe-wide tightening rather than a one-off here.
- **Malformed `subItems` start failing validation.** A producer sending a non-array or non-string members passes today (unknown key) and fails after the schema addition. Such payloads were never rendered correctly (the macro iterates the value and inline-filters each member), so treating them as unsupported keeps the risk Low — but it belongs in the release note, and step 2's negative test makes the tightening deliberate rather than incidental.
- **Typos remain silent.** Without `additionalProperties: false`, `subitems` (lowercase) is still accepted and ignored — pre-existing for every field in every recipe, unchanged by this plan; noted as out of scope.
- **Coupling to `recipe.yaml`.** The documented sub-numbering holds because `recipe.yaml` pins `numberingStyle: decimal`; the `section` branch of `render_agenda` ignores `subItems` entirely. If the recipe's numbering style ever changes, the documented field would silently stop rendering. Step 1's render assertion is what would catch that.
- **Fixture change.** `test_render_pdf[protokoll]` and the `TestRecipeEscaping` compile tests render the changed fixture; they assert `%PDF-` only, and the render of the exact sub-item content was verified at tex level before planning.

## Test Plan

- `tests/test_renderer.py::test_recipe_agenda_sub_items_render_with_decimal_numbering` — schema acceptance, decimal sub-numbering (`3.1.`, `3.2.`), inline filter applied inside a sub-item, sub-items placed after the parent's decision. Pure tex-level, runnable without xelatex.
- `tests/test_schemas.py::test_protokoll_schema_documents_sub_items` — the contract is present in the schema `klartex schema protokoll` shows, with its three documented promises, and `klartex/templates/protokoll/example.json` validates against it; seen failing before step 3, passing after.
- `tests/test_schemas.py::test_protokoll_sub_items_must_be_strings` — non-array / non-string `subItems` are rejected; red before step 3 (accepted as an unknown key today), green after.
- `tests/test_schemas.py::test_fixture_validates[protokoll]` — the updated fixture with `subItems` validates.
- xelatex: `tests/test_renderer.py::test_render_pdf[protokoll]` and `tests/test_recipe.py::TestRecipeEscaping` compile the updated fixture; `klartex -d tests/fixtures/protokoll.json -t protokoll -o <scratch>/protokoll.pdf` and a `pdftotext` glance to see `3.1.`–`3.3.` under "Ekonomisk rapport".
- Full `pytest -n auto` green with xelatex on PATH, 0 skipped (baseline after PR #71: 365 passed; expected 368 with the three new tests).
