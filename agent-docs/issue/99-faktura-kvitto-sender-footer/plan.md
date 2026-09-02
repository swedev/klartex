# Plan: Issue #99 — faktura and kvitto: sender required, sender name in the logo slot, and the columns footer always rendered with missing fields labelled

## Goal

An out-of-the-box `faktura` or `kvitto` — number, dates, one recipient, one line, and a `sender` with just a name — looks like an invoice or a receipt without a page template: the seller's name stands in the header where a logo would go, the Avsändare block sits next to the recipient, and the three-column footer (Adress | Företag | Betalning) is on the page with its gaps named in muted grey rather than collapsed. Producers that already send a full `page_template.footer` see no change.

Concretely:

1. `sender` (with a non-empty `sender.name`) becomes required in both recipe schemas. Breaking change, no shim.
2. Without `logo`, `sender.name` renders as a wordmark in the header's logo box, at the FAKTURA / KVITTO heading's size. With `logo`, nothing changes.
3. The recipes' default footer slot becomes the `columns` variant. Its fields are derived from `sender` (company, address lines, org number) and from `bankgiro` / `plusgiro` / `iban` / `bic`; a field the producer sets in `page_template.footer.fields` wins over the derived value, key by key. A footer of another variant, `null`, or a custom source is used as sent.
4. On these two recipes the columns footer renders every column; a column without content shows a label — `Adress saknas`, `Org.nr saknas`, `Betalningsuppgifter saknas` — in the column's own typography, in a new muted grey (`#6B6A63`). No validation error is raised for the gaps.

#79 has landed (closed; `footer` is rejected at the top level and `footer_has_payment` reads the slot alone), so the derivation has exactly one place to live: the footer slot.

## Approach

### State verified before planning

