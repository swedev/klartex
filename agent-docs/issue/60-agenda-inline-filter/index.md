# Issue #60: `agenda` renders item text without the inline filter

**Branch from:** main

## Summary

Routes `item.title`, `item.discussion`, `item.decision` and `subItems[]` through the `| inline` filter (and `decisionLabel` through `| inline_flat`) in the shared `render_agenda` macro, so bold/italic/code, locale-aware smart quotes and the change markers `{+…+}` / `[-…-]` work in agenda items like in every other text-bearing block — on both the block engine's `agenda` block and the protokoll recipe at once. Documents the support in `agenda.schema.json` and in protokoll's `schema.json`, puts markup into the canonical `block_dagordning.json` fixture, and adds red-first tests through both surfaces and both numbering styles. Same shape as #47 / PR #58; the `with context` import that fix added already carries `lang` into the macro.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Low |

Issue is open, unlabeled and unassigned, with no comments. No blockers: the referenced #47 is closed and PR #58 merged, so the `with context` prerequisite is on `main`. No other open issue references #60, and no other open plan touches `_block_macros.tex.jinja`, `agenda.schema.json` or the agenda tests (the #47 plan is completed). Compile tests need xelatex on PATH; the tex-level tests do not. The deliberate behaviour change (literal markup/quote characters in agenda text start being interpreted) goes into the next release's CHANGELOG, not this branch. Two agent-judgment calls to flag in the PR body: `inline` (newline → `\\`) for all four item fields including titles, and filtering `decisionLabel` too. Follow-up candidates noted in the plan: whether protokoll should document or reject `subItems`, and the remaining unfiltered text fields (`name_roster`, title-page and signatures headers).

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-08-29
**Feedback:** Codex round applied: the section-style title assertion corrected to `\punkt{\textbf{…}}` (the outer `\textbf` lives in the unexpanded `\punkt` definition, so the nested form only appears in the decimal branch); steps reordered so tests land and fail before the macro change; protokoll's `schema.json` added to the documentation work; the pre-escaping claim scoped correctly for recipe `decisionLabel` (trusted, unescaped `recipe.yaml` option); both-branch coverage made explicit via a parametrized test; and two triage statements fixed (`name_roster` has four raw fields, not one; the protokoll fixture is left alone as a scope choice, not because of `test_recipe.py:115`). Risk kept at Low, consistent with #47's identical behaviour-change profile.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress log
