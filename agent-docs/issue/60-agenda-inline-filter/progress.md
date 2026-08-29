# Progress: Issue #60 — `agenda` renders item text without the inline filter

## Status: Completed

**Slutförd:** 2026-08-29

(Update as work proceeds — newest entries first)

- 2026-08-29: Steg 8 klart. Full `pytest` grön med xelatex på PATH: 359 passed, inga skips.
- 2026-08-29: Steg 7 klart. `tests/fixtures/block_dagordning.json` har inline-markup i dagordningen: `**positivt**` i `discussion` och `[-med reservation-] {+utan anmärkning+}` i `decision`.
- 2026-08-29: Steg 5–6 klara. `klartex/schemas/blocks/agenda.schema.json` dokumenterar inline-markup på toppnivån och per fält (`title`, `discussion`, `decision`, `subItems.items` → radbrytning blir radbrytning; `decisionLabel` → radbrytning blir mellanslag). `klartex/templates/protokoll/schema.json` får samma beskrivning på `agenda_items[].title`, `discussion` och `decision`. Inget `$id`-bump — ingen strukturell ändring. `subItems` lades inte till i receptschemat och `additionalProperties` lämnades öppet.
- 2026-08-29: Steg 4 klart. `render_agenda` i `klartex/templates/_block_macros.tex.jinja` kör `item.title | inline`, `item.discussion | inline`, `item.decision | inline` och `sub | inline` i båda numreringsgrenarna, samt `decLabel | inline_flat`. Makrots huvudkommentar uppdaterad. Steg 3:s node-id:n gröna.
- 2026-08-29: Steg 1–3 klara. `tests/test_block_engine.py`: ny klass `TestAgendaInlineMarkup` (parametrerad över `section`/`decimal` med grenspecifik fet rubrik `\punkt{\textbf{…}}` respektive `\textbf{\textbf{…}}`, markörer och `\n` → `\\` i `discussion`, kursiv/kod i `decision`, `decisionLabel` radbrytning → mellanslag, markup i `subItems` efter `\makebox`-prefixet, svenska default-citattecken och `lang: "en"` genom det importerade makrot, plus en xelatex-kompilering per numreringsstil) och `TestChangeMarking::test_markers_work_in_agenda`. `tests/test_renderer.py`: `test_recipe_agenda_items_pass_through_inline_markup` genom `_render_recipe_tex("protokoll", …)`. Samtliga sju tex-nivå-assertions verifierade röda före makroändringen.
- 2026-08-29: Branch `issue/60-agenda-inline-filter` skapad från `main`. Implementation påbörjad enligt plan.md steg 1–8.

## Avvikelser från planen

- Inga. CHANGELOG-posten skrivs vid nästa release enligt repots release-flöde (`CLAUDE.md`), inte i den här branchen.

## Uppföljning

- `klartex/templates/protokoll/schema.json` sätter inte `additionalProperties: false` på `agenda_items[]`, så ett `subItems`-fält valideras och renderas (protokoll kör `decimal`) utan att receptets kontrakt nämner det. Om protokoll ska dokumentera eller avvisa `subItems` är en produktfråga för ett eget issue.
- Kvarvarande ofiltrerade textfält i `_block_engine.tex.jinja`: `name_roster` (`title`, `name`, `role`, `note`) samt rubrikfälten i titelsida och signaturer. Egna block, kandidater för ett eget issue.
