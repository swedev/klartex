# Issue #99: faktura and kvitto: sender required, sender name in the logo slot, and the columns footer always rendered with missing fields labelled

**Branch from:** main

## Summary

Makes a bare `faktura` / `kvitto` look like one without a page template: `sender` (with a non-blank `name`) becomes required in both schemas (breaking, no shim); without `logo` the sender's name renders as a wordmark in the header's logo box; the recipes' default footer slot becomes the `columns` variant with fields derived from `sender` and the payment fields — declared as `fields_from` in recipe.yaml, validated at load, resolved in `prepare_recipe_context` and merged key by key under whatever the payload's columns footer sets (a footer of another variant, `null` or a custom source is used as sent); and on these two recipes the columns footer renders every column, naming a gap (`Adress saknas`, `Org.nr saknas`, `Betalningsuppgifter saknas`) in a new muted grey `kxmuted` (`#6B6A63`) via a recipe-scoped `\kxfooterlabelmissing` conditional. `klartex schema faktura` describes the recipe's own default. Builds on #79 (merged). klartex.se's `llms.txt` and landing-page example need `sender` added before the release that ships this.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Medium |
| **Blocked by** | None (#79 closed) |
| **Related** | #79 (prerequisite, merged), #1 (closed, referenced), #86 (approved reference, examples), #96 (same files: recipe.yamls, `recipe.py`, `recipe.schema.json`, `_recipe_base.tex.jinja`, faktura golden), #62 (footer layout options) |

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-09-02
**Feedback:** Codex's first pass turned the derivation from wholesale slot replacement into a per-key merge under the payload's columns footer (removing two contradictory-output cases with the in-body `payment_info` block), added load-time validation of `fields_from`, per-recipe text for the injected `page_template` schema description and README paragraph, an explicit three-way wordmark branch, and tests for mutation leaks, page count, label-mode-off and a supplied footer without `org_number`. The second pass settled empty payload values as "unset" for the merge and replaced `minLength` with a non-whitespace pattern on `sender.name`.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress log
