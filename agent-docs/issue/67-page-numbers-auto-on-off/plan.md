# Plan: Issue #67 — Page numbers: auto/on/off, as a setting on the slot that carries them

## Goal

Replace the document-level boolean `page_template.page_numbers` with a tri-state setting — `"auto"` (page numbers only when the document runs past one page), `"on"` (always, including `Sida 1 av 1`), `"off"` (never) — that lives on the footer slot carrying the page numbers: `pagenumber` and `columns` both get it among their slot settings. The global key leaves the surface entirely (schema and loader both reject it), with no alias.

The issue's own premise needs one correction, verified against the code: the "render only when more than one page" rule is hardcoded today **only in the columns footer** (`klartex/cls/klartex-footer.sty:182-189`, `\ifnum\getpagerefnumber{LastPage}>1`). The `pagenumber` fragment (`klartex/page_templates/footer/pagenumber.tex.jinja:5`) prints `Sida 1 av 1` unconditionally on a one-page document. So today's behaviour is `on` for `pagenumber` and `auto` for `columns`. Making `auto` the default for both, as the issue decides, changes what a one-page block-engine or protokoll document prints in its footer: nothing (or the title alone) instead of `Sida 1 av 1`. That is a visible default change and is listed under Breaking changes.

## Approach

### State verified before planning

- `page_numbers` is a `DOCUMENT_SETTINGS` entry (`klartex/page_templates.py:618`), a `PageTemplate` field defaulting to `True` (`:724`, resolved at `:1019-1021`), and is threaded into the footer fragment context by `PageTemplate.footer_fragment` (`:770`). Nothing else in `klartex/` reads it: `block_engine.py`, `recipe.py` and `klartex/server/` only call `load_page_template`.
- The composition `klartex/templates/_page_template.tex.jinja:39-43` special-cases `variant == 'pagenumber' and not page_numbers` by emitting `\fancyfoot[C]{}` instead of the fragment. That is the only place the composition knows about page numbers; it goes.
- `columns.tex.jinja:7` emits the `\kxfooter` keyval `pagenumbers=true|false`, consumed by `\define@key{kxfooter}{pagenumbers}` as a `\newif` (`klartex-footer.sty:46,61`); the `>1` test uses `\getpagerefnumber` from `refcount`, which only `klartex-footer.sty` requires (`:29`). `refcount.sty` is installed in the CI TeX Live (the faktura fixtures render there), so requiring it from the class adds nothing to `.github/tl_packages`.
- #63 reserved this exact spot: the loader rejects `{"footer": {"variant": "pagenumber", "page_numbers": …}}` today (`tests/test_page_templates.py:316-318`, `tests/test_schemas.py:343`), explicitly "until #67 defines its tri-state" (agent-docs/issue/63 plan, D2). Both tests flip.
- `_check_settings` (`page_templates.py:856-891`) validates setting *keys* and the `fields` object, but not a setting's *value* — the `title` boolean is taken as-is. The schema is what rejects a wrong type on the validated paths; the loader is reached without the schema from Python callers and the custom-source paths.
- The recipes' defaults carry no `page_numbers`: `RECIPE_DEFAULT_SLOTS` is `{"variant": "pagenumber", "title": True}` (`:674-677`) and faktura/kvitto declare a `columns` footer with `fields_from` (`klartex/templates/faktura/recipe.yaml:19-28`). Both therefore resolve to `auto`, and the columns footer keeps its current behaviour exactly. A payload's own `page_template.footer.page_numbers` on faktura/kvitto has to survive the `fields_from` merge in `recipe.py` — that merge touches `fields` only, but a rendered test locks it.
- Goldens pin the emitted preamble as an order-insensitive set of significant lines (`golden_preamble` sorts them; the separate ordering tests lock emission order): `tests/fixtures/golden/page_template_{letterhead_title,logo,empty_header,faktura}.tex`, compared in `tests/test_block_engine.py:1948-1996` and `tests/test_renderer.py:1312-1325`. Every fragment change updates its golden in the same commit.
- `klartex/server/render.py:273` forwards `ValidationError.absolute_path` as `detail.path`. An unknown key under `additionalProperties: false` is reported on the containing object, so a top-level `page_numbers` yields `detail.path == ["page_template"]` with the key named in the message.
- `klartex templates` (`cli.py:229`) lists document templates only; nothing on the CLI calls `list_slot_variants()`. The discovery surface for slot settings is `klartex schema _block`.
- `tests/test_pdf_text_layer.py:193-202` asserts `Kallelse till stämma • Sida 1 av 2` on a two-page render — that stays true under `auto`. `:229-240` asserts no `Sida` with both slots empty — unaffected.
- The user-facing prose: `README.md:204` names `page_numbers` among the document-level settings; the module docstring example at `page_templates.py:39` sets `"page_numbers": false` at the top level. Both move to the slot form.
- The consumer swedev/klartex.se is not in this tree; it drives its template editor from the schema. Its follow-up (an issue in that repo) is noted for the user, not created here.

