# Issue #79: faktura and kvitto: use the regular footer slot instead of their own top-level `footer`

**Branch from:** main

## Summary

Removes the top-level `footer` field from the `faktura` and `kvitto` recipes so the page template's footer slot (`page_template.footer`, `columns` variant) is the single place for contact and payment details. Drops the template-level `emit_kxfooter` emission and the `data_footer` branch in `_recipe_base.tex.jinja`, lets `footer_has_payment` be the only suppression signal for the in-body `payment_info`, moves the examples to the slot form and rewrites the tests that locked the old precedence. Breaking, no shim — a top-level `footer` is rejected by the schema (`"footer": false`) rather than silently dropped, because klartex.se's `llms.txt` documents the old field; that guidance needs a coordinated update. Prerequisite for #99.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Medium |
| **Blocked by** | None |
| **Related** | #99 (blocked by this), #96 (adjacent edits in `_recipe_base.tex.jinja`), #78 (schema strictness), #63 |

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-09-02
**Feedback:** Codex found that klartex.se's `llms.txt` publicly documents the top-level `footer`, which flipped decision 1 from silent-ignore to schema rejection and raised the risk to Medium; also added removal of the now-unused `footer_keyvals` Jinja global in `renderer.py`, a schema-level rejection test (the tex helper bypasses validation), a fuller whole-page-source test, and fixes to the `note` descriptions.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress log
