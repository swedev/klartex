# Progress: Issue #78 — Recipe schemas accept unknown keys silently — decide on `additionalProperties: false` recipe-wide

## Status: Completed

Completed: 2026-09-03 on branch `issue/78-recipe-schemas-additional-properties` (from `main`).

(Update as work proceeds — newest entries first)

- 2026-09-03: Verification. `pytest -q` sequential: 821 passed, 9 skipped (the nine local font-availability skips; no `serve` skips). Baseline in the plan was 794 passed, 9 skipped. `klartex schema protokoll` reports `False False` for the top level and `agenda_items.items`. A protokoll fixture with `subitems` fails the CLI with `Additional properties are not allowed ('subitems' was unexpected)` and writes no PDF.
- 2026-09-03: Step 6 — `tests/test_server.py::test_render_recipe_unknown_key_reports_the_key_and_its_object`: a protokoll payload with `subitems` gets 400, `detail.type == "validation_error"`, the key in `detail.message`, `detail.path == ["agenda_items", 0]`.
- 2026-09-03: Steps 3–5 — `tests/test_schemas.py`: `_object_nodes()` walker plus registry-driven `test_recipe_schemas_are_closed_at_every_object_level`; `test_recipe_unknown_key_is_rejected` over the five typo shapes and a top-level unknown key on each of the seven recipes; `test_discover_all_templates` now asserts discovery equals `RECIPE_SCHEMA_NAMES`; `test_recipe_example_validates` and `test_fixture_validates` both parametrize over that tuple, which moved above its first use.
- 2026-09-03: Step 2 — `"additionalProperties": false` added to the 13 open object levels. A walk of the loaded registry schemas confirmed 13 open nodes before and 0 after, matching the plan's table exactly.
- 2026-09-03: Step 1 — read `tests/test_schemas.py` and the 400-contract tests in `tests/test_server.py`. `get_registry` is imported from `klartex.renderer`; `test_server.py` uses a module-level `client`, as the plan noted.
- 2026-09-03: Branch `issue/78-recipe-schemas-additional-properties` created from `main`.
