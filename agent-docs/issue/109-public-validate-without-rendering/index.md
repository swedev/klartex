# Issue #109: Public klartex.validate(): schema and block validation without rendering

**Branch from:** main

## Summary

Extract the validation prefix of `render()` (schema check, then per-block check on the block engine) into a public `klartex.validate(template_name, data)` that raises the same errors and never runs XeLaTeX; `render()` delegates to it. Adds a `klartex validate` CLI subcommand and documents the library use. Lets a document store reject a broken payload at upload with the rules the render service applies.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Low |

No blockers, no parent issue, no related open issues in this repo; downstream consumer styrla/styrla#46 waits for a release carrying the API (rollout dependency, not a blocker). No active PR touches the validation prefix of `render()`. Label: `enhancement`.

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-09-03
**Feedback:** Codex review applied: CLI handler must not shadow the imported `validate`; the schema-violation and page-template-boundary examples were wrong (`protokoll` has no `title`; the uncovered letterhead case is an empty `org_name`, not a missing one); added a direct block-schema failure test, a malformed-JSON CLI test in a new `tests/test_cli_validate.py`, explicit fixture/template pairs, `README.en.md`, and a shared `_load_data` helper.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress log (created when work starts)
