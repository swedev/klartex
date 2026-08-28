# Progress: Issue #47 — `description_list` renders `value` without the inline filter

## Status: Completed

**Slutförd:** 2026-08-28

(Update as work proceeds — newest entries first)

- 2026-08-28: Steg 7 klart. Full `pytest` grön: 348 passed, inga skips (xelatex på PATH).
- 2026-08-28: Steg 5–6 klara. `tests/test_block_engine.py`: ny klass `TestDescriptionListInlineMarkup` (fet i värde, nästlad `\textbf{\textbf{…}}` i etikett, kursiv/kod, svenska smarta citattecken som default, `lang: "en"` som når det importerade makrot — assertion på både rubrik och `description_list` i samma dokument, samt en xelatex-kompilering av ett markup-tungt block); `TestChangeMarking::test_markers_work_in_description_list`; två nya fall i `TestCellSafeLineBreaks` (värde → `\newline` utan bart `\\`, etikett → mellanslag). `tests/test_renderer.py`: markörer/fet och radbrytning genom protokoll-metadata via `_render_recipe_tex`. `tests/test_recipe.py`: `TestRecipeLanguageReachesInlineFilters` — syntetiskt `lang: en`-recept i `tmp_path` ger engelska citattecken, plus ett svenskt kontrollfall. Verifierat att samtliga 13 nya assertions faller utan fixen.
- 2026-08-28: Steg 4 klart. `tests/fixtures/block_stadgeandring.json` har ändringsmarkering i `description_list` igen: `"Två stämmor, [-två tredjedels-] {+enkel+} majoritet"`.
- 2026-08-28: Steg 3 klart. `klartex/schemas/blocks/description_list.schema.json` dokumenterar inline-markup på toppnivån och per fält (`label` → radbrytning blir mellanslag, `value` → radbrytning inuti cellen).
- 2026-08-28: Steg 1–2 klara. `render_description_list` kör `entry.label | inline_flat` och `entry.value | inline_cell`; `_block_engine.tex.jinja` och `_recipe_base.tex.jinja` importerar `_block_macros.tex.jinja` `with context` så `pass_context`-filtren ser dokumentets `lang`.
- 2026-08-28: Branch `issue/47-description-list-inline-filter` skapad från `main`. Implementation påbörjad enligt plan.md steg 1–7.

## Avvikelser från planen

- Inga. CHANGELOG-posten skrivs vid nästa release enligt repots release-flöde (`CLAUDE.md`), inte i den här branchen.

## Uppföljning

- `render_agenda` i samma makrofil har samma glapp: `item.title`, `item.discussion`, `item.decision` och `subItems` renderas utan inline-filter. Utanför #47:s scope — kandidat för ett eget issue.