### Where each change lives

**The LaTeX-time test, once, in the class.** `klartex-base.cls` gains `\RequirePackage{refcount}` and one macro, `\kxifpagenumbers{<mode>}{<content>}`: typesets `<content>` when `<mode>` is `on`; when `auto`, only if `\getpagerefnumber{LastPage}>1`; never when `off`. The mode arrives both as a literal (`\kxifpagenumbers{auto}` from the fragment) and as a macro (`\kxifpagenumbers{\kxf@pagenumbers}` from the sty), so the comparison must fully expand its argument first — `\ifstrequal` from etoolbox does not, `\edef` the argument into a scratch macro and compare with `\ifdefstring`, or use `\ifnum\pdfstrcmp`-style expansion; lock both call forms with a rendered test. Placing it in the class (beside the other shared chrome macros: `\kx@hdrline`, the contract macros) lets the `pagenumber` fragment, `klartex-footer.sty` and a custom slot source all use the same conditional. On xelatex's first run `LastPage` is undefined and `\getpagerefnumber` yields 0, so `auto` prints nothing on run one and the right thing on run two — the renderer always runs twice (`renderer.py`), and this is how the columns footer already behaves.

**The `pagenumber` fragment owns its own blanking.** `pagenumber.tex.jinja` renders `\fancyfoot[C]{…}` unconditionally and wraps the page-number text in `\kxifpagenumbers{\VAR{page_numbers}}{…}`. With `title` set the title prints unconditionally and the ` • ` separator moves inside the conditional, so a one-page titled document under `auto` shows the title alone, and `off` with `title` shows the title alone — the setting governs the page number, not the footer (decision 4). The composition's `\fancyfoot[C]{}` arm (`_page_template.tex.jinja:39-43`) is removed; the footer arm becomes `\VAR{page_template.footer_fragment}` for every predefined variant.

**The `columns` footer's keyval becomes the mode string.** `klartex-footer.sty`: `\def\kxf@pagenumbers{auto}` replaces the `\newif`; `\define@key{kxfooter}{pagenumbers}{\def\kxf@pagenumbers{#1}}`; the block at `:182-189` becomes `\kxifpagenumbers{\kxf@pagenumbers}{\par\vspace{4pt}\makebox…}`. The `\RequirePackage{refcount}` moves to the class. `columns.tex.jinja:7` emits `pagenumbers=\VAR{page_numbers}`. The package header comment documents `pagenumbers (auto|on|off)`.

**The slot model.** In `page_templates.py`:
- `PAGE_NUMBERS_SETTING = {"type": "string", "enum": ["auto", "on", "off"], "default": "auto", "description": …}` beside `TITLE_SETTING`, describing all three values and that `auto` means "only when the document has more than one page".
- Both `FOOTER_VARIANTS` entries add `"page_numbers": PAGE_NUMBERS_SETTING` to `settings`. The `columns` description drops "and page numbers when the document runs past one page" in favour of "and page numbers per page_numbers"; `pagenumber`'s description says the number is shown per `page_numbers`. `_slot_schema`, `list_slot_variants()` and the injected schema pick the setting up with no further change.
- `DOCUMENT_SETTINGS` loses `page_numbers`; `PAGE_TEMPLATE_KEYS` shrinks accordingly, so the loader's existing unknown-key check rejects a top-level `page_numbers` with its normal message, and the generated schema rejects it through `additionalProperties: false`.
- `PageTemplate.page_numbers` (the field) and its resolution in `load_page_template` go. `SlotSpec` gains a `page_numbers` property returning `settings.get("page_numbers", "auto")` (the mode a predefined footer renders with; `"auto"` for the bare variant form). `footer_fragment` passes `"page_numbers": self.footer.page_numbers` into the fragment context instead of the document-level value.
- `_check_settings` gains value validation for enum settings: when a variant setting's schema has `enum`, a value outside it raises `ValueError` naming the slot, variant, setting and the allowed values — so `{"variant": "pagenumber", "page_numbers": true}` fails in the loader as well as in the schema (a boolean is exactly the mistake a caller used to the old key will make).
- Module docstring example: `"page_numbers": false` moves to `"footer": {"variant": "columns", "page_numbers": "off", "fields": {…}}`.

