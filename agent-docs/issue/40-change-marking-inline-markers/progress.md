# Progress: Issue #40 — Change marking — `{+added+}` / `{-removed-}` inline markers och `klartex-changes.sty`

## Status: Completed

**Slutförd:** 2026-08-27

(Update as work proceeds — newest entries first)

- 2026-08-27: Steg 9 klart. Full `pytest` grön (312 passed, inga skips). Verifierat att `ulem.sty` **inte** ingår i CI:s TeX-installation — på Ubuntu ligger filen i `texlive-plain-generic`, som bara är *Recommends* för `texlive-latex-extra` och därmed utesluts av `--no-install-recommends`. `texlive-plain-generic` tillagt i både `.github/workflows/ci.yml` och `.github/workflows/publish.yml`.
- 2026-08-27: Steg 8 klart. `klartex/schemas/block_engine.example.json` visar nu `{+tillagd text+}` / `{-struken text-}` i markup-demomeningen; `tests/test_agent_cli.py` grön.
- 2026-08-27: Steg 7 (soul-experimentet) **inte genomfört** — `soul.sty` saknas i den lokala TeX-installationen, så planens acceptanskriterium (visuell granskning av renderade sidor) kan inte uppfyllas. Färgad text enligt baseline levereras; `\kxaddedstyle` finns kvar som hook för ett senare försök.
- 2026-08-27: Steg 5–6 klara. Fixture `tests/fixtures/block_stadgeandring.json` (rubrik, description_list, § 7 med `revision`-stycken, § 12 med markörer i tabellceller, § 18 med långt tillagt stycke, § 22 med struken passage över sidbrytning, signaturer). Tester i `tests/test_block_engine.py::TestChangeMarking`: tex-källassertions, `revision` i `clause.content[]`, schema-avvisning av ogiltigt `revision`-värde, xelatex-kompilering av fixture och per `revision`-värde.
- 2026-08-27: Steg 4 klart. `revision` (`added`/`removed`) på `text`-blocket i `klartex/schemas/blocks/text.schema.json` + villkorlig wrap i `text`-armen i `klartex/templates/_block_engine.tex.jinja`. `text`-fältets beskrivning namnger nu markörsyntaxen.
- 2026-08-27: Steg 2–3 klara. `_ADDED_RE`/`_REMOVED_RE` matchar de escapade formerna i `klartex/inline_markup.py`, substitutionen körs efter code-stash och före fetstil. Modulens docstring dokumenterar markörernas semantik. 21 nya enhetstester i `tests/test_inline_markup.py`.
- 2026-08-27: Steg 1 klart. `klartex/cls/klartex-changes.sty` med `\kxadded`/`\kxremoved` och hookarna `\kxaddedstyle`/`\kxremovedstyle`, laddad från `klartex-base.cls`.
- 2026-08-27: Branch `issue/40-change-marking-inline-markers` skapad från `main`. Implementation påbörjad enligt plan.md steg 1–9.

## Avvikelser från planen

- **`description_list` stödjer inte inline-markup alls.** Blocket renderar `entry.value` utan `| inline`-filtret, så varken `**fet**` eller ändringsmarkörer fungerar där. Detta är ett befintligt glapp som inte är i #40:s scope — markörerna i fixturens `description_list` togs bort i stället för att filtret lades till. Kandidat för ett uppföljningsissue.
- **CI-beroendet upptäcktes vid verifiering, inte i CI.** Planens steg 9 förutsatte en CI-körning; kontrollen gjordes i stället mot Ubuntus paketinnehåll, med samma slutsats och åtgärd.
