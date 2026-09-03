# Issue #98: Letterhead columns overflow on a single unbreakable token

**Branch from:** main

## Summary

A long email or web address in the letterhead's contact column overruns its 0.25\textwidth minipage because #84's `\hyphenpenalty=10000` forbids every break inside the token. Fix: the slot model's `Field` gains a `breaks_after` flag, set to `@./` on the letterhead's `web` and `email` fields, and `PageTemplate.header_macros` inserts `\allowbreak{}` after each run of those characters before the `\renewcommand` is emitted. The fragment, the goldens and the JSON surface are unchanged; a bbox-based render test locks the column's right edge.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Low |

Deferred from PR #93 (issue #84, closed). No open issue references #98; no open plan touches `header_macros` or the letterhead fragment (#99 works in the faktura/kvitto footer, a different slot). Plan verified against `main` at `d1bc528`.

## Plan Review

**Status:** Reviewed

Reviewed: 2026-09-02. Feedback applied: replaced the prototype's numbers with measurements from the real renderer (37pt overflow, three-line wrap, 2.6pt headroom on the widest segment); breaks now go after each run of separators so `https://` stays whole; added D6 on vertical growth (seven-line ceiling, 9.5pt above the body) with its own render test; parameterized the render test over email, `www.` and `https://` shapes via a plural bbox helper with explicit A4 geometry; corrected the footer-extensibility claim (`footer_keyvals` does not read the flag); added a schema-description assertion since `test_schemas.py` strips descriptions.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress log
