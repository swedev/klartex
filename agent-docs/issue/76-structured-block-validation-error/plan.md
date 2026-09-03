# Plan: Issue #76 — Raise a structured exception with the block path from _validate_blocks

## Goal

Block-validation failures in `klartex.render()` are raised as a `BlockValidationError` — a `ValueError` subclass with a `path` attribute (`["body", 3]`, `["body", 2, "content", 0]`, and for schema failures the block position plus the wrapped `jsonschema.ValidationError`'s `absolute_path`, e.g. `["body", 0, "items", 1, 0, "text"]`) — with the three existing message texts unchanged, so a consumer can read the failing node from an attribute instead of parsing prose. `klartex serve` becomes the first consumer: its regex over the message goes and `detail.path` is read from the attribute. `swedev/klartex.se` migrates after the next release (out of scope here).

## Approach

### State verified before planning

- `klartex/renderer.py::_validate_blocks(blocks, path: str)` (line 293) builds the position as a string (`f"{path}[{i}]"`) and raises three plain `ValueError` forms: `Block at {where} is missing 'type'`, `Unknown block type '{t}' at {where}. Available: …`, and `Invalid '{t}' block at {where}: {e.message}` (the last `from e`, `e` a `jsonschema.ValidationError` validated against the *block* schema, so its `absolute_path` is relative to the block). It recurses through `_child_block_lists(block, where)` (line 268), which returns `(path_string, blocks)` pairs with the string forms `{path}.items[{i}].content`, `{path}.items[{i}]`, `{path}.content`. `_restore_block_types` (line 328) also calls `_child_block_lists(orig)` with the default path and ignores the returned path.
- `render()` calls `_validate_blocks(data.get("body", []), "body")` (line 187) only on the block-engine path, after the top-level `jsonschema.validate` and before `_preflight_font_files` and the `shutil.which("xelatex")` check — so the exception is reachable and testable without TeX (the existing `TestNestedBlockValidation` in `tests/test_block_engine.py` line 1145 already relies on this and carries no xelatex skip).
- The string form maps one-to-one onto a list: `["body", 0, "items", 1, 0]` renders as `body` + `[0]` + `.items` + `[1]` + `[0]` = `body[0].items[1][0]`, i.e. every `str` segment after the first is emitted as `.{seg}` and every `int` as `[{i}]`. The same rule reproduces `body[2].content[0]` and `body[0].items[0].content[0]`. So the list can be the source of truth and the current strings derived from it byte for byte — the message stays as it is, which is what the issue requires.
- `klartex/server/render.py` holds the consumer-side parser: `_BLOCK_POSITION`, `_BLOCK_ERROR_RE`, `_block_error_path(exc)` (lines 80–120), used in the `except ValueError` arm of `render()` to add `detail["path"]`. It appends `cause.absolute_path` when `__cause__` is a `ValidationError`, which is exactly the shape the issue asks the core to carry. `re` stays imported for `ASSET_NAME_RE`. CLAUDE.md (line 122, "HTTP surface") calls this parser a stopgap that goes when the core grows a structured exception.
- `tests/test_server.py` pins the three forms end to end (`test_render_validation_error_returns_structured_400`, `…_points_at_the_offending_block`, `…_reaches_into_the_block`, `…_covers_nested_blocks`, `test_render_unknown_block_type_carries_path`, `test_render_unknown_block_type_cannot_forge_a_path`, `test_render_block_with_empty_type_carries_path`) and one unit test on the parser itself, `test_block_error_path_returns_none_for_other_errors` (line 304), which references `render_module._block_error_path`. `test_render_unknown_template_returns_400` asserts that a non-block `ValueError` carries no `path`.
- `tests/test_block_engine.py` asserts on the messages with `pytest.raises(ValueError, match=…)` in ~30 places; all keep passing under a `ValueError` subclass with an unchanged message.
- `klartex/__init__.py` exports only `render`. No `errors` module exists; `ValueError` is raised directly from `renderer.py`, `page_templates.py` and `recipe.py` for every other input failure.
- README.md / README.en.md document the Python API with one snippet (`from klartex import render`) and the HTTP error contract (`detail.path`) in one paragraph each (line 119). Nothing documents Python-side exceptions today.
- `pyproject.toml` is at 0.19.0, released 2026-09-03. The CHANGELOG is written at release time by the release flow (CLAUDE.md, Releases), not in the PR.

### Provenance

- **User decision** (issue #76): a `ValueError` subclass named along the lines of `BlockValidationError`, with a `path` attribute in the `["body", 3]` / `["body", 2, "content", 0]` / block-position-plus-`absolute_path` shape; message text unchanged; `swedev/klartex.se` migrates after a release.
- **Existing convention** (CLAUDE.md, HTTP surface): the server's regex is a stopgap to be replaced by the structured exception when it exists — so replacing it is part of this issue, not a follow-up.
- **Agent judgment, open to question**: where the class lives (D1), building the path as a list and deriving the string (D2), the exception's attribute set (D3), what stays a plain `ValueError` (D4), README wording (D5). All bounded: nothing is stored or migrated, the message contract is unchanged, and each is a small in-repo edit to reverse.

### Design decisions

- **D1 — `BlockValidationError` is defined in `klartex/renderer.py` next to its raise site and re-exported from `klartex/__init__.py` (agent judgment).** Options: (a) a new `klartex/errors.py`; (b) in `renderer.py`, exported from the package root. Decision: (b). `klartex/__init__.py` gets `from klartex.renderer import BlockValidationError, render` and `__all__ = ["BlockValidationError", "render"]`; the server imports it from `klartex`. Consequence if wrong: a one-file move; the public import path `from klartex import BlockValidationError` stays whichever way. Rationale: it is the only structured exception in the package and every other input error is a bare `ValueError` raised where it occurs — an `errors` module for one class is premature. What would make (a) right: a second structured exception (e.g. for page-template failures).
- **D2 — The path is threaded through `_validate_blocks` and `_child_block_lists` as a list, and the message string is rendered from it by a `_format_block_path(path)` helper (agent judgment).** Options: (a) keep the string path and parse it back into a list at the raise site; (b) carry `list[str | int]` and format the string. Decision: (b). `_child_block_lists(block, path=())` returns `(list_path, blocks)` pairs built as `[*path, "items", i, "content"]`, `[*path, "items", i]`, `[*path, "content"]`; `_validate_blocks(blocks, path)` computes `where = [*path, i]` and `where_text = _format_block_path(where)`; `render()` passes `["body"]`. `_restore_block_types` keeps calling `_child_block_lists(orig)` and ignoring the path. Consequence if wrong: a string-parsing `_block_error_path` reappears inside the core — the same function the server has today. Rationale: parsing what one just formatted is the bug class the issue exists to remove (an unknown block type may contain `at body[9]`, which the server needs a forgery test for today); the formatter is the single place where the message wording is defined, and the goldens in `tests/test_block_engine.py` lock it byte for byte.
- **D3 — The exception carries `path` and the message; nothing else (agent judgment).** Options: also `block_type`, `block`, or a structured `reason`. Decision: `path` only, plus `__cause__` as today for the schema form. Signature: `BlockValidationError(message: str, path: list[str | int])`, calling `super().__init__(message)` so `str(exc)` and `pytest.raises(match=…)` behave as for a `ValueError`; `path` is stored as a plain `list` (the `absolute_path` deque converted with `list(...)`) so it JSON-serialises directly. Consequence if wrong: a follow-up adds an attribute — additive, no consumer breaks. Rationale: the issue names `path`; the consumer's contract (`detail.path`) needs only that; every extra attribute is a promise to keep.
- **D4 — Only the three `_validate_blocks` forms become `BlockValidationError`; every other `ValueError` in `render()` stays as it is (agent judgment).** Options: also wrap the top-level `jsonschema.ValidationError` (it already carries `absolute_path` and is caught separately by the server), the unknown-template error, `asset_dir` and font preflight errors. Decision: no — the issue is about block validation, and `test_render_unknown_template_returns_400` pins that a plain `ValueError` carries no `path`. Consequence if wrong: another issue for another exception; nothing here would need undoing.
- **D5 — Document the exception in one sentence under "Som Python-bibliotek" / "As a Python library" in both READMEs (agent judgment).** Options: nothing (the docstring suffices); a sentence in the README; a full exceptions section. Decision: one sentence, in both languages, stating that block-validation failures raise `klartex.BlockValidationError` (a `ValueError`) whose `path` lists the failing node in the same shape as the HTTP API's `detail.path`. Consequence if wrong: a documentation edit. Rationale: the class is the Python API's only structured error and the README is where the Python API is introduced; the HTTP paragraph already documents the same `path` shape, so the two lines cross-reference.

### Out of scope

- The `swedev/klartex.se` pin bump and removal of its `_block_error_path` — happens in that repo after the next klartex release.
- A release. The CHANGELOG entry is written at release time by the release flow.
- Structured exceptions for non-block failures (D4).

## Steps

1. **Core exception and list-shaped path** — `klartex/renderer.py`:
   - Add `class BlockValidationError(ValueError)` with `__init__(self, message: str, path: list[str | int])`, storing `self.path = list(path)` and calling `super().__init__(message)`. Docstring: raised by block validation on the block-engine path; `path` addresses the failing node in the submitted data (`["body", 1]` the block, `["body", 0, "items", 1, 0, "text"]` a field inside a nested block); the message is the human-readable form of the same position.
   - Add `_format_block_path(path: Sequence[str | int]) -> str` (`collections.abc.Sequence`): first segment verbatim, then `.{seg}` for `str` and `[{i}]` for `int`.
   - Change `_child_block_lists(block: dict, path: Sequence[str | int] = ()) -> list[tuple[list[str | int], list]]` to build list paths (`[*path, "items", i, "content"]`, `[*path, "items", i]`, `[*path, "content"]`); the read-only `Sequence` input type is what makes the empty-tuple default and the constructed lists both valid. Keep the docstring's "single source of truth for nesting" point.
   - Change `_validate_blocks(blocks: list, path: Sequence[str | int])`: `where = [*path, i]`, `where_text = _format_block_path(where)`; raise `BlockValidationError(f"Block at {where_text} is missing 'type'", where)`, `BlockValidationError(f"Unknown block type '{block_type}' at {where_text}. Available: {available}", where)`, and for the schema form `BlockValidationError(f"Invalid '{block_type}' block at {where_text}: {e.message}", [*where, *e.absolute_path]) from e`. Update the docstring's path example to the list form.
   - `render()` passes `["body"]` instead of `"body"`.
2. **Package export** — `klartex/__init__.py`: import and export `BlockValidationError` alongside `render`.
3. **Server reads the attribute** — `klartex/server/render.py`:
   - Delete `_BLOCK_POSITION`, `_BLOCK_ERROR_RE` and `_block_error_path` (and their comments). `re` stays for `ASSET_NAME_RE`.
   - Import `BlockValidationError` from `klartex`. In `render()`, add `except BlockValidationError as e:` before `except ValueError as e:` that raises the 400 with `{"type": "input_error", "message": str(e), "path": e.path}`; the `ValueError` arm no longer adds a path.
   - Rewrite the module docstring's paragraph on `detail.path` so it says both shapes come from the core (`ValidationError.absolute_path` and `BlockValidationError.path`) — no mention of parsing.
4. **Core tests** — `tests/test_block_engine.py`, in `TestNestedBlockValidation` (or a sibling class `TestBlockValidationError`):
   - Missing `type` (`{"type": ""}` at `body[1]`, after a valid block, since a block without the key is stopped by the top-level schema first): `pytest.raises(BlockValidationError)` with `exc.path == ["body", 1]` and message `Block at body[1] is missing 'type'`.
   - Unknown type at `body[0]`: `path == ["body", 0]`; and the forged-type case `"x' at body[9]. Available: y"` still gives `["body", 0]`.
   - Schema failure with a field path: `{"type": "heading", "text": 123}` gives `["body", 0, "text"]`; a required-field failure gives the bare block position `["body", 0]`.
   - Nested carriers: `clause.content` → `["body", 0, "content", 0]`, `list.items[].content` → `["body", 0, "items", 0, "content", 0]`, `columns.items[][]` → `["body", 0, "items", 1, 0]` and with a field failure `["body", 0, "items", 1, 0, "text"]`.
   - Each asserts the message with the exact string form beside the path, so the formatter is pinned (`str(exc)` contains `at body[0].items[1][0]`).
   - One test per message form asserts full equality, `str(exc.value) == expected` — for the unknown-type form with the complete `Available: ` suffix built from `", ".join(sorted(KNOWN_BLOCK_TYPES))`, for the schema form with the `jsonschema` `e.message` taken from the cause. `match=` is a regex search and the server tests check fragments, so this is the only byte-exact pin on the wording klartex.se still parses.
   - `isinstance(exc, ValueError)` and `exc.__cause__` is a `jsonschema.ValidationError` for the schema form.
   - The tests import `BlockValidationError` from `klartex`, not `klartex.renderer`, so the package-root export is covered by CI.
   - Switch the four existing `TestNestedBlockValidation` tests to `pytest.raises(BlockValidationError, match=…)`; leave the other `pytest.raises(ValueError, match="Invalid … block")` sites as they are — they document that the subclass relationship holds.
   - A `_format_block_path` unit test: `["body"]` → `body`, `["body", 0, "items", 1, 0]` → `body[0].items[1][0]`, `["body", 2, "content", 0]` → `body[2].content[0]`.
5. **Server tests** — `tests/test_server.py`:
   - Replace `test_block_error_path_returns_none_for_other_errors` (the function is gone) with a behavioural negative test: monkeypatch `render_module.klartex_render` to raise a plain `ValueError("Block at body[9] is missing 'type'")` — text that looks exactly like a block error — and assert the 400 `input_error` carries no `path`. That pins dispatch by exception type, which the unknown-template test alone does not.
   - Update the docstrings of `test_render_validation_error_returns_structured_400` and `test_render_block_with_empty_type_carries_path` so they describe `BlockValidationError.path` rather than message recovery. Keep `test_render_unknown_block_type_cannot_forge_a_path` — it now guards that the attribute, not the message, is the source. All path assertions stay unchanged; they are the contract.
6. **Docs** — `CLAUDE.md`: replace the "Block-path extraction … stopgap" paragraph with one sentence stating that `render.py` reads `detail.path` from `BlockValidationError.path` (block failures) and `ValidationError.absolute_path` (schema failures). `README.md` / `README.en.md`: the D5 sentence under the Python-library heading.
7. Run `pytest -n auto` with the `dev` and `serve` extras installed and xelatex on PATH — that is the CI-equivalent run; CI fails on any skipped xelatex or `test_server` test, so a local run without either is only the targeted no-TeX iteration in the Test Plan, not the gate. Confirm no reference to `_block_error_path`, `_BLOCK_ERROR_RE` or `_BLOCK_POSITION` remains (`grep -rn "_block_error_path\|_BLOCK_ERROR_RE\|_BLOCK_POSITION" klartex tests CLAUDE.md`).

## Files Summary

- `klartex/renderer.py` — `BlockValidationError`, `_format_block_path`, list paths in `_child_block_lists` / `_validate_blocks`, `render()` call site.
- `klartex/__init__.py` — export.
- `klartex/server/render.py` — regex parser removed, `except BlockValidationError` arm, docstring.
- `tests/test_block_engine.py` — path and formatter tests; existing nested tests narrowed to the subclass.
- `tests/test_server.py` — one test removed, two docstrings updated.
- `CLAUDE.md`, `README.md`, `README.en.md` — documentation of the new source of `path`.

No other open plan touches these files (all other `agent-docs/issue/*` folders belong to closed issues). Open issue #44 (xelatex-missing error message) also edits `renderer.py` but a different function, and has no plan.

## Risks

- **Message drift.** Any deviation in `_format_block_path` from today's string form changes the message and breaks the klartex.se regex before it migrates. Mitigated by the full-equality assertions in step 4 (one per form) and the unchanged server tests in step 5, which assert `"body[1]" in detail["message"]`.
- **Path for a required-field schema failure.** `absolute_path` is empty when `required` fails, so the path is the bare block position — same as today's server behaviour (`test_render_validation_error_returns_structured_400` asserts `["body", 0]`). Not a change, but worth a test so nobody "fixes" it to point at the missing key.
- **Consumers catching `ValueError` and reading `.path` defensively.** None in this repo; klartex.se uses `getattr`-free regex until it migrates and is unaffected.
- **`_restore_block_types` and `_child_block_lists` signature.** The restore walk passes no path; the default must stay a valid empty sequence, and a tuple default (`()`) avoids a shared mutable list.

## Test Plan

- `pytest tests/test_block_engine.py -k "BlockValidation or NestedBlockValidation or format_block_path"` — no xelatex required: validation raises before the TeX check.
- `pytest tests/test_server.py -k "path or block_error"` with the `serve` extra installed — every `detail["path"]` assertion passes unchanged; `test_render_unknown_template_returns_400` still sees no `path`.
- `pytest -n auto` with `.[dev,serve]` and xelatex installed — the CI gate; the ~30 `pytest.raises(ValueError, match="Invalid …")` sites stay green, proving the subclass relationship.
- The package-root import is exercised by the step-4 tests (`from klartex import BlockValidationError`); the monkeypatched plain-`ValueError` test in step 5 proves the server dispatches on type, not on prose.
- `grep -rn "_block_error_path\|_BLOCK_ERROR_RE\|_BLOCK_POSITION" klartex tests CLAUDE.md` returns nothing.
