# Progress: Issue #96 — Re-express the invoice recipes' margins through the margins surface and retire the narrowmargins class option

## Status: Completed

**Completed:** 2026-09-03

(Update as work proceeds — newest entries first)

## 2026-09-03 — all steps done

Plan steps 1–11 complete. `pytest -n auto`: 789 passed, 9 skipped (all
pre-existing font-availability skips, unrelated). Smoke renders of faktura,
kvitto and protokoll with the repo code; `klartex templates` and
`klartex schema faktura` run clean.

1. Baseline recorded (pre-change `pdftotext -bbox` word boxes for both
   fixtures).
2. `load_page_template` merges `defaults["margins"]` under the payload's, per
   key; docstrings updated.
3. `recipe.py`: `class_options` removed from the dataclass, the load and the
   context; `_check_recipe_margins` validates the recipe's margins at load;
   `describe_recipe_defaults` gained the margins clause.
4. `recipe.schema.json`: `class_options` deleted, `page_template` description
   extended.
5. `_recipe_base.tex.jinja`: unconditional `\documentclass{klartex-base}`.
6. faktura/kvitto `recipe.yaml`: `class_options` → `page_template.margins`
   `{left: 2cm, right: 2cm, top: 1.7cm}`.
7. `klartex-base.cls`: `\DeclareOption{narrowmargins}` and
   `\ProcessOptions\relax` removed; margin-profile comment rewritten.
8. Golden diff verified by hand — exactly the `\documentclass` line plus the
   three margin lines (`\renewcommand{\kxreclaimtop}{1.7cm}`,
   `\geometry{left=2cm, right=2cm, headsep=\dimexpr 1.7cm-2.1cm\relax}`,
   `\setlength{\headwidth}{\textwidth}`); golden updated; stale docstring
   fixed.
9. Tests updated/added across `test_renderer.py`, `test_page_templates.py`,
   `test_recipe.py`, `test_schemas.py`, `test_pdf_text_layer.py`.
10. `README.md`, `README.en.md`, `CLAUDE.md`: one sentence each.

### Position invariance

Every word box on the first page of both fixtures is byte-identical before
and after the change — not just the two committed anchors. faktura's
`Betalningsvillkor:` at (56.693, 253.276) and kvitto's `Betalsätt` at
(56.693, 311.275) are the committed expected values in
`test_invoice_body_text_sits_at_the_recipes_own_margins`; 56.693pt is
`2 * _PT_PER_CM`.
