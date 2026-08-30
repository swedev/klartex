# Progress: Issue #70 — Protokoll recipe: `subItems` on `agenda_items[]` is accepted and rendered but undocumented

## Status: Completed

**Slutförd:** 2026-08-30

(Update as work proceeds — newest entries first)

- [x] Steg 5: `pytest -n 4` — 368 passerade, 0 skippade (baslinje 365 + tre nya tester). Manuell kontroll: `klartex -d tests/fixtures/protokoll.json -t protokoll` ger 3.1.–3.3. under "Ekonomisk rapport", efter beslutsraden, och `klartex schema protokoll` visar `subItems`.
- [x] Steg 4: `subItems: ["Intäkter", "Kostnader", "Prognos för 2026"]` på "Ekonomisk rapport" i `klartex/templates/protokoll/example.json` och `tests/fixtures/protokoll.json` (filerna är fortsatt identiska)
- [x] Steg 3: `subItems` dokumenterad i `klartex/templates/protokoll/schema.json` — array av strängar, ingen `additionalProperties`. Steg 2:s tester gröna efteråt.
- [x] Steg 2: `tests/test_schemas.py` — `test_protokoll_schema_documents_sub_items` och `test_protokoll_sub_items_must_be_strings`, båda sedda röda före steg 3 (`KeyError` respektive `DID NOT RAISE`)
- [x] Steg 1: `tests/test_renderer.py::test_recipe_agenda_sub_items_render_with_decimal_numbering` — grön direkt, låser decimal undernumrering, inline-filtret och placeringen efter beslutet
