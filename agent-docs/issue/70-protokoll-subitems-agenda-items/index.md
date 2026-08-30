# Issue #70: Protokoll recipe: `subItems` on `agenda_items[]` is accepted and rendered but undocumented

**Branch from:** main

## Summary

Documents `subItems` on `agenda_items[]` in `klartex/templates/protokoll/schema.json` (array of strings, Swedish description with the #60 inline-markup wording plus the two rendering facts: decimal sub-numbering under the parent, placed after discussion and decision), puts the field into the protokoll example/fixture, and locks the behaviour with a tex-level test through `_render_recipe_tex("protokoll", …)` (decimal sub-numbering, inline filter, placement after the parent's decision), a schema-contract test that also validates `example.json`, and a negative test that non-array / non-string `subItems` are rejected. No change to the macro, recipe or Python: the shared `render_agenda` already renders the field in the `decimal` style the recipe pins, verified at tex level before planning. Documenting rather than rejecting is an agent judgment, flagged open: every recipe item array is open today (faktura `lines[]`, kvitto `items[]`, protokoll top level), so tightening one array would be inconsistent and breaking; the reject alternative is spelled out step by step in the plan. Well-formed payloads are unaffected; malformed `subItems` values that passed as unknown keys start failing validation, which goes into the release note.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Low |

Issue is open, unlabeled and unassigned, with no comments. No blockers: the referenced #60 is closed and PR #68 merged, so the inline filter in `render_agenda` and the #60 wording in the protokoll schema are on `main`. No other open issue references #70, no `agent-docs/github/project.json` (no board fields to check), and no other open plan touches `klartex/templates/protokoll/schema.json`, the protokoll example/fixture, or the recipe tests (the #60 plan is completed). Compile coverage comes from the existing fixture-driven xelatex tests; the new tests are tex-level and need no TeX. Two agent-judgment calls to flag in the PR body: the document-not-reject direction, and adding `subItems` to the canonical example/fixture (which #60 deliberately left alone for its own scope).

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-08-30
**Feedback:** Codex round applied: the "purely additive" claim corrected — typing the field rejects malformed `subItems` that pass as unknown keys today, so a negative validation test and a risk/release-note item were added; the reject alternative rewritten step by step (it previously left the schema-contract test permanently red); `jsonschema` import noted as test-local in `tests/test_renderer.py`; the targeted pytest command switched from two `-k` flags (only the last applies) to node IDs; the schema test now asserts the three documented promises as stable fragments and validates `example.json`, which no existing test covered. Risk kept at Low.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress log
