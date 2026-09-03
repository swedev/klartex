# Progress: Issue #76 — Raise a structured exception with the block path from _validate_blocks

## Status: Completed

Completed: 2026-09-03

(Update as work proceeds — newest entries first)

- Verification: `pytest -n auto` → 836 passed, 9 skipped (all nine are the OS-font availability skips in `tests/test_renderer.py`; no xelatex or `test_server` skips). Targeted runs: `tests/test_block_engine.py -k "BlockValidation or NestedBlockValidation or FormatBlockPath"` (20 passed) and `tests/test_server.py` (76 passed).
- Step 6: `CLAUDE.md` HTTP-surface paragraph rewritten to name the two core sources of `detail.path`; one sentence on `klartex.BlockValidationError` added under the Python-library heading in `README.md` and `README.en.md`.
- Step 5: `tests/test_server.py` — `test_block_error_path_returns_none_for_other_errors` replaced by `test_plain_value_error_carries_no_path`, which monkeypatches `klartex_render` to raise a plain `ValueError` whose text mimics a block error and asserts no `path`; two docstrings updated. All path assertions unchanged.
- Step 4: `tests/test_block_engine.py` — `TestBlockValidationError` (path and full-message assertions per form, forged-type case, nested carriers, `required` case, `isinstance` and `__cause__`) and `TestFormatBlockPath`; the four `TestNestedBlockValidation` tests narrowed to `BlockValidationError` and importing from the package root.
- Step 3: `klartex/server/render.py` — `_BLOCK_POSITION`, `_BLOCK_ERROR_RE` and `_block_error_path` removed; `except BlockValidationError` arm added ahead of `except ValueError`; module docstring updated.
- Step 2: `klartex/__init__.py` exports `BlockValidationError`.
- Step 1: `klartex/renderer.py` — `BlockValidationError(ValueError)` with `path`, `_format_block_path`, list-shaped paths through `_child_block_lists` / `_validate_blocks`, `render()` passing `["body"]`.
- Branch `issue/76-structured-block-validation-error` created from `main`.
