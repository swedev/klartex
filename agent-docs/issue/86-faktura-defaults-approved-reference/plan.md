# Plan: Issue #86 — Faktura defaults: close the gap to the approved reference invoice

## Goal

A plain `klartex -t faktura` render with default settings lands close to the approved reference invoice (rendered 2026-08-07 with a custom whole-page template), so producers get a presentable invoice out of the box instead of needing a custom template for the chrome deltas: black chrome, tighter/wider geometry, a larger default height for a supplied logo, and an example payload that models the approved footer shape.

Measurable acceptance criteria (the reference artifacts — payload + `page_template.tex.jinja` — live locally with the user, not in the repo): side margins 2 cm; reclaimed top margin 1.7 cm; `brandprimary` = `brandsecondary` = `#000000`; a logo supplied without `logo_height` renders at 1 cm; the example footer matches the shape settled in D5.

## Approach

### State verified before planning

- `klartex/cls/klartex-base.cls` defines `brandprimary` = `#1A1A1A`, `brandsecondary` = `#666666`, `brandaccent` = `#0066CC` (lines 73–75). `brandsecondary` colors the letterhead header, the `pagenumber` footer fragment, and the `klartex-footer.sty` rule + text; `brandprimary` is only used for `linkcolor`/`urlcolor` in `\hypersetup`. No test asserts on the hex values.
- Geometry lives in the class: `left=3cm, right=3cm, top=0.9cm, includehead, headheight=1.2cm, headsep=1.3cm` (effective text top ≈ 3.4 cm). The header-space reclaim in `klartex/page_templates.py` (`_RECLAIM`) rewrites to `top=2cm, headheight=0pt, headsep=0pt, includehead=false` when the header slot resolves empty. A default faktura (recipe default header = bare `letterhead`, no fields) *does* reclaim — so delta 3 is purely about the values: side margins 3 cm → 2 cm, reclaimed top 2 cm → 1.7 cm.
- The reclaim string is asserted verbatim in `tests/test_block_engine.py` (~lines 1903–1958), in `tests/test_renderer.py::test_faktura_preamble_unchanged_from_golden`, and appears in all four `tests/fixtures/golden/page_template_*.tex` files.
- The body-logo default `0.8cm` lives in two `or '0.8cm'` fallbacks in `klartex/templates/_recipe_base.tex.jinja` (the `header_logo` macro, shared by faktura and kvitto) and as documentation-only `"default"` in `klartex/templates/faktura/schema.json` and `klartex/templates/kvitto/schema.json`. `tests/test_renderer.py::test_kvitto_sender_logo_and_footer` asserts `height=0.8cm`.
- `klartex example faktura` prints `klartex/templates/faktura/example.json` verbatim. Its `footer` today carries `company, address, seat, org_number, vat_number, f_tax, email, web, bankgiro, iban, bic` — six lines in the middle (Företag) column.
- Related open issues: #83 (guaranteed font set) owns the font-availability question; #65 (margins on the page-template surface) owns the future *configurability* of margins; #79 will move faktura/kvitto's top-level `footer` into the footer slot; #84 covers letterhead layout defects; #1 is the umbrella polish issue this makes concrete.

### Provenance

