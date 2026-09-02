# Progress: Issue #99 — faktura and kvitto: sender required, sender name in the logo slot, and the columns footer always rendered with missing fields labelled

## Status: Completed

(Update as work proceeds — newest entries first)

- 2026-09-02: All eleven plan steps done except step 11 (klartex.se, another repo — a release dependency for the user). Full suite green: 729 passed, 9 skipped (pre-existing local font skips).
  1. Recipe contract — `document.label_missing_footer_fields` and the footer slot's `fields_from` in `recipe.schema.json`; `RecipeDocument.footer_fields_from` / `footer_fields_from_variant` / `label_missing_footer_fields`; `_pop_fields_from` validates at load.
  2. Derivation — `_derive_slot_fields` and `_merge_derived_footer_fields`, merged under the payload's footer key by key on a new `SlotSpec`.
  3. Schema default text — `describe_recipe_defaults` per recipe, `Variant.label` in the slot model, `RECIPE_DEFAULT_TEXT` gone.
  4. LaTeX — `kxmuted` and `\newif\ifkxfooterlabelmissing` in `klartex-base.cls`; the three column blocks reworked in `klartex-footer.sty`.
  5. Recipes — both `recipe.yaml`s: derived columns footer, label flag, `sender_name` in the header `data_map`.
  6. Meta-template — the three-way `doc_header` branch and `\kxfooterlabelmissingtrue`.
  7. Data schemas — `sender` required, `sender.name` `pattern: "\\S"`, descriptions in now-state.
  8. Fixtures + regenerated faktura golden.
  9. Tests — `TestFooterFieldsFrom`, `TestDerivedFooterFields`, `TestSenderWordmark`, the schema/server `sender` cases, three text-layer cases.
  10. Docs — both READMEs and `CLAUDE.md`.
- Started: 2026-09-02. Branch `issue/99-faktura-kvitto-sender-footer` from `main`.
