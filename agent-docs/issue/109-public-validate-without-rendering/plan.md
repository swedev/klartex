# Plan: Issue #109 — Public klartex.validate(): schema and block validation without rendering

## Goal

Give library consumers a public entry point, `klartex.validate(template_name, data)`, that runs exactly the validation `render()` runs — the JSON-Schema check against the template's validation schema, then the recursive per-block check on the block-engine path — raises the same exceptions (`ValueError` for an unknown template, `jsonschema.ValidationError`, `BlockValidationError` with `path`), returns `None`, and never touches the TeX toolchain. `render()` delegates to the same function so the two cannot drift. Secondary: a `klartex validate` CLI subcommand with the same semantics.

The concrete consumer is a document store (styrla/styrla#46) that wants to reject a broken payload at upload, before anyone reads it, using the same rules as the render service. Styrla can only consume the API once a klartex release carrying it is published — a rollout dependency for the consumer, not a blocker for this issue.

## Approach

Extract the validation prefix of `render()` (`klartex/renderer.py`, the registry lookup + `jsonschema.validate` + `_validate_blocks`) into a new public function `validate()` in the same module, and make `render()` call it as its first statement. Nothing about what is validated changes; the only observable difference is that the checks are reachable without a compile.

Boundaries kept deliberately narrow, matching the issue text ("exactly the validation `render()` runs (schema, then per-block)"):

- `_preflight_font_files()` stays in `render()`. It inspects the filesystem for external font files under `asset_dir` — a render-time precondition, not payload validation, and `validate()` takes no `asset_dir`.
- Errors that `load_page_template()` raises while composing chrome stay where they are: they happen after escaping, on the template-render step, not in the validation step. Concretely: a `margins.top` at or below the header band when a predefined header carries content, a `letterhead` whose `org_name` is present but empty (the generated schema requires the key, `_slot_schema()` in `klartex/page_templates.py`, but only the loader rejects an empty string), and combining a whole-page source with slot sources. A payload that passes `validate()` can still fail there; documented in the docstring and README as the boundary, and left as a possible follow-up rather than widened here.
- Signature is `validate(template_name: str, data: dict) -> None`. No `header_source`/`footer_source`/`page_template_source` — those are not validated by `render()` either.

The exported error contract is unchanged: `__all__` grows by `validate`; `BlockValidationError` and `jsonschema.ValidationError` keep their current shapes, so `klartex/server/render.py` needs no change (it maps the same exceptions from `render()`).

## Steps

### Phase 1 — Core: `validate()` in `klartex/renderer.py`

1. Add `def validate(template_name: str, data: dict) -> None` directly above `render()`. Body, in this order, lifted verbatim from `render()`:
   1. `registry = get_registry()`; unknown name → the same `ValueError("Unknown template '…'. Available: …")` that `render()` raises today.
   2. `jsonschema.validate(data, template_info.get_validation_schema())` — the base schema without the blocks' `oneOf`, so messages stay readable (existing comment moves with it).
   3. `if template_info.is_block_engine: _validate_blocks(data.get("body", []), ["body"])`.
   Docstring states: what is checked, what is raised, that it never runs xelatex, and that page-template composition errors (`margins.top` vs the header band, an empty `letterhead.org_name`, source combination) are render-time and not covered.
2. Replace the corresponding lines at the top of `render()` with `validate(template_name, data)`, then keep `template_info = get_registry()[template_name]` for the branch below (the lookup is cheap; the registry is cached). `_preflight_font_files`, escaping, restore, and compile follow unchanged.
3. Export: `klartex/__init__.py` imports and lists `validate` in `__all__` (alphabetical with the existing two).

### Phase 2 — Tests (`tests/test_renderer.py`, no xelatex needed)

4. `test_validate_is_exported`: `from klartex import validate`; `"validate" in klartex.__all__`.
5. `test_validate_passes_fixtures_without_xelatex`: parametrised over explicit (template, fixture) pairs — every `tests/fixtures/block_*.json` plus `avtal_block.json` with `_block`, and each recipe fixture with its own name (`protokoll.json` → `protokoll`, `faktura.json` → `faktura`, `avtal.json` → `avtal`, `balansrakning.json`, `resultatrakning.json`, `budgetrapport.json`, `kvitto.json`, `sie-exportrapport.json`). There is no general inference helper in the suite, so list the pairs. `validate(...)` returns `None` with `shutil.which` monkeypatched to return `None` and `subprocess.run` monkeypatched to `pytest.fail` — proves no toolchain involvement.
6. `test_validate_raises_same_errors_as_render`, four cases:
   - unknown template → `ValueError` whose message carries the `Available:` list;
   - schema violation → `jsonschema.ValidationError`: `protokoll` payload missing one of its required keys (`meeting_type`, `date`, `attendees`, `agenda_items` — see `klartex/templates/protokoll/schema.json`), and `_block` with `body` not a list;
   - a known block whose payload fails its component schema, e.g. `{"body": [{"type": "heading", "text": 123}]}` → `BlockValidationError` with `path == ["body", 0, "text"]` and `__cause__` a `jsonschema.ValidationError` — proves per-block schema validation, not only type checking;
   - unknown block type nested in a `list` item → `BlockValidationError` with the same `path` render() reports (reuse the assertions from `TestBlockValidationError` in `tests/test_block_engine.py`).
7. `test_render_delegates_to_validate`: monkeypatch `klartex.renderer.validate` to raise a sentinel exception and assert `render()` propagates it before `_compile_tex`/`subprocess.run` is reached (spy on `subprocess.run` and assert it was never called). This is the lock on "render() calls validate(), so the two cannot diverge".

### Phase 3 — CLI: `klartex validate` (`klartex/cli.py`)

8. Add `@app.command("validate")` on a handler named `validate_command`, with the renderer function imported as `from klartex.renderer import validate as validate_data` — the handler and the imported function must not share a name, or the handler shadows (or recurses into) the import. Options: `--data/-d` (file, or stdin when omitted) and `--template/-t` (default `_block`). Factor the file/stdin reading **and** the JSON parsing of `main` into one helper, `_load_data(data: Optional[Path]) -> dict`, that applies the existing rules (missing file, non-file path, tty without a pipe, invalid JSON → `Error: …` on stderr, exit 1) and is used by both `main` and the new command, so neither re-implements them. The command calls `validate_data(template, payload)`, prints nothing on success and exits 0; on `ValueError`, `jsonschema.ValidationError` or `BlockValidationError` it prints `Error: <message>` to stderr and exits 1, mirroring `main`'s error shape.
9. Tests in a new `tests/test_cli_validate.py` (typer `CliRunner` and the `_all_output()` stderr pattern from `tests/test_cli_errors.py`; `tests/test_agent_cli.py` covers discovery commands, not `CliRunner` flows): valid fixture → exit 0, empty stdout; invalid block → exit 1, output contains the block path text; unknown template → exit 1; malformed JSON → exit 1 with `invalid JSON`; stdin path works. `tests/test_cli_errors.py` keeps passing unchanged after the `_load_data` refactor.

### Phase 4 — Documentation

10. `README.md` and `README.en.md` (the English mirror has the same library and CLI sections), "Som Python-bibliotek" / library section: add `validate` to the import line and a short paragraph — validates without running XeLaTeX, same errors as `render()`, `render()` calls the same function; note that page-template composition (e.g. `margins.top` against the header band) can still fail at render time, and that `jsonschema.ValidationError` is imported from `jsonschema`. CLI section: add `klartex validate -d data.json` (and `-t protokoll`) to the example block. Swedish in `README.md`, English in `README.en.md`.
11. `CLAUDE.md`, "Rendering pipeline": one line noting that the first two pipeline steps are `validate()`, public and reused by `render()`. Keep it a nu-state description.
12. No `CHANGELOG.md` entry in the PR — entries are written by the release commit (see the repo's release procedure); the PR body carries the user-facing summary.

## Risks

- **Drift between `validate()` and `render()`** is the failure mode the issue exists to prevent. Mitigated structurally (render() calls validate(), locked by step 7) rather than by duplicated code.
- **Consumers may read "validated" as "will render".** Page-template composition errors and font-file preflight are not covered. Mitigated by stating the boundary in the docstring and README; a follow-up could pull `load_page_template()`'s checks forward if the consumer needs them.
- **CLI option collision.** The root callback already owns `-d`/`-t`; typer keeps callback options separate from subcommand options, so `klartex validate -d x.json` is fine, but `klartex -d x.json validate` would pass `-d` to the root callback, which returns early when a subcommand is invoked. Test the documented form only.
- **`_load_data` refactor touches the render path.** The existing `tests/test_cli_errors.py` cases are the regression guard; run them before and after.
- **Exception import surface.** `jsonschema.ValidationError` is not re-exported by klartex; consumers import it from `jsonschema` (already a hard dependency). Documented in the README paragraph; re-exporting would be a separate decision.

## Test Plan

- `pytest tests/test_renderer.py tests/test_cli_validate.py tests/test_cli_errors.py -k "validate or cli"` — new tests plus the CLI regression guard, no TeX Live required.
- `pytest -n auto` — full suite unchanged in behaviour; the render fixtures still compile, and `tests/test_server.py` passes untouched (server exception mapping is unchanged).
- Manual: `klartex validate -d tests/fixtures/block_kallelse.json` exits 0 silently; feed a payload with `{"type": "nope"}` in `body` and confirm `Error: Unknown block type 'nope' at body[0]. Available: …` on stderr, exit 1.
- Library check from a shell with `xelatex` absent from PATH: `python -c "import klartex, json; klartex.validate('_block', json.load(open('tests/fixtures/block_kallelse.json')))"` succeeds.

## Design Decisions

### 1. Where `validate()` lives
- **Options:** (a) `klartex/renderer.py`, next to `render()`; (b) a new `klartex/validation.py` that `renderer.py` imports.
- **Decision:** (a).
- **Provenance:** agent judgment.
- **Consequence if wrong:** bounded — a module move is a mechanical follow-up.
- **Rationale:** `_validate_blocks`, `_child_block_lists` and `BlockValidationError` already live in `renderer.py` and `_restore_block_types` shares `_child_block_lists`; splitting the module is a larger refactor than the issue asks for. A new module becomes right if `renderer.py` keeps growing or if the server wants to import validation without importing the compile machinery.

### 2. What `validate()` covers
- **Options:** (a) exactly the schema + per-block checks `render()` runs; (b) also the `load_page_template()` checks; (c) also `_preflight_font_files`.
- **Decision:** (a).
- **Provenance:** user decision — the issue states "runs exactly the validation `render()` runs (schema, then per-block for the block engine)" and "never touches the TeX toolchain".
- **Consequence if wrong:** bounded — widening later is additive and does not change the error contract for what (a) already rejects.
- **Rationale:** (c) needs an `asset_dir` and the filesystem; (b) runs after escaping today and would need to be lifted out of `_render_*` first. Both are named as the boundary in the docs so a consumer is not surprised.

### 3. Signature
- **Options:** (a) `validate(template_name, data) -> None`; (b) return a result object / list of errors.
- **Decision:** (a), raising on the first failure.
- **Provenance:** user decision — the issue specifies "returns nothing" and "raises the same errors".
- **Consequence if wrong:** bounded.
- **Rationale:** identical to what `render()` does today, so the consumer's error handling is the same code path as against the service.

### 4. `render()` delegates to `validate()`
- **Options:** (a) `render()` calls `validate()`; (b) both call a private helper.
- **Decision:** (a).
- **Provenance:** user decision — "`render()` calls it, so the two cannot diverge".
- **Consequence if wrong:** bounded.
- **Rationale:** the public function is the single definition; a private helper adds an indirection with no gain.

### 5. Include the CLI subcommand in this PR
- **Options:** (a) ship `klartex validate` now; (b) library only, CLI as a follow-up issue.
- **Decision:** (a), as its own phase after the library work.
- **Provenance:** agent judgment (the issue calls the CLI "secondary", not "out of scope").
- **Consequence if wrong:** bounded — the subcommand is a thin wrapper that can be dropped or split into its own PR in review.
- **Rationale:** it is ~30 lines on top of the function and gives a way to check the boundary manually without writing Python. Splitting it out becomes right if the reviewer wants the library change merged first for the consumer.

### 6. Keep `jsonschema.ValidationError` un-re-exported
- **Options:** (a) consumers import it from `jsonschema`; (b) re-export as `klartex.ValidationError`.
- **Decision:** (a).
- **Provenance:** existing convention — `__all__` exports only `render` and `BlockValidationError` today and the server imports `ValidationError` from `jsonschema` (`klartex/server/render.py`).
- **Consequence if wrong:** bounded — a re-export is additive.
- **Rationale:** stays closest to the issue's wording, which names `jsonschema.ValidationError` as the raised type.

## Files Summary

- `klartex/renderer.py` — new `validate()`; `render()` calls it.
- `klartex/__init__.py` — export `validate`.
- `klartex/cli.py` — `validate` subcommand (`validate_command`), `_load_data` helper shared with `main`.
- `tests/test_renderer.py` — validate tests, render-delegates lock.
- `tests/test_cli_validate.py` — new; CLI subcommand tests.
- `README.md`, `README.en.md`, `CLAUDE.md` — library and CLI usage, pipeline note.

No active PR touches the validation prefix of `render()`; the most recent change there (#76, PR #108) is merged. Open issue #44 may later touch `renderer.py` in the compile-error section, which this plan does not change. Issue label: `enhancement`.