- **User decision** (issue #86, conversation 2026-08-31): align faktura defaults with the approved reference invoice; delta 1's black defaults are decided and class-wide.
- **Agent-extracted, open to question** (issue #86): deltas 2–4 in scope and exact values. The design decisions below say per item whether they extend a user decision or are this plan's judgment.

### Design decisions

- **D1 — Colors (user decision).** `brandprimary` and `brandsecondary` both become `#000000` in `klartex-base.cls`. Side effect: hyperlinks (`linkcolor`/`urlcolor` = `brandprimary`) render pure black and are no longer visually distinct — acceptable for print-shaped documents, noted as a consequence, not separately configurable here. `brandaccent` untouched.
- **D2 — Geometry scope: class-wide (agent judgment, open to question).** Change the class geometry to `left=2cm, right=2cm` and the reclaim to `top=1.7cm`. Rationale: delta 1 was decided class-wide, the class is today's single geometry source, and a faktura-only mechanism (a geometry hook in `recipe.yaml` + emission ordering against the reclaim) would build a second margins channel that #65 is about to design properly. Cost: every document type gets the wider text block (~17 cm line width on A4) — protokoll and the financial reports included. This is the plan's main open question for review; the faktura-scoped alternative was considered and rejected for mechanism complexity and overlap with #65.
- **D3 — Typography: deferred to #83 (agent judgment).** No default font family change in this issue. The approved invoice's Avenir Next is not in the render environment, and the environment today guarantees only MS core fonts + Latin Modern; picking a stand-in now would preempt #83's curation. The "default faktura should not read as unstyled LaTeX" intent transfers to #83 as a requirement.
- **D4 — Logo default height 1 cm (agent judgment, extends the issue's "consider").** Both `or '0.8cm'` fallbacks in `_recipe_base.tex.jinja` become `'1cm'`, and the schema defaults in faktura and kvitto follow. Kvitto follows deliberately — the fallback is shared and the two recipes mirror each other. `logo_offset` default stays `0`: the approved invoice's `y: 0.35` compensates for that artwork's built-in padding, which is artwork-specific; instead the `logo_offset` schema description already documents the padding case.
- **D5 — Example footer: approved shape plus the legally expected fields (agent judgment, deviates from the issue's listed shape — flagged for the user).** `faktura/example.json`'s `footer` becomes `company, address, seat, org_number, vat_number, f_tax, email` + payment fields (`bankgiro, iban, bic`) — only `web` is dropped. The issue lists the approved shape without `vat_number`/`f_tax`, but the example charges 25% VAT and Swedish invoice requirements expect the seller's VAT registration number, and F-tax approval is customarily stated on service invoices — the steering example should model a legally complete invoice, not just the reference's field count. If the user wants the exact approved shape instead, the change is trivial to narrow. Kvitto's example is left as is (its footer is already minimal). The footer stays top-level — #79 moves it into the slot later and will update the example again.
- **D6 — Goldens updated in place (agent judgment).** The golden fixtures were captured to lock the #63/#80 refactors' output equivalence; that purpose is served. Update only the reclaim `\geometry` line in the four golden `.tex` files (and the verbatim assertions in the tests) rather than re-capturing wholesale, so unrelated preamble drift cannot hide in a regeneration.

### Out of scope

- Default font family (D3 → #83).
- Margins as a configurable page-template setting (#65).
- Moving the top-level `footer` into the footer slot (#79).
- The header-slot fragments' `0.855cm` logo height and letterhead layout (#84).
- CHANGELOG entry — written at release time per the release flow, not in the PR.

## Steps

1. **Colors** — `klartex/cls/klartex-base.cls`: `brandprimary` `1A1A1A` → `000000`, `brandsecondary` `666666` → `000000`.
2. **Geometry, class** — `klartex-base.cls`: `left=3cm, right=3cm` → `left=2cm, right=2cm` in the `geometry` load. Leave `top`/`bottom`/`headheight`/`headsep`/`footskip` untouched (the header-present layout is not part of the approved deltas).
3. **Geometry, reclaim** — `klartex/page_templates.py::_RECLAIM`: `top=2cm` → `top=1.7cm`.
4. **Tests + goldens for the reclaim** — update the verbatim reclaim strings in `tests/test_block_engine.py` (the `\geometry{top=2cm, …}` assertions around lines 1903–1958) and the single `\geometry` line in each of `tests/fixtures/golden/page_template_{empty_header,faktura,letterhead_title,logo}.tex`; `tests/test_renderer.py::test_faktura_preamble_unchanged_from_golden` reuses the golden, so it needs no edit of its own.
5. **Logo default** — `klartex/templates/_recipe_base.tex.jinja`: both `cdata.get('logo_height') or '0.8cm'` → `or '1cm'`; `klartex/templates/faktura/schema.json` and `klartex/templates/kvitto/schema.json`: `"default": "0.8cm"` → `"1cm"` (and the description's example dimension if it now reads oddly). Update `tests/test_renderer.py::test_kvitto_sender_logo_and_footer` to expect `height=1cm`, and add one assertion that a faktura with `logo` but no `logo_height` emits `height=1cm` (the explicit-height test `test_faktura_logo_rendered_in_header_block` stays as is).
6. **Lock the new defaults in fast tests** — the goldens start at `\documentclass{klartex-base}` and cannot catch class regressions, so add cheap static assertions (no xelatex): the bundled `klartex-base.cls` contains `left=2cm`, `right=2cm` and `\definecolor{brandprimary}{HTML}{000000}` / `{brandsecondary}` ditto; and the faktura + kvitto schemas declare `logo_height` default `"1cm"` (the runtime fallback test does not verify the schema documentation).
7. **Example** — `klartex/templates/faktura/example.json`: adjust `footer` per D5.
8. **Visual check** — since D2 is class-wide, render and eyeball a matrix: `klartex example faktura | klartex -t faktura -o /tmp/faktura.pdf`, the same payload with a `logo` added and no `logo_height` (the example itself carries no logo, so the 1 cm default needs its own render), `klartex example kvitto`, `klartex example protokoll`, one financial report (e.g. resultaträkning), and one dense block-engine fixture (`tests/fixtures/block_kallelse.json`). Compare against the acceptance criteria and the approved reference; watch page-count changes and overfull-box warnings in the xelatex logs; note anything that still reads off in the PR body.
9. **Full suite** — `pytest -rs -n auto` (xelatex required); confirm no xelatex-tagged test was skipped (CI rejects skips, so a local skip hides a failure) and that no other test bakes in `3cm` side margins or the old colors.

## Risks

- **Class-wide margins widen every document type.** Protokoll, financial reports and block-engine documents all get ~17 cm text width. This is D2's deliberate trade-off but the change most likely to be reverted or re-scoped after review — the visual check in step 7 exists to catch it before the PR, and the decision is explicitly flagged as agent judgment.
- **Black hyperlinks.** `linkcolor`/`urlcolor` follow `brandprimary`; links stop being visually distinct. Consequence of the decided D1, called out so it is not rediscovered as a bug.
- **Golden updates masking drift.** Mitigated by D6: edit only the one `\geometry` line per golden, never re-capture.
- **Hidden layout assumptions on 3 cm margins.** Minipage-based layouts use fractional widths (`0.45\textwidth`, footer columns `0.34/0.30/0.36\linewidth`) so they scale, but a wider footer at 8pt may look sparse; step 7's eyeball covers it.
- **Kvitto changes ride along** (logo default, class chrome). Intended per D4, but the PR body should say so explicitly since the issue title says faktura.

## Test Plan

- `pytest -rs -n auto` — full suite including the ~80 xelatex compilations, with skip reporting on so a silently skipped xelatex test cannot pass for green; the reclaim-string tests, golden comparisons and the kvitto logo test all exercise the changed values.
- New/updated assertions: default `height=1cm` for a faktura logo without `logo_height`; updated `height=1cm` in the kvitto test; updated reclaim strings in `test_block_engine.py` and the four goldens; static assertions on `klartex-base.cls` margins + black brand colors and on the `logo_height` schema defaults (step 6), since neither goldens nor compile tests cover the class values.
- `klartex example faktura | klartex -t faktura -o /tmp/faktura.pdf` — the out-of-the-box render this issue is about; compare against the acceptance criteria in the Goal and the approved reference for chrome color, margins and footer shape. A second render with a `logo` added (no `logo_height`) verifies the 1 cm default visually.
- Visual matrix per step 8 (kvitto, protokoll, a financial report, a dense block fixture), since D2 is class-wide — record page-count changes and check overfull warnings.
