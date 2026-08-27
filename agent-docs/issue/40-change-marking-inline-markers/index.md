# Issue #40: Change marking — `{+added+}` / `{-removed-}` inline markers and `klartex-changes.sty`

**Branch from:** main

## Summary

Semantic change marking for documents that show what changed between two versions (canonical case: stadgeändringar). New `klartex-changes.sty` owns `\kxadded` (green) / `\kxremoved` (red + strikethrough) macros, loaded unconditionally from `klartex-base.cls`. Inline markers `{+…+}` / `{-…-}` are added to `inline_markup.py` — matched in their *escaped* form (`\{+…+\}`), since the filter runs after `escape_data()` — and a block-level `revision: "added" | "removed"` attribute lands on the `text` block. Clause/list-level revision is deferred to a follow-up. Canonical example: a new `block_stadgeandring.json` fixture that also probes the known fragility spots (tabular cells, page breaks).

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Medium |
| **Issue state** | Open, label `enhancement`, no comments (verified via `gh issue view 40`, 2026-08-27) |
| **Blockers** | None (no parent/dependency references; no related open issues found) |
| **Plan conflicts** | None — no other open plan touches `inline_markup.py` or the changes sty; the `_block_engine.tex.jinja` text-arm edit avoids the spacing-fix lines |
| **Test dependency** | XeLaTeX (already required by CI) |
| **Runtime dependency** | `ulem.sty` becomes a hard dependency of every render (verify once in CI); `soul.sty` is experiment-only and not installed locally |
| **Behavior change** | New marker syntax in all inline-markup fields on both rendering paths (text containing `{+…+}`/`{-…-}` shapes previously rendered literally); ulem loaded globally with `[normalem]` (no intended emphasis/visual change to existing documents, locked by full-fixture regression) |

## Plan Review

**Status:** Reviewed

**Reviewed:** 2026-08-27

**Feedback:** Codex confirmed the overall order (sty → parser → tests → schema/template → fixture) and pushed four things that were applied: explicit marker semantics (mixed nesting locked by test, same-type nesting undefined, adjacent/empty/unmatched markers, escaped specials and code spans inside markers); rendered-source assertions via the existing tex helper instead of relying on "the PDF compiled", plus invalid-`revision` schema rejection and a clause-nested revision case; risk raised to Medium with `ulem` named as a hard runtime dependency and `soul` demoted to a conditional, availability-gated experiment with visual acceptance; marker syntax documented in `text.schema.json`'s field description, not only the example payload. Codex's suggestion to drop the `progress.md` link was skipped — the repo template mandates it and the file is created during implementation.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress log
