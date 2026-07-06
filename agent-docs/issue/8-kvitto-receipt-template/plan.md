# Plan: Issue #8 — Template: kvitto (receipt)

## Goal

Add a `kvitto` (receipt) template as a new recipe: a payment confirmation that is deliberately lighter than faktura — receipt number, date, a simple items list, one explicit total, payment method. No VAT breakdown, no due date, no line-item price computation.

## Approach

**Recipe path, not block engine.** A kvitto is exactly the kind of stable transactional document the recipe path exists for (domain-shaped JSON from upstream systems, fixed layout), parallel to faktura. The block engine remains available for free-form receipts, but producers sending `{receipt_number, items, total_amount}` should not have to describe layout.

**Reuse before build.** The recipe is composed from:

- **New recipe-only components** (2): `receipt_header` and `receipt_table`. `invoice_header` cannot be reused — it hardcodes the "FAKTURA" title and a due-date line. `invoice_table` cannot be reused — it computes per-line `quantity × unit_price` and a VAT summary, which a receipt must not have.
- **Existing mechanisms**: `description_list` + `document.metadata` (with `optional: true`) renders the payment-method/paid-by label-value pairs — no new component needed. `invoice_note` renders the optional footer note as-is (it is generic despite the name).

**Design decisions carried over from the original plan** (still sound, re-validated against today's issue text):

1. Items are `{description, amount?}` — a simple list, not the faktura quantity/unit/price model. Per-item amounts are informational only.
2. `total_amount` is an explicit required field, never computed from items (item amounts are optional, so summation would be unreliable).
3. `payment_method` is a free-text string ("Kontant", "Swish", "Kort", …).
4. Seller identity comes from the page template (`\orgname`, logo) — no seller fields in the schema; the free-text `note` covers edge cases.

**Currency handling:** follow the existing faktura pattern — `comp.data.get('currency') or 'SEK'` in the template arm. JSON-Schema `default` values are not injected at validation time, so the fallback must live in the template (see `test_faktura_missing_currency_defaults_to_sek`).

## Steps

1. **`klartex/templates/kvitto/schema.json`** — draft-07, same shape as faktura's schema.
   - Required: `receipt_number` (string), `date` (string, YYYY-MM-DD), `total_amount` (number), `items` (array, minItems 1).
   - `items[]`: object with required `description` (string), optional `amount` (number).
   - Optional: `page_template` (enum formal/clean/none, default formal), `currency` (string, default SEK), `payment_method` (string), `paid_by` (string), `note` (string).
   - Descriptions in the same style as faktura's schema.

2. **`klartex/templates/kvitto/recipe.yaml`** — `template.name: kvitto`, `lang: sv`, `document.title: "Kvitto {{ data.receipt_number }}"`, `document.page_template: "{{ data.page_template | default('formal') }}"`.
   - `document.metadata`: `payment_method` (label "Betalsätt", optional) and `paid_by` (label "Betalt av", optional).
   - Components in order: `receipt_header` (data_map: receipt_number, date), `receipt_table` (data_map: items, total_amount, currency), `description_list`, `invoice_note` (data_map: note).

3. **`klartex/components.py`** — two new recipe-only `ComponentSpec` entries (no `sty_package`, no `block_schema_path`, so they stay invisible to the block engine like the `invoice_*` family):
   - `receipt_header` — "Right-aligned receipt header with number and date".
   - `receipt_table` — "Receipt items list with optional per-item amounts and explicit total".

4. **`klartex/templates/_recipe_base.tex.jinja`** — two new component arms, placed next to the `invoice_*` arms, plus one guard on an existing arm:
   - `receipt_header`: mirror `invoice_header` (flushright, `\Large\bfseries KVITTO`, Nr, Datum) minus the due-date line.
   - `receipt_table`: `tabularx` `{Xr}` with booktabs rules; each item row shows description and the amount column uses an explicit `item.get('amount') is not none` check — so `amount: 0` renders as `0.00`, and only a truly absent amount gives an empty cell. Below the table a flushright block with a single prominent line `\textbf{Summa:} \textbf{{:,.2f} {currency}}` using the explicit `total_amount`. No subtotal/VAT rows.
   - Guard the existing `description_list` arm with `\BLOCK{if metadata}`: `recipe.py` skips `optional: true` metadata whose value is absent, so a kvitto without `payment_method`/`paid_by` yields `metadata == []`, and `render_description_list([])` would otherwise emit 4em of spacing around an empty `tabularx`. The guard is a no-op for protokoll (always has metadata).

5. **`klartex/templates/kvitto/example.json`** — full example payload (all optional fields set). Required for `klartex example kvitto` (`cli.py` reads `templates/<name>/example.json`).

6. **`tests/fixtures/kvitto.json`** — realistic fixture (förening use case: e.g. medlemsavgift paid via Swish), all fields populated.

7. **Test updates:**
   - `tests/test_schemas.py`: add `"kvitto"` to `test_discover_all_templates` and to the `test_fixture_validates` parametrize list.
   - `tests/test_renderer.py`: add `"kvitto"` to the recipe parametrize list (line ~23) and a `test_kvitto_discovered` alongside `test_faktura_discovered`; xelatex render test comes free via the parametrized full-pipeline test.
   - `tests/test_components.py`: assert `receipt_header` and `receipt_table` are registered, with `sty_package is None` and `block_schema_path is None`, next to the existing recipe-only component assertions (~line 122).
   - Add a focused test rendering items with one missing amount and one `amount: 0` — the zero must render as `0.00`, the missing one as an empty cell — and assert `total_amount` appears formatted.
   - Add a minimal-payload render test (no metadata fields set) asserting the description_list output is absent (empty-metadata guard).

8. **Docs:** add a `kvitto` row to the template tables in `README.md` and `README.en.md`, extend the recipe-template enumerations (`protokoll`, `faktura`, …), and add `receipt_header`/`receipt_table` to the recipe-component lists (~line 140) in both files.

## Risks

- **Low overall.** Registry auto-discovers `recipe.yaml + schema.json`; no registry or CLI changes needed.
- `_recipe_base.tex.jinja` is shared by all recipes — the new `elif` arms are additive, but the `description_list` guard (step 4) touches an arm used by protokoll; the guard only changes the `metadata == []` case, which no existing recipe hits. Covered by the existing protokoll render tests.
- Jinja number formatting: `total_amount` arrives as int or float from JSON; `"{:,.2f}".format()` handles both (same as faktura lines).

## Test Plan

- `pytest` — full suite including new kvitto tests (fixture validation, discovery, xelatex compile).
- `klartex -d tests/fixtures/kvitto.json -t kvitto -o /tmp/kvitto.pdf` — visual check: lighter than faktura, total prominent, no VAT.
- Render a minimal payload (only required fields) — no payment method, no note, no per-item amounts.
- `klartex templates` lists kvitto; `klartex schema kvitto` and `klartex example kvitto` return the new schema/example.
- LaTeX-special characters in `description`/`note` (e.g. `50%`, `A&B`) render escaped.
