# Issue #78: Recipe schemas accept unknown keys silently — decide on `additionalProperties: false` recipe-wide

**Branch from:** main

## Summary

Decides the open question in favour of closing the recipe contracts: `additionalProperties: false` goes on the 13 object levels that are still open across the seven recipe schemas (top level of every recipe; `protokoll` `agenda_items[]`; `faktura` `sender`, `recipient`, `lines[]`; `kvitto` `sender`, `items[]`), so a producer's typo is rejected with a `validation_error` naming the key instead of rendering as if the field were omitted — the convention the block engine's closed block schemas already set. A recipe-wide test walks every loaded recipe schema (injected `page_template` subtree included) and asserts the closure; rejection tests lock the message/path shape and one `klartex serve` test locks the 400 contract. All shipped examples, fixtures and the full suite already pass against the closed schemas, so no payload changes. Breaking, no shim; klartex.se's `llms.txt` examples and, where available, its generated requests are validated against the closed schemas before the release that ships it.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Medium (implementation Low; rollout Medium — breaking change to a published contract) |
| **Blocked by** | None (#79, the sequencing prerequisite, is merged) |
| **Related** | #70 (origin, closed), #79 (prerequisite, closed), #99 (adjacent schema edits, closed) |

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-09-03
**Feedback:** Codex corrected the open-node count to 13, made the guard test registry-driven (a new recipe cannot escape a hard-coded tuple) and widened its object-node definition to nullable `["object", "null"]` and `properties`-only nodes; narrowed the block-engine consistency claim to block objects (nested block objects are not all closed); raised rollout risk to Medium with a concrete klartex.se pre-release check (payloads and generated requests, `jsonschema.validate`, zero errors); fixed the server-test instructions (module-level `client`, literal payload) and the `footer` reasoning (declared property, not evaluation order).

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress log
