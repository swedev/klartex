# Progress: Issue #109 — Public klartex.validate(): schema and block validation without rendering

## Status: Completed

Completed 2026-09-03 on branch `issue/109-public-validate-without-rendering` (from `main`).

## Steps

- [x] 1. `validate(template_name, data) -> None` added to `klartex/renderer.py`, above `render()`, with the registry lookup, `jsonschema.validate` against the validation schema and the block-engine `_validate_blocks` call lifted verbatim. Docstring states the checks, the raised exceptions, that no TeX toolchain is touched, and the page-template/font-preflight boundary.
- [x] 2. `render()` calls `validate(template_name, data)` first, then re-reads `template_info` from the cached registry.
- [x] 3. `klartex/__init__.py` exports `validate`; `__all__` is `["BlockValidationError", "render", "validate"]`.
- [x] 4-7. `TestValidate` in `tests/test_renderer.py`: export check, fixture parametrisation with `shutil.which` and `subprocess.run` monkeypatched, unknown template, recipe schema violation, block base-schema violation, block payload failure (path + `__cause__`), nested unknown block type, and the render-delegates lock.
- [x] 8. `klartex validate` subcommand on handler `validate_command`, with `from klartex.renderer import ... validate as validate_data`; `_load_data(data)` helper shared with `main` owns file/stdin reading and JSON parsing.
- [x] 9. `tests/test_cli_validate.py` — 9 cases; `tests/test_cli_errors.py` unchanged and passing.
- [x] 10-11. `README.md`, `README.en.md` library + CLI sections; `CLAUDE.md` pipeline note.

## Deviations

- The plan's fixture list named `avtal.json` → `avtal`, but there is no `avtal` recipe template in `klartex/templates/`; the fixture is an unused leftover. The parametrisation covers `avtal_block.json` against `_block` (as planned) and the seven recipe templates that exist. Block fixtures are globbed rather than listed, so a new `block_*.json` is covered automatically.

## Verification

- `pytest -n auto`: 874 passed, 9 skipped (all pre-existing local missing-font skips).
- `klartex validate -d tests/fixtures/block_kallelse.json` → exit 0, silent.
- `{"body":[{"type":"nope"}]}` → `Error: Unknown block type 'nope' at body[0]. Available: …`, exit 1.
- `klartex.validate("_block", …)` returns `None` with `shutil.which` stubbed to `None`.