**Docs.** `README.md:204` drops `page_numbers` from the document-level list and gains a short paragraph under the slot section: the setting sits on the footer variant, its three values, `auto` default, and that a footer with its own LaTeX owns its page numbers. `CHANGELOG.md` gets an entry under a new unreleased heading: Breaking changes (global key removed, no alias; `pagenumber` footer's one-page default changes from `Sida 1 av 1` to nothing) and New features (tri-state per slot). The `--page-template` help text in `cli.py:82` lists the document-level settings that still apply — it does not mention `page_numbers`, so it is already correct.

**Release dependency, not an implementation blocker.** swedev/klartex.se drives its template editor from this package's schema and is the only producer of `page_template` payloads. If it still emits a top-level `page_numbers` when the release that ships this reaches app.klartex.se, every such render fails with `400 validation_error`. The implementation here is unblocked; the release is gated on a klartex.se change, tracked in an issue in that repo that the user creates or asks for — this plan writes nothing to GitHub. Whether klartex.se emits the key today is not verifiable from this tree; the PR body states the dependency so it is checked before release.

**What stays put.** `first_page_header` (issue #66 owns the chrome-free title page and that key); the header variants (none carries page numbers today — the setting is added to a header variant when one gets page numbers, per the issue); `RECIPE_DEFAULT_SLOTS` and the recipe.yamls (they resolve to `auto`); the `lastpage` package and `\pageref{LastPage}` text; the server (`klartex/server/render.py` passes `page_template` through untouched, and its error mapping already turns the loader's `ValueError` into `400 input_error`).

## Steps

1. **Red tests, loader** — `tests/test_page_templates.py`: replace `test_page_numbers_override` / the `page_numbers` assertions in `TestDefaults` and `test_multiple_overrides` with: bare `"pagenumber"` and `RECIPE_DEFAULT_SLOTS` resolve `footer.page_numbers == "auto"`; `{"footer": {"variant": "pagenumber", "page_numbers": "off"}}` and `{"footer": {"variant": "columns", "page_numbers": "on", "fields": {…}}}` resolve to their mode; top-level `{"page_numbers": False}` raises the unknown-key `ValueError` naming `page_numbers`; `{"footer": {"variant": "pagenumber", "page_numbers": True}}` and `"sometimes"` raise a `ValueError` listing `auto, on, off`; `{"footer": {"variant": "pagenumber", "title": True, "page_numbers": "off"}}` is accepted (both settings coexist). Replace `test_footer_page_numbers_is_not_a_setting` with the accept case.
2. **Red tests, schema** — `tests/test_schemas.py`: the boolean slot case `{"footer": {"variant": "pagenumber", "page_numbers": True}}` is already in the reject list (`:343`) and stays there — a boolean remains wrong, now by type instead of by key. Add accept cases `{"footer": {"variant": "pagenumber", "page_numbers": "auto"}}`, `{"footer": {"variant": "pagenumber", "title": True, "page_numbers": "off"}}`, `{"footer": {"variant": "columns", "page_numbers": "off"}}`, and reject cases `{"page_numbers": True}`, `{"page_numbers": "auto"}` (top level), `{"footer": {"variant": "pagenumber", "page_numbers": "sometimes"}}`, `{"header": {"variant": "logo", "page_numbers": "on"}}` (no header variant carries it). Assert the generated schema's `footer` subtree exposes the enum on both variant forms, that `properties` of `page_template` has no `page_numbers` key, and that `list_slot_variants()["footer"]` lists `page_numbers` among both variants' settings.
3. **Red tests, composition** — `tests/test_block_engine.py`: `test_page_template_object` (`:41-49`) switches to the slot form and asserts `footer.page_numbers == "off"`; `test_custom_footer_owns_page_numbers` (`:2114`) and `test_page_numbers_false_emits_no_empty_footer` (`:2274`) become "a custom footer source is emitted verbatim and no `\kxifpagenumbers` appears for it"; new assertions that the `pagenumber` footer emits `\kxifpagenumbers{auto}` by default, `\kxifpagenumbers{off}` when set, and that `\fancyfoot[C]{}` is never emitted by the composition; the `columns` footer emits `pagenumbers=on` / `pagenumbers=auto` in its `\kxfooter` call. `tests/test_server.py`: a top-level `page_numbers` maps to `400 validation_error` with `detail.path == ["page_template"]` and `page_numbers` in the message.
4. **Red tests, rendered PDF** — `tests/test_pdf_text_layer.py`, the full matrix on both variants. `pagenumber`: one page under default `auto` → no `Sida`; one page with `"on"` → `Sida 1 av 1`; two pages with `"off"` → no `Sida` on either page; one page with `title` under `auto` → the title, no `•`; `test_title_footer_carries_the_title_and_page_count` stays as the `auto` two-page case. `columns` (block engine, `fields` with a company): one page under `auto` → no `Sida`; two pages under `auto` → `Sida 1 av 2`; two pages with `"off"` → no `Sida`; one page with `"on"` → `Sida 1 av 1`. Plus one faktura render (recipe path, derived footer) with `page_template.footer: {"variant": "columns", "page_numbers": "on"}` → `Sida 1 av 1`, proving the setting survives the `fields_from` merge.
5. **Model and loader** — `page_templates.py`: `PAGE_NUMBERS_SETTING`, the two variant entries and descriptions, remove from `DOCUMENT_SETTINGS`, `SlotSpec.page_numbers`, drop `PageTemplate.page_numbers`, update `footer_fragment` to pass the slot's mode string, enum validation in `_check_settings`, module docstring example. From here the fragments receive `"auto" | "on" | "off"`, never a boolean.
6. **Class** — `klartex-base.cls`: `\RequirePackage{refcount}`, define `\kxifpagenumbers` with a comment stating its contract (three modes, expansion of the mode argument, first-run behaviour). Move the `\RequirePackage{refcount}` out of `klartex-footer.sty`.
7. **Fragments and sty** — `pagenumber.tex.jinja`, `columns.tex.jinja`, `klartex-footer.sty` as described above.
8. **Composition** — `_page_template.tex.jinja`: remove the `pagenumber`/`page_numbers` arm; update the emission-order comment (footer slot: "custom source or the variant fragment — a fragment owns its own page-number conditional"). Steps 5–8 are one atomic change: the tree renders correctly only with all four in place, so they land in one commit.
9. **Goldens** — regenerate `page_template_letterhead_title.tex`, `page_template_logo.tex`, `page_template_empty_header.tex` (new `\kxifpagenumbers{auto}` line in the footer) and `page_template_faktura.tex` (`pagenumbers=auto`), reading each diff to confirm it is exactly the intended change.
10. **Docs** — `README.md` slot section and `:204`, `CHANGELOG.md` entry.
11. **Full suite** — `pytest -n auto`; then render `tests/fixtures/block_kallelse.json` and a faktura fixture with the repo code (not the stale `klartex` shim on PATH) and check the footer text with `pdftotext` for the combinations in step 4.

## Design Decisions

### 1. Tri-state as the string enum `"auto" | "on" | "off"`, default `"auto"`, on both footer variants

Options: (a) string enum as the issue names it; (b) `true | false | "auto"` (boolean kept as two of the states); (c) an object like `{"show": "auto"}`.

Decision: (a). **Provenance:** user decision per the issue text ("`auto` (default …) / `on` / `off`", both `pagenumber` and `columns` "get the auto/on/off setting among their slot settings"). The issue is agent-written, so this is the claimed decision; the shape is unambiguous and (b) would keep the very boolean the issue retires.

Consequence if wrong: a renamed enum value is a one-line change in the model plus the schema's own tests; nothing is stored.

### 2. The setting is named `page_numbers` on the slot

Options: (a) `page_numbers` — the key the global setting had and the one #63 reserved on the footer slot object; (b) `pagenumbers` matching the `\kxfooter` keyval; (c) `numbering`.

Decision: (a). **Provenance:** agent judgment. The issue names the *values* but not the key; (a) is the wording closest to the issue ("the global `page_numbers` field … the footer slot's setting"), and the loader has rejected exactly this key on the footer slot since #63 as a placeholder for this issue. What would make (b) right: a wish to keep JSON keys and `\kxfooter` keyvals identical — but the model already maps `org_number → orgnr` and `f_tax → ftax`, so that identity is not a convention.

Consequence if wrong: rename in the model, schema tests and README; bounded.

### 3. The global key is removed outright — no alias

Options: (a) remove; top-level `page_numbers` is an unknown key. (b) keep it as an alias writing into the footer slot's setting.

Decision: (a). **Provenance:** existing convention — the user's 2026-08-30 ruling "ingen bakåtkompabilitet för ett paket bara jag använder" (memory `no-backward-compat`), applied to exactly this kind of alias in #80's "no aliases" rework (CHANGELOG 0.17.0). The issue leaves the alias question to planning; this settles it. Breaking change under `Breaking changes`, and klartex.se gets a follow-up issue (the user creates it, or asks for it — no GitHub writes from this plan).

Consequence if wrong: an alias can be added later in the loader in a few lines; the reverse (removing an alias once shipped) costs a second breaking change, so removing now is the cheaper direction to be wrong in.

### 4. `auto` applies to the `pagenumber` footer too — one-page documents lose `Sida 1 av 1` by default

Options: (a) `auto` default on both variants, as the issue says, accepting that the `pagenumber` footer's one-page output changes; (b) default `on` for `pagenumber` (preserving its current output) and `auto` for `columns` (preserving its); (c) default `auto` everywhere but make the `pagenumber` fragment keep printing on one page (i.e. `auto` meaning different things per variant).

Decision: (a). **Provenance:** user decision per the issue ("`auto` (default — render page numbers only when the document has more than one page …)") — with the correction that the issue's "today's implicit rule made into a visible choice" describes the columns footer only. (c) would make one word mean two things; (b) would give the two variants different defaults for the same setting, which the template editor would then have to explain. The issue's `on` value exists precisely to ask for `Sida 1 av 1` when wanted.

Consequence if wrong: a default flip in one dict entry and one golden; the change is visible in every one-page protokoll/block document until then, so it is called out in the CHANGELOG's Breaking changes and in this plan's summary for the user to veto.

### 5. With `title` set, the title prints regardless of the page-number mode; the separator belongs to the number

Options: (a) title unconditional, `•` and the number inside the conditional; (b) the whole footer line (title included) subject to the mode, as `page_numbers: false` blanks it today; (c) reject `title: true` together with `off`.

Decision: (a). **Provenance:** agent judgment. The setting is named for page numbers and the issue calls the title "optional document title" content of the variant; a `pagenumber` footer with `title` is the recipes' default, and a one-page protokoll losing its footer title because its page number is suppressed would be the surprising reading. What would make (b) right: a decision that `pagenumber` without a number is meaningless and should collapse to an empty footer — then `off` + no title already yields that, and `off` + title becomes the only case that differs.

Consequence if wrong: a two-token move inside one fragment and its three goldens; bounded.

### 6. One shared conditional `\kxifpagenumbers` in `klartex-base.cls`, used by the fragment and the sty

Options: (a) shared macro in the class; (b) duplicate the `\ifnum\getpagerefnumber{LastPage}>1` test in the fragment and keep the sty's copy; (c) decide in Python and emit different LaTeX per mode.

Decision: (a). **Provenance:** agent judgment, following the existing convention that shared chrome helpers live in the class (`\kx@hdrline`, the contract macros, `\ifkxfooterlabelmissing` "declared here … so the meta-template can set it without knowing whether that package is loaded"). (c) is impossible for `auto`: the page count is known only at LaTeX time. What would make (b) right: nothing structural — it is just two copies of the same test.

Consequence if wrong: the macro is a dozen lines and can be inlined back; bounded. Note that a custom slot source can call `\kxifpagenumbers` too, which is a small bonus rather than a contract to document heavily.

### 7. The loader validates enum-typed settings, not only setting keys

Options: (a) generic: `_check_settings` rejects a value outside a setting's `enum`; (b) a `page_numbers`-specific check; (c) rely on the schema alone.

Decision: (a). **Provenance:** agent judgment, in line with the loader's existing stance for `margins` and `font` ("`load_page_template` is reachable from callers that never ran the JSON Schema, so the loader states the contract itself", `page_templates.py:_check_font` docstring). A boolean here is the most likely migration mistake, and the message can list the three values. Booleans (`title`) get no new check — `TITLE_SETTING` has no `enum` — which keeps this change scoped.

Consequence if wrong: a redundant check that the schema also performs; nothing is lost by removing it.

### 8. No header variant gets the setting now

Options: (a) add `page_numbers` only where a variant actually renders page numbers (both footers); (b) add it to every variant of both slots for symmetry.

Decision: (a). **Provenance:** user decision per the issue ("a future header variant with page numbers gets the same setting on its slot") — the setting follows the content. (b) would offer a knob with no effect on `letterhead`/`logo`, and the schema test in step 2 locks that out.

Consequence if wrong: adding a setting to a variant is one table entry.

## Risks

- **Visible default change on one-page documents** (decision 4): every block-engine and protokoll/årsredovisnings-style document that fits on one page stops printing `Sida 1 av 1`. Correct per the issue, but it is the kind of change a user notices in a PDF before reading a changelog — surfaced in the CHANGELOG's Breaking changes and in the PR body.
- **First-run undefined `LastPage`.** `auto` relies on the second xelatex run, as the columns footer already does. A single-run caller (none exists in the repo — `renderer._compile_tex` runs twice) would silently get no page numbers under `auto`; the class comment states this.
- **Consumer break (release dependency).** klartex.se sends the payload this package validates; a top-level `page_numbers` it still emits fails validation (`400 validation_error`, `detail.path == ["page_template"]`) after the release that ships this. Not an implementation blocker — the PR can merge to `main` — but the release is gated on the klartex.se change, which needs an issue in that repo; flagged for the user, not created here.
- **`\kxifpagenumbers` argument expansion.** The macro is called with a literal from the fragment and with `\kxf@pagenumbers` from the sty; a comparison that does not expand its argument silently treats the macro form as "neither on nor auto" and the columns footer loses its page numbers. The rendered `columns` cases in step 4 catch that.
- **Golden churn overlapping open work.** No other open plan touches `pagenumber.tex.jinja`, `columns.tex.jinja` or the composition's footer arm. #66 (title page chrome) and #62 (footer layout) will edit neighbouring lines of `_page_template.tex.jinja` / `klartex-footer.sty` when planned; land this first, it is small.
- **`refcount` in the minimal CI TeX Live.** Moving the `\RequirePackage` to the class loads it for every render, not only the columns footer. It is already present (faktura renders in CI), and `.github/tl_packages` is derived from the recorder, so a CI failure here would be loud, not silent.

## Test Plan

- `pytest tests/test_page_templates.py tests/test_schemas.py` — the loader and schema cases in steps 1–2 (fast, no TeX).
- `pytest tests/test_block_engine.py -k "page_template or golden or PageTemplate"` — composition output and the three goldens; `pytest tests/test_renderer.py -k golden` for the faktura golden.
- `pytest tests/test_pdf_text_layer.py` — the `pdftotext` matrix from step 4: `auto`/`on`/`off` on both variants, one- and two-page, plus the faktura case through the recipe path.
- `pytest tests/test_server.py` — unchanged contract; a top-level `page_numbers` maps to `400 validation_error` with `detail.path == ["page_template"]` and the key named in the message.
- `pytest -n auto` — full suite; the CI skip guard means every xelatex test must run locally too.
- Manual: render `tests/fixtures/block_kallelse.json` (one page, default) and confirm with `pdftotext` that no `Sida` appears; render with `"footer": {"variant": "pagenumber", "page_numbers": "on"}` and confirm `Sida 1 av 1`; `klartex schema _block | jq '.properties.page_template.properties | keys'` shows no `page_numbers`, and the footer `oneOf` carries the enum on both object forms (`klartex schema _block` is the discovery surface for slot settings — `klartex templates` lists document templates only).
