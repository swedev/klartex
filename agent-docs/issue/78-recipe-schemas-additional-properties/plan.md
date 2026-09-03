# Plan: Issue #78 — Recipe schemas accept unknown keys silently — decide on `additionalProperties: false` recipe-wide

## Goal

Decide the open question the issue poses — should recipe contracts be closed? — and, having decided **yes**, make every object level in all seven recipe schemas (`klartex/templates/*/schema.json`) carry `additionalProperties: false`, so a producer's typo (`subitems` for `subItems`, `discusion` for `discussion`) fails validation with a message naming the unexpected key instead of rendering as if the field had been omitted. A recipe-wide test in `tests/test_schemas.py` walks every loaded recipe schema and asserts the closure, so a new recipe or a new sub-object cannot reopen the surface. The recipe surface then matches the block engine's convention — every block schema rejects unknown keys on the block object — and goes one level further, closing every nested object too.

## Approach

### State verified before planning

Verified against `main` at `31368b1` (0.19.0 in `CHANGELOG.md`; #79, #96, #99 merged):

- `#79` is closed and merged — the top-level `footer` on faktura/kvitto is now a `{"not": {...}}` property that rejects with guidance, so the sequencing concern in the issue is resolved. That `footer` entry is a property, not an object level; closing the top-level object leaves it as-is and its message still wins: `footer` is declared in `properties`, so it is not an additional property (verified — the error keeps validator `not`, path `["footer"]` and the guidance text).
- Walking the **loaded** registry schemas (after `registry.py::_inject_page_template`) for `type: object` nodes without `additionalProperties: false` finds exactly **13 open nodes**, all in the seven files, none in the injected `page_template` subtree (which the slot model already closes throughout — `page_templates.py` lines 371, 518, 1100, 1115, 1135):

  | Recipe | Open object levels |
  |---|---|
  | `protokoll` | top level, `agenda_items.items` |
  | `faktura` | top level, `sender`, `recipient`, `lines.items` |
  | `kvitto` | top level, `sender`, `items.items` |
  | `resultatrakning`, `balansrakning`, `budgetrapport`, `sie-exportrapport` | top level only (all nested objects, including `balansrakning`'s `definitions`, are already closed) |

- **All seven `example.json` files and all seven `tests/fixtures/<recipe>.json` fixtures validate against the fully closed schemas** — no fixture carries an undocumented key. The whole test suite (794 passed, 9 skipped — the usual font/`serve`-less skips) also passes in a scratch copy of the repo with all 13 nodes closed, so no test payload relies on an extra key either. The gap the issue expected this to surface does not exist today.
- The error jsonschema produces for an unknown key is `Additional properties are not allowed ('subitems' was unexpected)` with `absolute_path` = the *parent object* (`["agenda_items", 2]`), `validator == "additionalProperties"`. `klartex/server/render.py` already maps `ValidationError` to `400 validation_error` with `detail.message` + `detail.path`, so `klartex serve` needs no change — the key is named in the message, the object in the path.
- `tests/test_schemas.py` already has `RECIPE_SCHEMA_NAMES` (the seven names), `test_fixture_validates` parametrized over all seven, and `test_recipe_example_validates` parametrized over faktura/kvitto only. Line 313 asserts `margins["additionalProperties"] is False` — the same assertion style the new test extends recipe-wide.

### The decision: close

Every recent contract change on the recipe path has moved from silent tolerance to rejection with guidance — #70 typed `subItems` so malformed values are rejected rather than misrendered, #79 rejects the top-level `footer` with a message pointing at the slot, #99 made `sender` required and its name non-blank. Closing the objects is the general form of those three decisions. Since no shipped example, fixture or test relies on an extra key, the change costs nothing in this repo; the only cost is to a producer sending keys the schema never documented, and for that producer a loud `validation_error` naming the key is the fix the issue asks for. See Design Decision 1 for the consequence assessment.

### Where each change lives

1. **The 13 nodes** get a literal `"additionalProperties": false` in the schema files, placed right after `"required"` (or after `"type": "object"` where there is no `required`), matching how the already-closed nodes in the financial schemas are written. Nothing else in the files moves.
2. **The guard test** iterates over every non-block template in `get_registry()` (`not info.is_block_engine`) rather than the hard-coded `RECIPE_SCHEMA_NAMES` tuple, so a newly discovered recipe is covered without anyone remembering to list it. For each it walks `info.schema` (post-injection) recursively — through `properties`, `items`, `definitions`, `oneOf`/`anyOf`/`allOf` — and asserts `additionalProperties is False` on every object node. An object node is a dict whose `type` is `"object"`, or a list containing `"object"` (the nullable `["object", "null"]` form `page_template.margins` uses), or that carries `properties` without a `type`. Walking the loaded schema rather than the file means the injected `page_template` subtree is covered too, so a future open object in the slot model also trips it. `{"not": {...}}` nodes and `additionalProperties: {schema}` forms do not occur in recipe data schemas; the walk asserts `False` exactly.
3. **Rejection tests** — one parametrized test per shape the issue names: `protokoll` `agenda_items[0].subitems`, `protokoll` `agenda_items[0].discusion`, a top-level unknown key on each of the seven recipes, and a nested unknown key on faktura `lines[0]` and kvitto `items[0]`. Each asserts `ValidationError`, `excinfo.value.validator == "additionalProperties"`, the key's name in `message`, and `list(absolute_path)` equal to the parent object's path — the last is what `klartex serve`'s `detail.path` becomes.
4. **`test_recipe_example_validates` extends to all seven** recipes (currently faktura/kvitto), since `klartex example <name>` exists for every recipe and the closure is exactly the kind of change an example could regress on.
5. **One server test** in `tests/test_server.py` (guarded by the existing `importorskip`, using the module-level `client`) posts a minimal literal protokoll payload — `meeting_type`, `date`, `attendees`, one agenda item with `title` and `subitems` — and asserts `400`, `detail.type == "validation_error"`, `"subitems"` in `detail.message`, `detail.path == ["agenda_items", 0]`. It runs without xelatex because validation fails before compilation.
6. **No `CHANGELOG.md` edit in the PR**: per the release flow in `CLAUDE.md`, the entry is written at release from the PR body. The PR body carries a `Breaking changes` paragraph in the wording of Design Decision 1 so the release entry can be lifted from it.
7. **No README edit**: `README.md` was trimmed to what does not go stale (`bb9cb51`), and the schema is the discovery surface — `klartex schema <name>` now shows the closure itself.
8. **klartex.se pre-release check** (outside this repo, before the release that ships this; owner: the user, at release time): in the klartex.se repo, extract every recipe payload from `llms.txt` and the landing-page example, and — where they are available — a sample of the requests the site actually generates for each recipe, and run `jsonschema.validate(payload, get_registry()[name].schema)` with this branch's klartex on `PYTHONPATH`; pass condition is zero `ValidationError`s. This is the same check #79 and #99 did for their breaking edges. Any key found there that the schema does not carry is either a documentation error on klartex.se or a real undocumented field — in the second case, document it in the schema (as #70 did for `subItems`) rather than leave the level open.

## Steps

1. Read `tests/test_schemas.py` in full and `tests/test_server.py`'s existing 400-contract tests to reuse their helpers (`_MINIMAL_RECIPE_PAYLOAD`, `RECIPE_SCHEMA_NAMES`, the module-level `client` in `test_server.py` — there is no client fixture, and the module imports neither `json` nor a fixture-path helper).
2. Add `"additionalProperties": false` to the 13 nodes listed above — `klartex/templates/protokoll/schema.json` (2), `faktura/schema.json` (4), `kvitto/schema.json` (3), and the top-level object in `resultatrakning`, `balansrakning`, `budgetrapport`, `sie-exportrapport` (1 each). Keep the existing key order and 2-space indentation; put the new key after `"required"` where present.
3. In `tests/test_schemas.py`, add `_object_nodes(schema)` (recursive generator over dicts and lists yielding every object node — `type == "object"`, `"object" in type` when `type` is a list, or `properties` present without `type` — with its path for the assertion message) and `test_recipe_schemas_are_closed_at_every_object_level`, parametrized over `[name for name, info in get_registry().items() if not info.is_block_engine]`, asserting `node.get("additionalProperties") is False` for every yielded node. Add a one-line assertion (in the same test or beside `test_discover_all_templates`) that the discovered non-block names equal `set(RECIPE_SCHEMA_NAMES)`, so the static tuple the other tests use cannot drift from discovery. The docstring states the promise: the recipe surface rejects unknown keys like the block engine does, and names #78.
4. Add `test_recipe_unknown_key_is_rejected` parametrized over `(template_name, mutate, expected_path)` cases: protokoll `agenda_items[0]["subitems"]` → `["agenda_items", 0]`; protokoll `agenda_items[0]["discusion"]` → `["agenda_items", 0]`; faktura `lines[0]["price"]` → `["lines", 0]`; faktura `sender["adress"]` → `["sender"]`; kvitto `items[0]["amout"]` → `["items", 0]`; and a top-level `"organisation"` on each of the seven → `[]`. Build each payload from the fixture (`FIXTURES / f"{name}.json"`), copy, mutate, and assert validator, message and path as described in "Where each change lives" 3.
5. Extend `test_recipe_example_validates`'s parametrize list to `RECIPE_SCHEMA_NAMES` (move the tuple above the test or reference it after definition — it is currently defined below that test).
6. Add the `klartex serve` test in `tests/test_server.py`: POST `{"template": "protokoll", "data": {"meeting_type": "Styrelsemöte", "date": "2026-02-10", "attendees": ["A"], "agenda_items": [{"title": "Öppnande", "subitems": ["x"]}]}}` via the module-level `client`, assert status 400, `detail.type == "validation_error"`, `"subitems"` in `detail.message`, `detail.path == ["agenda_items", 0]`.
7. Run `pytest tests/test_schemas.py tests/test_server.py tests/test_recipe.py -q` first (fast), then the full suite sequentially (`pytest -q`, no `-n auto` without asking) — the only expected difference from the pre-change run is the new tests passing.
8. Run `klartex schema protokoll | python -c "import json,sys; s=json.load(sys.stdin); print(s['additionalProperties'], s['properties']['agenda_items']['items']['additionalProperties'])"` with the repo code on `PYTHONPATH` (the `klartex` shim on PATH is a stale pyenv install — use `python -m klartex.cli` or a venv) and confirm `False False`.
9. Write the PR body: what changed, the `Breaking changes` paragraph (unknown keys at any level of a recipe payload are now rejected with `validation_error` naming the key; producers relying on extra keys being ignored must drop them), the note that no shipped example or fixture needed changing, the klartex.se pre-release check as a follow-up item, and Design Decisions 1–3 listed as agent judgment open to override. End with `Closes #78`.

## Design Decisions

### 1. Close the recipe contracts

- **Options:** (a) `additionalProperties: false` at every object level in all seven recipe schemas; (b) leave them open and record the reasoning in the issue, removing the partial closures for consistency; (c) close only the levels the issue's typo examples touch (`agenda_items[]`).
- **Decision:** (a).
- **Provenance:** agent judgment. The issue explicitly leaves the choice open ("Decide whether recipe contracts should be closed"); no comment settles it. The direction follows the *existing convention* of the last three recipe-contract changes (#70 rejects malformed `subItems`, #79 rejects the top-level `footer` with guidance, #99 requires `sender`) and the block engine's closed block schemas, but no user text states the general rule, so it stays agent judgment surfaced in the PR body.
- **If wrong:** bounded. Reverting is deleting one line at each of 13 nodes plus the guard test; nothing is migrated or lost. A producer hit by the change gets a `400 validation_error` naming the key at a path — a loud failure with the fix in the message, not silent damage — and can be unblocked by dropping the key. The only known consumer is klartex.se (the user's own site; established in the project's memory notes, not in the repo or the issue — which is why the rollout risk is rated Medium and the pre-release check in step 8 under "Where each change lives" is part of the plan). Breaking changes on this surface are routine and ship under `Breaking changes` in every recent release.
- **Rationale:** the issue's own framing is that the two surfaces make opposite promises and the recipe surface is inconsistent with itself; (b) would keep a producer's typo invisible, the exact defect behind #70, and (c) would leave the contract inconsistent the way the deferral note in the issue warns against. What would make (b) right: a documented producer that deliberately sends extra keys for its own bookkeeping through klartex — none is known, and the klartex.se check would reveal one before release.

### 2. Literal `additionalProperties: false` in the schema files, guarded by a test — not injected at load time

- **Options:** (a) write the key into each object level of the seven files and add a recipe-wide test; (b) have `registry.py` walk each recipe schema at load and set it, the way `page_template` is injected.
- **Decision:** (a).
- **Provenance:** user decision — the issue text says "add `additionalProperties: false` at every object level in all seven recipe schemas, and add a test in `tests/test_schemas.py` that asserts it recipe-wide".
- **If wrong:** bounded — (b) is a small refactor that replaces 13 literal lines with one loop; the guard test stays the same either way.
- **Rationale:** the files are what a contributor reads and edits; a contract written in the file is visible without knowing about a load-time walk, and the test is what prevents the regression the issue worries about. (b) would make the file lie about the contract it enforces. What would make (b) right: if the number of recipes grew to the point where the per-file key became noise — not the case at seven.

### 3. The guard test walks the loaded schema, including the injected `page_template` subtree

- **Options:** (a) walk `get_registry()[name].schema` (post-injection); (b) walk the raw `schema.json` file only.
- **Decision:** (a).
- **Provenance:** agent judgment.
- **If wrong:** bounded — switching the test to read the file is a two-line change. The injected subtree is already fully closed, so (a) passes today.
- **Rationale:** the contract a producer meets is the loaded one. A future open object in the slot model would reopen the recipe surface just as surely as one in the file, and (a) catches both; `test_schema_files_hold_only_the_placeholder` already covers the file side of the injection. What would make (b) right: if the slot model ever needs an intentionally open object (e.g. a free-form `fields` map) — then the test would have to exempt the subtree, and (b) would be the simpler form.

### 4. No CHANGELOG or README edit in the PR

- **Options:** (a) PR body carries the `Breaking changes` paragraph; the CHANGELOG entry is written at release; README untouched. (b) Add an `Unreleased` CHANGELOG entry and a README sentence about unknown keys.
- **Decision:** (a).
- **Provenance:** existing convention — `CLAUDE.md` "Releases" step 2 writes the dated entry at release time; the #96 plan applied the same rule ("No `CHANGELOG.md` change in the PR; the entry is written at release from the PR body"); `README.md` was deliberately trimmed to what does not go stale (`bb9cb51`).
- **If wrong:** bounded — both are one-paragraph additions.
- **Rationale:** the schema is the discovery surface (`klartex schema <name>` shows the closure), and the release flow already sources the entry from the PR body.

## Risks

- **klartex.se documents a key the schema does not carry.** #79's review found `llms.txt` documenting the old `footer`; a recipe key in the same position would start failing for producers who follow that documentation. Mitigated by the pre-release check (step 8 under "Where each change lives"); if a real undocumented field surfaces, it is added to the schema before release, not left open.
- **`detail.path` points at the parent object, not the offending key.** This is how jsonschema reports `additionalProperties`; the key is only in `message`. Acceptable — the message names it — and locked by the server test so a later change to path extraction cannot silently drop it. A "did you mean `subItems`" hint is out of scope.
- **Rollout risk is Medium even though implementation risk is Low.** This is a breaking change to a published contract, and the repo cannot prove who consumes it beyond klartex.se. The pre-release check is the mitigation; it needs to look at generated requests where possible, not only documentation examples.
- **The guard test over-reaches.** A future intentionally open object anywhere in a recipe schema or the slot model would need an explicit exemption in the test. That is the intended friction — the exemption is where the reasoning gets written down.
- **Conflicts with other plans:** none. No open plan touches `klartex/templates/*/schema.json` or `tests/test_schemas.py` (#96, #98, #99 are merged; the other plan folders belong to closed issues).

## Test Plan

- `tests/test_schemas.py::test_recipe_schemas_are_closed_at_every_object_level[<every discovered recipe>]` — every object node (including nullable `["object", "null"]` and `properties`-only nodes) in each loaded recipe schema has `additionalProperties: False`; discovered recipe names equal `RECIPE_SCHEMA_NAMES`.
- `tests/test_schemas.py::test_recipe_unknown_key_is_rejected[...]` — the typo shapes from the issue and a top-level unknown key per recipe fail with validator `additionalProperties`, the key in the message, the parent path in `absolute_path`.
- `tests/test_schemas.py::test_recipe_example_validates[<7 recipes>]` — every shipped `example.json` still validates.
- `tests/test_schemas.py::test_fixture_validates[<7 recipes>]` (existing) — every fixture still validates.
- `tests/test_server.py::test_recipe_unknown_key_is_a_validation_error_with_path` — `400 validation_error`, message names the key, `detail.path == ["agenda_items", 0]`.
- Full suite `pytest -q` (sequential) passes; xelatex render tests over the recipe fixtures are unchanged because no fixture changed.
- Manual: `klartex schema protokoll` (repo code) shows `"additionalProperties": false` at top level and on `agenda_items.items`; `klartex -t protokoll -d <fixture with subitems>` exits with the validation error naming `subitems`.

## Files Summary

- `klartex/templates/protokoll/schema.json` — `additionalProperties: false` on the top level and `agenda_items.items`.
- `klartex/templates/faktura/schema.json` — on the top level, `sender`, `recipient`, `lines.items`.
- `klartex/templates/kvitto/schema.json` — on the top level, `sender`, `items.items`.
- `klartex/templates/resultatrakning/schema.json`, `balansrakning/schema.json`, `budgetrapport/schema.json`, `sie-exportrapport/schema.json` — on the top level.
- `tests/test_schemas.py` — registry-driven closure test (plus the discovery-equals-tuple assertion), unknown-key rejection tests, `test_recipe_example_validates` over all seven.
- `tests/test_server.py` — one 400-contract test for an unknown recipe key.
- No change to `klartex/registry.py`, `klartex/server/render.py`, `README.md`, `CHANGELOG.md` (entry written at release from the PR body).
