# Issue #86: Faktura defaults: close the gap to the approved reference invoice

**Branch from:** main

## Summary

Move the default chrome toward the approved reference invoice so an out-of-the-box faktura lands close to it: `brandprimary`/`brandsecondary` default to black (user decision, class-wide), side margins 3 cm → 2 cm and the header-space-reclaim top 2 cm → 1.7 cm (class-wide, plan's judgment, open to question), body-logo default height 0.8 cm → 1 cm (faktura + kvitto, shared fallback), and `klartex example faktura`'s footer aligned with the approved field shape while keeping the legally expected `vat_number`/`f_tax` (plan's judgment, deviates from the issue's listed shape). The default-font delta is deferred to #83; margin configurability stays with #65.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Medium |

No blockers, but two provenance-flagged decisions need the user's plan review before implementation: D2 (class-wide margins — every document type reflows) and D5 (example footer keeps `vat_number`/`f_tax` against the issue's listed shape). Related: #83 (owns the font delta, deferred there), #65 (future margins surface — this issue only changes defaults), #79 (will move the top-level `footer` into the footer slot and touch the example again — rebase coordination if it lands first), #84 (letterhead header defects, untouched), #1 (umbrella polish issue). No other open plan touches these files.

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-08-31
**Feedback:** Codex review applied: the example keeps `vat_number`/`f_tax` (a VAT-charging service invoice should model a legally complete footer), measurable acceptance criteria added to the Goal, static fast tests added for the class margins/colors and schema defaults (goldens cannot catch class regressions), the visual matrix widened to kvitto + a financial report + a logo-bearing payload, and `pytest -rs` with a no-skip check. Not applied: marking the plan blocked on D2/D5 — they are provenance-flagged open decisions for the user's plan review, which is this workflow's decision gate.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress log
