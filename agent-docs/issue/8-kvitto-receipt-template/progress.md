# Progress: Issue #8 — Template: kvitto (receipt)

## Status: Completed (2026-07-06)

(Update as work proceeds — newest entries first)

- 2026-07-06: All steps implemented and verified. Full suite 237 passed (6 new tests).
  Rendered fixture and minimal payload via CLI; visual check OK (header, items,
  prominent total, metadata list, note). `klartex templates`/`schema kvitto`/
  `example kvitto` all work.

- [x] 1. templates/kvitto/schema.json
- [x] 2. templates/kvitto/recipe.yaml
- [x] 3. components.py: receipt_header + receipt_table specs
- [x] 4. _recipe_base.tex.jinja: new arms + description_list guard
- [x] 5. templates/kvitto/example.json
- [x] 6. tests/fixtures/kvitto.json
- [x] 7. Test updates (test_schemas, test_renderer, test_components, focused tests)
- [x] 8. README.md + README.en.md
