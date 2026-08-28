# Issue #47: `description_list` renders `value` without the inline filter

**Branch from:** main

## Summary

Routes `description_list`'s `entry.value` and `entry.label` through the inline-markup filters (`inline_cell` for the paragraph-mode value column, `inline_flat` for the LR-mode label column) in the shared `render_description_list` macro, so bold/italic/code, smart quotes, and change markers `{+…+}` / `[-…-]` work like in every other text-bearing block — on both the block-engine and recipe surfaces at once. Also adds `with context` to the `_block_macros.tex.jinja` imports, fixing a latent bug found during planning: the `pass_context` inline filters never saw the document `lang` inside imported macros, so headings rendered Swedish smart quotes even in `lang: "en"` documents.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Low |

No blockers: the referenced #40 (change marking) and PR #45 are closed/merged. Note that #52 (v0.15.0) changed the removed-marker notation after the issue was written — it is `[-…-]` now, not `{-…-}` as the issue body says. No related open issues found via search; no other open plan touches the templates or macro files involved. Follow-up candidate noted in the plan: `render_agenda` in the same macro file has the identical missing-filter gap (`item.title`/`discussion`/`decision`) — out of scope here, propose filing a separate issue.

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-08-28
**Feedback:** Codex round applied: a synthetic `lang: en` recipe test to actually lock `with context` on the recipe path (marker tests alone are lang-independent), a nested `\textbf{\textbf{…}}` assertion for label markup (a bare `\textbf` check passes even without the fix), corrected test-command claims (`-k "not xelatex"` filters names, not skipif markers — use node IDs), a schema-description update for agent introspection, and the PDF text-layer claim scoped down to actual coverage. The `with context` bundling is now stated as a decided agent-judgment call to flag in the PR body.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress log