- `klartex/templates/faktura/schema.json` and `kvitto/schema.json`: `sender` is optional; `sender.name` is required inside the object but only typed `string` (an empty name passes). `footer` is `{"not": …}` (from #79).
- `klartex/recipe.py::load_recipe` merges `document.page_template` from recipe.yaml over `RECIPE_DEFAULT_SLOTS`; `prepare_recipe_context` hands that dict to `load_page_template(..., defaults=…)`. `_resolve_slot` takes the payload's slot value over the default wholesale (no per-key merge) and validates a slot object's `fields` against the variant's field table. `PageTemplate` and `SlotSpec` are plain dataclasses.
- `PageTemplate.footer_has_payment` reads `self.footer.fields`, so any field that ends up in the resolved slot — derived or supplied — counts.
- `klartex/cls/klartex-footer.sty::\kxfooter` builds three top-aligned minipages and replaces a column whose fields are all empty with a blank `\begin{minipage}[t]{…}~\end{minipage}` (three `\ifboolexpr` tests). Labels are language-switched with `\kxf@T{sv}{en}`.
- `_recipe_base.tex.jinja::doc_header(cdata, …)` puts `header_logo` in the left `0.45\textwidth` minipage when `cdata.logo` is set, followed by an unconditional `~`; `invoice_header` / `receipt_header` `data_map`s carry `logo`, `logo_height`, `logo_offset` — no sender field.
- `payment_info` renders the in-body Betalningsinformation block when the data has a payment field and `not page_template.footer_has_payment`.
- `klartex/registry.py::_inject_page_template` injects the generated `page_template` subtree into every recipe schema with the blanket `RECIPE_DEFAULT_TEXT` ("the letterhead header and the page-number footer with the document title", `klartex/page_templates.py:1053`); the same sentence is in the `page_templates.py` module docstring and in `README.md` / `README.en.md` (the paragraph under the slot table).
- `tests/fixtures/faktura.json` and `kvitto.json` carry no `sender`; `tests/fixtures/golden/page_template_faktura.tex` pins the faktura fixture's preamble (letterhead + `pagenumber` footer) via `test_faktura_preamble_unchanged_from_golden`. `_minimal_faktura()` in `tests/test_renderer.py`, `_MINIMAL_RECIPE_PAYLOAD` in `tests/test_schemas.py` and the faktura payload in `tests/test_server.py::test_render_faktura_top_level_footer_reports_its_path` all omit `sender`.
- `klartex/templates/*/example.json` already carry `sender` and a full `page_template.footer` (approved field form, #86).
- `brandsecondary` is `#000000` since 0.18.0 (#86); no muted grey exists in `klartex-base.cls`.
- `klartex/schemas/recipe.schema.json`: `document` is `additionalProperties: false`; `document.page_template` is a loosely typed object, so a `fields_from` map passes schema validation and must be checked in Python.
- #96 (open) will edit the two recipe.yamls, `recipe.py`, `recipe.schema.json`, `_recipe_base.tex.jinja` and the faktura golden's `\documentclass` line — the same files, different hunks.

### Where each change lives

**Derivation (change 3).** The recipes declare which footer fields derive from which data paths, in recipe.yaml:

```yaml
document:
  page_template:
    footer:
      variant: columns
      fields_from:
        company: sender.name
        address: [sender.address_line1, sender.address_line2]
        org_number: sender.org_number
        bankgiro: bankgiro      # faktura only — kvitto's schema has no payment fields
        plusgiro: plusgiro
        iban: iban
        bic: bic
```

`load_recipe` pops `fields_from` off the footer slot object into `RecipeDocument.footer_fields_from` and validates it there, so the remaining slot object (`{"variant": "columns"}`) stays valid payload syntax for `load_page_template`. Validation at load time: `fields_from` is allowed only on a footer slot object whose variant has fields (`FOOTER_VARIANTS[variant].fields`), every key must be a field of that variant, every value a non-empty string or a non-empty list of non-empty strings, and `fields` and `fields_from` on the same slot object is an error. Each rule raises `ValueError` with the recipe path and the offending key.

`prepare_recipe_context` resolves the map against the escaped `data` with `components.resolve_data_path` — a string path yields the value when truthy, a list of paths the list of truthy values (dropped when empty) — and merges the result **after** `load_page_template`: when the resolved footer `is_predefined` and its variant is the one the map was declared for, every derived key the supplied `fields` does not set — or sets to an empty value (`""`, `[]`, `null`), the same "unset" that `footer_keyvals` and `footer_has_payment` already apply — is added, on a new `SlotSpec` built with `dataclasses.replace` (the recipe's default dict and the loaded `PageTemplate` are never mutated). Any other footer — another variant, `null`, a custom `footer_source`, a whole-page source — is left as resolved. Everything downstream is unchanged: `footer_keyvals` joins the address list with `\\`, `footer_has_payment` sees the derived bankgiro, and the in-body `payment_info` block is suppressed whenever the columns footer carries a payment field.

**Labels (change 4).** Recipe-scoped, not a slot setting: `document.label_missing_footer_fields: true` in the two recipe.yamls (new boolean in `recipe.schema.json`), carried into the Jinja context, and emitted by `_recipe_base.tex.jinja` right after the page-template include as `\kxfooterlabelmissingtrue` when the resolved footer is the predefined `columns` variant. The conditional `\newif\ifkxfooterlabelmissing` lives in `klartex-base.cls` (so the emission never depends on whether `klartex-footer.sty` was loaded), and `\kxfooter`'s three column tests become: with the conditional true, always typeset the column and print the label where the content is missing; false, today's blank minipage. The label rows use the column's own font and size with `\color{kxmuted}`; `kxmuted` is a new `\definecolor{kxmuted}{HTML}{6B6A63}` next to the brand colours in `klartex-base.cls`, redefinable like them.

Per column, with labels on:

| Column | Renders | Label when |
|---|---|---|
| Adress | company line if set, then address lines or the label | no address lines (`Adress saknas` / `Address missing`) |
| Företag | Org.nr row or the label, then the other rows (vatnr, seat, F-skatt, phone, email, web) as today | no `orgnr` (`Org.nr saknas` / `Org. no. missing`) |
| Betalning | the four payment rows, or the label | none of bankgiro/plusgiro/iban/bic (`Betalningsuppgifter saknas` / `Payment details missing`) |

**Wordmark (change 2).** `invoice_header` and `receipt_header` `data_map`s gain `sender_name: sender.name`. `doc_header`'s left minipage becomes an explicit three-way branch — `logo` → `header_logo`; `elif sender_name` → `{\LARGE\bfseries\raggedright\hyphenpenalty=10000 \VAR{cdata.sender_name}\par}`; `else` → `~` — so the wordmark's baseline sits on the FAKTURA / KVITTO baseline (both minipages are `[t]`) and no stray paragraph follows it.

**Schemas (change 1).** `sender` joins `required` in both schemas and `sender.name` gets `"pattern": "\\S"` (at least one non-whitespace character; validation runs before `escape_data`, so the pattern sees the raw string) — the wordmark and the footer's company line are built on it, so an empty or blank string is a gap the schema names rather than a blank header. Descriptions are rewritten in now-state: `sender` (required; the name is the header wordmark when there is no logo, and the default footer is derived from it), `logo` (replaces the sender wordmark), `bankgiro` & co. (rendered in the footer's Betalning column; the in-body block is the fallback for a custom footer source or a non-columns footer).

**Schema and docs default text.** `RECIPE_DEFAULT_TEXT` no longer describes every recipe. `registry.py` builds the text per recipe from the loaded `Recipe`: `describe_recipe_defaults(recipe.document)` in `recipe.py` (which already imports from `page_templates.py`; the reverse import would be a cycle) names the two default variants and, when `footer_fields_from` is set, "with fields derived from `sender` and the payment fields" (source paths joined). `klartex schema faktura` then describes the columns default; protokoll keeps today's sentence. The `page_templates.py` module docstring and the README paragraph under the slot table say that recipes may declare their own defaults, with faktura/kvitto as the example.

**Body `payment_info` block.** Unchanged in code. With the derived or merged footer carrying the payment fields, `footer_has_payment` suppresses it; it still renders when the resolved footer is not the predefined columns variant (custom `footer_source`, whole-page source, `pagenumber`, `null`) and the data has payment fields. The combination "columns footer supplied without payment fields + top-level `bankgiro`" can no longer show the label in the footer and the number in the body at once, because the merge puts the bankgiro in the footer.

## Steps

1. **Recipe contract — `klartex/schemas/recipe.schema.json`, `klartex/recipe.py`.** Add `document.label_missing_footer_fields` (boolean, default false, English description) and extend the `document.page_template` description with the footer slot's `fields_from` map (field → dot-path or list of dot-paths, resolved at render time, merged under the payload's footer fields). `RecipeDocument` gains `footer_fields_from: dict` and `label_missing_footer_fields: bool`; `load_recipe` pops and validates `fields_from` per the rules above before the `RECIPE_DEFAULT_SLOTS` merge. Negative tests in `tests/test_recipe.py` (unknown destination field, `fields_from` on a `pagenumber` footer, on a bare variant string, empty list, non-string path, together with `fields`).
2. **Derivation — `klartex/recipe.py`.** `_derive_slot_fields(fields_from, data)` (uses `components.resolve_data_path`) and the post-load merge in `prepare_recipe_context`, producing a new `SlotSpec` via `dataclasses.replace`; `label_missing_footer_fields` added to the returned context. Docstrings describe the merge order (payload field > derived field) and the variants it applies to.
3. **Schema default text — `klartex/page_templates.py`, `klartex/registry.py`.** `describe_recipe_defaults(document)` in `recipe.py` replaces the blanket `RECIPE_DEFAULT_TEXT`; `discover_templates` loads the recipe (it already has the path) before calling `_inject_page_template` with the per-recipe text. `page_templates.py` module docstring updated.
4. **LaTeX — `klartex/cls/klartex-base.cls`, `klartex/cls/klartex-footer.sty`.** `\definecolor{kxmuted}{HTML}{6B6A63}` after the brand colours and `\newif\ifkxfooterlabelmissing` (default false). In the sty: `\kxf@missing{<sv>}{<en>}` (one line, `\color{kxmuted}`, label via `\kxf@T`) and the three column blocks reworked per the table, keeping the blank-minipage branch for the conditional's false state. Header comment updated (usage, "all keys are optional" paragraph, the label mode). Column widths (0.34 / 0.30 / 0.36) and the page-number line untouched. Extend `test_class_default_chrome` with the colour line.
5. **Recipes — `klartex/templates/faktura/recipe.yaml`, `kvitto/recipe.yaml`.** The `document.page_template.footer` block above, `label_missing_footer_fields: true`, and `sender_name: sender.name` in the `invoice_header` / `receipt_header` `data_map`. kvitto's `fields_from` carries only the three sender entries.
6. **Meta-template — `klartex/templates/_recipe_base.tex.jinja`.** `doc_header`'s three-way branch; after `\BLOCK{include '_page_template.tex.jinja'}`: `\BLOCK{if label_missing_footer_fields and page_template.footer.is_predefined and page_template.footer.variant == 'columns'}\kxfooterlabelmissingtrue\BLOCK{endif}`. Rewrite the `payment_info` comment in now-state.
7. **Data schemas — `klartex/templates/faktura/schema.json`, `kvitto/schema.json`.** `sender` into `required`, `sender.name` `pattern: "\\S"`, descriptions rewritten. `example.json` files stay as they are.
8. **Fixtures and golden.** `tests/fixtures/faktura.json`: add `sender` with name and address lines but no `org_number` (the fixture compile then exercises `Org.nr saknas` beside a filled Betalning column); `tests/fixtures/kvitto.json`: `sender` with name only (all three labels). Regenerate `tests/fixtures/golden/page_template_faktura.tex` by hand from the new default preamble: `\usepackage{klartex-footer}` + `\kxfooter{company=…,address=…,bankgiro=…,iban=…,bic=…,pagenumbers=true}` replace the `pagenumber` `\fancyfoot[C]`, and `\kxfooterlabelmissingtrue` appears after the composition. Update the docstring of `test_faktura_preamble_unchanged_from_golden`.
9. **Tests** — see Test Plan. Add `sender` to `_minimal_faktura()`, `_MINIMAL_RECIPE_PAYLOAD` (both recipes), the `test_server.py` faktura payload and the `test_kvitto_*` payloads.
10. **Docs.** `README.md` / `README.en.md`: the slot-table paragraph says a recipe may declare its own defaults and names faktura/kvitto's columns footer derived from `sender`; the `faktura` and `kvitto` rows in the Mallar / Templates table mention the sender wordmark and the derived footer. `CLAUDE.md` recipe-path paragraph: one sentence on `fields_from` and `label_missing_footer_fields`. CHANGELOG is written by the user at release; the PR body carries the breaking-change text (`sender` required on faktura and kvitto, `sender.name` non-empty; their default footer is `columns`, derived from `sender` and the payment fields and merged under the payload's footer fields; missing footer fields are labelled on those two recipes; `klartex schema faktura` describes the recipe's own default).
11. **klartex.se follow-up (outside this repo, needs the user's OK to open).** `llms.txt` and the landing page's curl example need `"sender": {"name": "…"}`. This is a release dependency, not a merge dependency: the PR can merge on `main`, but the version that ships it should not be published before klartex.se's guidance carries `sender` — otherwise the public example returns a 400. Recorded for the user's release step.

## Design Decisions

### 1. Derived fields are merged under the payload's columns footer, key by key; the derivation is declared in recipe.yaml

- **Options:** (a) the derived footer is the recipe's default slot and a payload `page_template.footer` replaces it wholesale; (b) per-key merge: a supplied `columns` footer keeps every field it sets and gets the derived value for every field it leaves out; (c) hard-code a faktura/kvitto branch in `recipe.py` or the meta-template instead of a recipe-declared map.
- **Decision:** (b), declared as `fields_from` in recipe.yaml.
- **Provenance:** user decision for both ends of the range — the issue: "With no footer data, the first two columns are filled from `sender`" and "Full footer data sent by the producer wins as today" — and both hold under (b). The in-between case (a partial payload footer) is agent judgment for (b): under (a), a footer sent with only `bankgiro` would print `Adress saknas` while the Avsändare block above it shows the address, and a footer sent without payment fields plus a top-level `bankgiro` would print `Betalningsuppgifter saknas` in the footer and the number in the body — two contradictions on one page. The recipe-declared map rather than a code branch keeps `recipe.py` generic and follows the `data_map` dot-path convention.
- **Empty values:** a payload field set to `""`, `[]` or `null` counts as unset and takes the derived value — the same reading `footer_keyvals` and `footer_has_payment` already give such values, so the footer's label and the body's fallback can never disagree about whether a payment detail exists.
- **Consequence if wrong:** a producer cannot leave a footer field deliberately blank on faktura/kvitto while sending it in `sender`. Bounded — the value shown is the seller's own; reverting to (a) is a change in one helper.
- **What would make (a) right:** the user wanting a supplied footer taken literally, gaps and all.

### 2. An explicit `footer: null`, `"pagenumber"` or a custom footer source is honoured — "always rendered" means the default

- **Options:** (a) force the columns footer on faktura/kvitto regardless of the payload's footer slot; (b) treat "always" as the recipe default and let the slot model's explicit choices stand.
- **Decision:** (b).
- **Provenance:** agent judgment. The issue's "always render the columns footer" is written against today's behaviour (fallback to `pagenumber` when no footer data is sent), and the slot model's contract is that the payload's slot value wins. (a) would make faktura the only surface where `footer: null` is ignored.
- **Consequence if wrong:** a producer that sends `footer: null` gets an invoice without a footer, which is what it asked for. Bounded.

### 3. The missing-field labels are recipe-scoped, not a slot setting and not global to the `columns` variant

- **Options:** (a) label gaps in the `columns` variant everywhere, including block-engine documents; (b) a `columns` slot setting (`label_missing: true`) the recipe's default sets and a producer would have to set on its own footer object; (c) a recipe document flag that turns the labels on for every `columns` footer the recipe renders, whoever supplied the fields.
- **Decision:** (c) — `document.label_missing_footer_fields` → `\kxfooterlabelmissingtrue`.
- **Provenance:** agent judgment. The issue scopes the labels to faktura and kvitto ("never hidden" on those recipes); (a) would print `Betalningsuppgifter saknas` on a protokoll or a letter using the columns footer, and (b) would hide the gaps again the moment a producer supplies its own partial footer, which is exactly the case the issue wants labelled.
- **Consequence if wrong:** the flag is one line per recipe.yaml and one `\newif`; moving it to a slot setting later is a bounded change in `page_templates.py` and the schema. No payload surface is added now, so nothing has to be kept compatible.
- **What would make (b) right:** a block-engine document wanting the same labels — then a slot setting (default false) serves both, and the recipe flag becomes its default.

### 4. kvitto labels the Betalning column too

- **Options:** (a) apply the issue's table to both recipes literally, so a receipt whose footer has no payment fields shows `Betalningsuppgifter saknas`; (b) exempt the Betalning column on kvitto (per-column toggles in the sty).
- **Decision:** (a).
- **Provenance:** agent judgment, closest to the issue's wording — change 2 and its table are stated for "`faktura` and `kvitto`" without distinction. kvitto's schema has no payment fields, so a default kvitto footer always carries the label unless the producer's `page_template.footer` supplies bankgiro & co.
- **Consequence if wrong:** a receipt footer names a gap that a receipt arguably does not have. Bounded — visible on the first render, and the fix is a per-column toggle or dropping the flag from kvitto's recipe.yaml. Surfaced in the PR body for the user to settle; a one-word comment on the issue before implementation settles it earlier.

### 5. Wordmark typography: the heading's own `\LARGE\bfseries`, ragged and unhyphenated

- **Options:** (a) `\LARGE\bfseries` like the FAKTURA heading; (b) `\kxheaderfont` at a smaller size, styled like the letterhead.
- **Decision:** (a), with `\raggedright\hyphenpenalty=10000` so a long name wraps at a word boundary instead of hyphenating (the #84 rule for org names in the letterhead).
- **Provenance:** the issue says "set there as a wordmark at the heading's height"; size is therefore user decision, the weight and wrap rule agent judgment.
- **Consequence if wrong:** typographic — one line in `doc_header`. Bounded.

### 6. The placeholder colour is a new class colour `kxmuted` = `#6B6A63`

- **Options:** (a) a new named colour in `klartex-base.cls`; (b) hard-code the hex in the sty; (c) reuse `brandsecondary`.
- **Decision:** (a).
- **Provenance:** the value is user decision (issue: "secondary grey (Grå 600, `#6B6A63`)"); (c) is ruled out because `brandsecondary` is black since #86, so the label would not read as a remark. Name and location are agent judgment, following the brand colours' `\definecolor` pattern so a custom source can redefine it.
- **Consequence if wrong:** a rename. Bounded.

### 7. The in-body `payment_info` block stays, as the fallback for a footer that cannot show payment

- **Options:** (a) remove `payment_info` now that the default footer carries payment; (b) keep it, driven by the existing `footer_has_payment` signal.
- **Decision:** (b).
- **Provenance:** agent judgment. With a custom `footer_source`, a whole-page source, `pagenumber` or `null`, the footer slot has no payment detail and the data's `bankgiro` would otherwise vanish from the page. The signal already exists and needs no change; with decision 1 it is never true while the columns footer shows the payment label.
- **Consequence if wrong:** an in-body block that is rarely reached. Bounded; removal is a later cleanup.

### 8. `sender` required and `sender.name` non-empty; breaking, no shim

- **Decision:** add `sender` to `required` in both schemas and `pattern: "\\S"` on `sender.name`; nothing is accepted or translated for payloads that omit it.
- **Provenance:** user decision (issue change 1: "an invoice without a seller is not an invoice") and the repo convention of no backward-compatibility shims (memory note, #79). The pattern is agent judgment: `""` or `"   "` would satisfy `required` and render a blank wordmark and a blank company line, which is the state the issue is removing.
- **Consequence if wrong:** a producer without `sender` gets a 400 naming the missing property. Bounded.

### 9. The Avsändare party block stays next to the recipient

- **Decision:** unchanged — name in the header and the legal block in the body coexist.
- **Provenance:** the issue leaves this to the plan ("Open to question, plan's judgment … so keep it"); agent judgment agrees: the wordmark is branding, the party block is the legal seller identification with org number and address.
- **Consequence if wrong:** the block is one `\BLOCK{if}` in `invoice_recipient`. Bounded.

### 10. `fields_from` is validated at recipe load, and cannot sit beside `fields`

- **Decision:** unknown destination fields, wrong variant, bad path shapes, and `fields` + `fields_from` on one slot object all raise at `load_recipe`, not at render. Literal defaults and derived defaults on the same slot are not combined.
- **Provenance:** agent judgment. `document.page_template` is loosely typed in the recipe schema, so a typo would otherwise surface as a `ValueError` from `_resolve_slot` on the first render, or silently as a label. No recipe needs both forms today; allowing both would need a precedence rule nobody has asked for.
- **Consequence if wrong:** a future recipe wanting a literal default beside derived fields relaxes one check. Bounded.

### 11. Examples stay; fixtures and the golden change

- **Decision:** `example.json` files (already `sender` + full footer, approved form from #86) are untouched. Test fixtures gain a `sender` shaped to exercise the labels, and the faktura golden is regenerated in the same commit.
- **Provenance:** existing convention (`TestPageTemplateGoldens` docstring: a deliberate fragment change updates the golden in the same commit).
- **Consequence if wrong:** none beyond a fixture edit.

## Risks

- **Breaking for every faktura/kvitto producer that omits `sender`**, including klartex.se's `llms.txt` guidance and the landing page's curl example. The schema error names the property; the klartex.se update (step 11) is a release dependency handled by the user. This is what makes the risk Medium.
- **The default preamble for faktura changes** (`pagenumber` → derived `columns` footer). The golden test and `test_faktura_top_level_footer_is_not_rendered` (asserts `\usepackage{klartex-footer}` absent) both fail until re-expressed — every affected test is listed below, and each was read during planning.
- **`klartex schema faktura` must describe the new default** — the injected `page_template` description is generated from a blanket sentence today (step 3). Without that step the discovery surface tells an agent the footer defaults to page numbers.
- **The columns footer's band geometry now applies to every default faktura/kvitto** (`klartex-footer.sty` enlarges `bottom`/`footskip`). An invoice that fit one page with the slim `pagenumber` footer could run to two; the text-layer test asserts the fixture invoice stays on one page.
- **`\ifboolexpr` rework in the sty** is the most error-prone edit (three tests, `\multicolumn` rows inside `kxf@coltab`). Both label modes are compiled by the suite: faktura/kvitto fixtures (labels on) and the block-engine columns-footer render (labels off).
- **Escaping:** derived values come from the already-escaped `data`, the same source the party block prints, so no double-escaping; the address list is joined with `\\` by `footer_keyvals` exactly like a payload list.
- **Shared mutable defaults:** the merge must build a new `SlotSpec`; a test renders two payloads with different senders through one loaded recipe and asserts neither leaks into the other.
- **Open plans touching the same files:** #96 (retire `narrowmargins`) edits the two recipe.yamls, `recipe.py`, `recipe.schema.json`, `_recipe_base.tex.jinja` and the golden's `\documentclass` line. Sequential merges, not overlapping hunks; whichever lands second rebases the golden.

## Test Plan

Unit (no xelatex):

- `tests/test_schemas.py`: `sender` missing → `ValidationError` for both recipes; `sender: {}`, `sender: {"name": ""}` and `sender: {"name": "   "}` rejected; `_MINIMAL_RECIPE_PAYLOAD` gains `sender` so the top-level-footer tests keep validating; examples and fixtures still validate; the injected `page_template` description for `faktura` and `kvitto` names `columns` and `sender`, protokoll's still names the page-number footer.
- `tests/test_recipe.py`: faktura/kvitto `recipe.yaml` loads with `document.page_template["footer"] == {"variant": "columns"}` (no `fields_from` left in the slot), `footer_fields_from` populated, `label_missing_footer_fields` true; protokoll unchanged (`RECIPE_DEFAULT_SLOTS`, flag false); the negative cases from step 1 raise `ValueError` naming the key.
- `tests/test_renderer.py`:
  - derived footer: `_minimal_faktura(sender={name, address_line1, address_line2, org_number}, bankgiro=…)` emits `\usepackage{klartex-footer}`, `company={…}`, `address={…\\…}`, `orgnr={…}`, `bankgiro={…}`, and no in-body `Betalningsinformation`;
  - sender with name only → keyvals carry only `company`; `\kxfooterlabelmissingtrue` present;
  - merge: payload `columns` footer with `company="Annat namn"` and `email` only, plus `sender` with address and top-level `bankgiro` → keyvals carry `company={Annat namn}` (payload wins), `email`, the derived `address` and `bankgiro`; in-body block suppressed; payload footer with `company` and `f_tax` but no `org_number` and a sender without one → no `orgnr` keyval (label at compile time); payload footer with `bankgiro: ""` plus top-level `bankgiro` → `bankgiro={…}` in the keyvals and no in-body block;
  - `footer: "pagenumber"` and `footer: null` → no `\kxfooter`, no `\kxfooterlabelmissingtrue`, in-body block rendered when `bankgiro` is set; `footer_source="…"` → source emitted, in-body block rendered;
  - two renders through one loaded recipe with different senders: the second's keyvals carry only its own sender;
  - wordmark: without `logo`, the `\LARGE\bfseries\raggedright\hyphenpenalty=10000 <name>` wrapper appears; with `logo`, `\includegraphics` appears and the wrapper does not (the name itself still appears in the Avsändare block and the footer keyvals, so the assertion targets the wrapper); same for kvitto;
  - `test_faktura_sender_block_rendered` drops its "without sender" half; `test_kvitto_without_sender_renders_no_party_block` becomes "kvitto with sender and no recipient renders the Avsändare block and an empty right column";
  - `test_faktura_top_level_footer_is_not_rendered`: keep the "Från data"/"1111-1111" assertions, drop the `\usepackage{klartex-footer}` absence;
  - `test_faktura_payment_info_renders_without_footer` → re-expressed as "renders with a custom footer source"; `test_faktura_payment_info_skipped_when_no_payment_fields` unchanged in intent;
  - `test_faktura_preamble_unchanged_from_golden` against the regenerated golden; `test_class_default_chrome` asserts `\definecolor{kxmuted}{HTML}{6B6A63}`;
  - protokoll tex has no `\kxfooterlabelmissingtrue`.
- `tests/test_server.py`: the faktura payload gains `sender`; a request without `sender` returns 400 `validation_error` whose message names `sender`.

xelatex:

- `test_render_pdf` for the `faktura` and `kvitto` fixtures (labels on, mixed filled/missing columns) and the existing block-engine columns-footer compile (labels off).
- `tests/test_pdf_text_layer.py` (existing `requires_tools` marker, xelatex + pdftotext):
  - a minimal faktura with `sender: {name}` and no payment fields: the text layer contains the sender name, `Adress saknas`, `Org.nr saknas` and `Betalningsuppgifter saknas`, and the document is one page (one `\f` separator);
  - the same payload with address, org number and bankgiro contains none of the three labels;
  - a block-engine document with a `columns` footer carrying only `company`: none of the three labels (label mode off outside the recipes).

Manual, for the user to look at (no quality claims from the agent): render `_minimal_faktura` with `sender: {name: "Exempelbolaget AB"}` via the CLI and open the PDF — wordmark placement against the FAKTURA heading, the grey labels in the footer, and page count.
