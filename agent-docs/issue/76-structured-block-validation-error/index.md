# Issue #76: Raise a structured exception with the block path from _validate_blocks

**Branch from:** main

## Summary

`_validate_blocks` raises `BlockValidationError(ValueError)` with a `path` attribute — `["body", 3]`, `["body", 2, "content", 0]`, and for schema failures the block position plus the wrapped `jsonschema.ValidationError`'s `absolute_path` — while the three message texts stay byte-identical. The path is carried as a list through `_child_block_lists` / `_validate_blocks` and the message string is formatted from it. `klartex serve` drops its message-parsing regex and reads `detail.path` from the attribute; the class is exported from `klartex`. `swedev/klartex.se` migrates after the next release.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Low |
| **Blocked by** | None |
| **Related** | swedev/klartex.se#26 (closed) and PR swedev/klartex.se#61 (merged) — the consumer whose regex migrates to `path` after the next klartex release; downstream rollout, not a blocker. #44 (open, no plan) also edits `renderer.py` but a different function — coordination risk, not a dependency |

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-09-03
**Feedback:** Codex confirmed the architecture and order; applied its refinements — full-equality message assertions per form (`match=` is only a search), a monkeypatched plain-`ValueError` server test proving dispatch by type instead of the deleted parser unit test, the `klartex` package-root import in tests, `Sequence[str | int]` signatures for the path helpers, and explicit CI-gate requirements (`dev`+`serve` extras, xelatex).

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress log
