# Plan: Issue #65 — Expose page margins on the page-template surface

## Goal

Add a structured `margins` setting to the `page_template` surface so callers can set page margins per document, on both render paths, without custom LaTeX. Margins are page chrome in the same category as header, footer, fonts and colors (user decision, template-editor design 2026-08-29), so they belong on the page-template surface — and the issue's defining constraint is that they must be specified **in interplay with the chrome geometry**, not as four raw `\geometry` numbers, because the built-in chrome already manipulates geometry dynamically.

The geometry as it exists on `main`, verified before planning:

- `klartex/cls/klartex-base.cls:14-33` loads `geometry` with `left=\kxsidemargin, right=\kxsidemargin, top=0.9cm, bottom=2cm, includehead, headheight=1.2cm, headsep=1.3cm, footskip=1cm`. `\kxsidemargin` defaults to `3cm`; the `narrowmargins` class option (faktura/kvitto, via `document.class_options` in their `recipe.yaml`) tightens it to `2cm` and `\kxreclaimtop` from `2cm` to `1.7cm`. With a header, body text therefore starts at `0.9 + 1.2 + 1.3 = 3.4cm` from the paper edge.
- The header-space reclaim (`page_templates.py:252`, `_RECLAIM`) fires when the header slot is empty or a predefined variant ends up with no content: `\geometry{top=\kxreclaimtop, headheight=0pt, headsep=0pt, includehead=false}`. It is emitted **after** both slots (`_page_template.tex.jinja`, step 4) because its `\ifdefempty` tests must see the final value of the contract macros — a custom footer source may still `\renewcommand{\orgname}`. So which top-geometry regime applies is decided at LaTeX time, not in Python.
- Document-level settings (`font`, `header_font`, `diff_style` in `DOCUMENT_SETTINGS`, `page_templates.py:225`) apply in every mode, including alongside custom slot sources, and are emitted first (step 1) so a custom source's own preamble wins.

There is no margins knob anywhere on the surface: the only margin variation today is the internal `narrowmargins` class option, which recipe authors set — not payload authors.

## Approach

### Provenance summary

- **User decision (issue #65 body, template-editor design 2026-08-29):** margins go on the structured `page_template` surface; they must compose with the chrome geometry rather than being four raw numbers; per-template *block* styling stays out of scope.
- **Existing conventions (with location):** document-level settings live in `DOCUMENT_SETTINGS` and apply in every mode, emitted first in the composition (`page_templates.py:225`, `_page_template.tex.jinja`); the reclaim's late LaTeX-time binding via `\kxreclaimtop` (`page_templates.py:252`, `klartex-base.cls:15`); the schema subtree is generated from the slot model, schema files carry only a placeholder (`page_template_schema`, `registry.py:43`); `FILENAME_PATTERN`-style validation-by-pattern for values that reach LaTeX unescaped-critical positions (`page_templates.py:96`); English schema descriptions (`CLAUDE.md`).
- **Agent judgment (D1–D8 below — flag in the PR body as open to question):** the user-facing meaning of the values (text-block margins), the key set and JSON shape, dimension-string typing, the dual-regime `top` implementation, the "applies alongside custom sources" rule, the conditional minimum-`top` validation, leaving `narrowmargins` in place as the recipe default, and late-binding the columns footer's bottom geometry through macros so `margins.bottom` wins over its automatic enlargement.

### The margins model

**D1 — the values mean text-block margins.** `margins.{top,bottom,left,right}` is the distance from the paper edge to the **body text block** on each side. This is the number a template-editor user reasons about, and it stays meaningful no matter what the slots contain — the chrome adapts to it, which is exactly the "interplay" the issue demands. Alternatives considered and rejected:

- *Raw geometry passthrough* (`headsep`, `headheight`, `includehead`, …): leaks the chrome implementation that the slot model deliberately owns; the values silently change meaning whenever a slot changes (empty header reclaims; #67/#62 will keep reshaping chrome), which is the issue's stated anti-goal.
- *Chrome-relative distances* ("gap between header and text"): the reference point disappears when the header is empty, so the same payload value means different things per document.
- *Slot-level margins*: margins are one page geometry shared by both slots, not slot content — same category as `font`, so document-level.

**D2 — shape and location.** A new entry in `DOCUMENT_SETTINGS`:

```json
"page_template": {
  "margins": {"top": "2.5cm", "bottom": "2cm", "left": "2cm", "right": "2cm"}
}
```

An object with four optional keys; each key applies independently (only `left` is fine). It rides the existing machinery for free: `PAGE_TEMPLATE_KEYS` derives from `tuple(DOCUMENT_SETTINGS)`, and `page_template_schema()` injects the subtree into every template schema, so `klartex schema _block` and all seven recipe schemas pick it up with no schema-file edits.

**D3 — values are LaTeX dimension strings, strictly validated.** Pattern `^[0-9]+(\.[0-9]+)?(cm|mm|pt|in)$` (module constant `DIMENSION_PATTERN`, next to `FILENAME_PATTERN`). No bare numbers meaning implicit cm — explicit units are unambiguous and match every LaTeX example a user will meet; the four units are the full supported set (no `em`/`ex` — font-relative units have no stable meaning before `\setmainfont` resolves). The pattern admits no LaTeX special characters and survives `escape_data()` untouched, so the values are injection-safe in the `\geometry` call. The loader enforces the same pattern at runtime (`_check_margins`) so the API path without JSON-schema validation gets the same errors. Contract edges, decided here: `margins: null` and `margins: {}` both mean "no margins given" (same treatment as an absent key — the loader normalises `None` to `{}`, and the generated schema types `margins` as object-or-null so schema validation accepts the same payloads the loader does); zero values (`"0cm"`) structurally pass — LaTeX accepts them and clamping aesthetics is not the loader's job (a zero `top` still trips the D6 check when a header renders; the schema description notes that extreme values can clip chrome).

**D4 — `top` composes with the header chrome via both regimes at once.** The two top-geometry regimes are decided at LaTeX time (see Goal), so the emission covers both and lets the existing late binding pick:

- *Header renders:* the header band stays anchored where it is today (`top=0.9cm`, `headheight=1.2cm` untouched) and the header–text gap absorbs the change: `headsep=\dimexpr <top>-2.1cm\relax` in the emitted `\geometry` call. `2.1cm` = the band bottom (`0.9cm + 1.2cm`); it lives as a named module constant with a comment pointing at `klartex-base.cls:27,30`, and a cls-lock test keeps the two files in sync.
- *Header reclaimed:* `\renewcommand{\kxreclaimtop}{<top>}`, emitted with the settings in step 1; the reclaim block in step 4 then applies `top=\kxreclaimtop` — the user's value — through the existing macro.

Both are always emitted when `top` is set; whichever branch the `\ifdefempty` tests select at the end of the preamble wins, and Python never has to guess whether a custom footer source populated `\orgname`. (`\dimexpr` is eTeX, unconditionally available under XeLaTeX; computing the subtraction in Python and emitting a plain dimension is an acceptable fallback if geometry's keyval parsing ever balks — the validation already parses the value.)

`bottom`, `left`, `right` are plain `\geometry{bottom=…, left=…, right=…}` keys; the footer baseline sits `footskip` below the text bottom inside the bottom margin (1cm for the page-number footer — the columns footer's own geometry is D8). One fancyhdr caveat for the side keys: `\headwidth` does not reliably track a `\textwidth` change made after the class loaded fancyhdr, so when `left`/`right` is set the emission appends `\setlength{\headwidth}{\textwidth}` after the `\geometry` call to keep the header/footer band aligned with the new text block. (Verify against the render environment's fancyhdr during implementation — if it demonstrably auto-tracks, the line is harmless anyway; keep it.)

Concretely, `PageTemplate` grows a `margins: dict` field and a `margin_setup` property that renders, for the keys present, one `\geometry{…}` call plus the `\kxreclaimtop` renewal — e.g. for all four keys:

```latex
\renewcommand{\kxreclaimtop}{2.5cm}
\geometry{left=2cm, right=2cm, bottom=2cm, headsep=\dimexpr 2.5cm-2.1cm\relax}
\setlength{\headwidth}{\textwidth}
```

**D5 — margins apply in every mode, like the other document-level settings.** Emitted in step 1 of `_page_template.tex.jinja`, before either slot, so a custom slot source that emits its own `\geometry` wins — the same precedence `font` has. A custom header source also keeps owning its reclaim behaviour (its `header_reclaim` is empty), so with a custom header, `margins.top` still emits its two pieces but the source's own geometry has the last word. Documented in the schema description and README.

**D6 — minimum-`top` validation, only where Python knows it applies.** A `top` at or below `2.1cm` makes `headsep` zero/negative when a header actually renders. The loader raises `ValueError` for `top` **≤** `2.1cm` — strictly-greater is required, since equality means `headsep=0pt`, header butted against the text, which is never what a caller meant — **only when the resolved header will render as far as Python can tell** (`header.is_predefined` and `header_macros` non-empty; both `letterhead` and `logo` go through `header_macros`, so both variants are covered; `header.is_custom` is excluded — a custom source owns its geometry). An empty or content-less predefined header takes any positive `top` (the reclaim regime; note `narrowmargins`' own reclaim top is `1.7cm`, so small values are legitimate there). The one unguardable edge — a custom *footer* source that `\renewcommand`s `\orgname` and thereby un-reclaims a header under a small `top` — is documented, not validated. Unit comparison converts to TeX points with the exact factors (`pt=1`, `in=72.27`, `cm=72.27/2.54`, `mm=72.27/25.4`) computed as `Fraction`s, so the boundary comparison has no float wobble.

**D7 — `narrowmargins` stays.** faktura/kvitto keep their class option as the recipe *default*; an explicit `margins` in the payload is emitted after `\documentclass` and overrides it per key. Re-expressing the recipe defaults through the margins surface (and retiring the class option) is a possible follow-up, not this issue — it would change `recipe.yaml`'s contract and the cls-lock tests for no user-visible gain now.

**D8 — `margins.bottom` composes with the columns footer through late-bound macros.** `\kxfooter` (klartex-footer.sty:96) forces `\geometry{bottom=3.6cm, footskip=2.6cm}` to make room for its multi-line band, and it runs *after* the step-1 margin emission — both for the `columns` footer slot and for the recipe-level `data.footer` that `_recipe_base.tex.jinja` emits after the include. Left alone it would silently override the user's `bottom`, breaking the text-block-margin contract. Fix with the same late-binding pattern as `\kxreclaimtop`: the sty gains `\providecommand{\kxfooterbottom}{3.6cm}` / `\providecommand{\kxfooterfootskip}{2.6cm}` and applies `\geometry{bottom=\kxfooterbottom, footskip=\kxfooterfootskip}`; when `margins.bottom` is set, `margin_setup` also emits `\renewcommand{\kxfooterbottom}{<bottom>}` and `\renewcommand{\kxfooterfootskip}{\dimexpr <bottom>-1cm\relax}` — preserving today's `bottom − footskip = 1cm` relationship, so the band's bottom edge keeps the same clearance. A `bottom` too small for the band clips the footer (documented in Risks, not validated — the band height is content-dependent). Output for default payloads is byte-identical: the provided defaults are today's literals.

**What stays put.** `headheight`/the header band size (a taller-header knob is not this issue), `footskip`, per-block spacing (`block_settings`, explicitly out of scope per the issue), the reclaim mechanism and its emission order, `first_page_header`/`page_numbers` (#66/#67), typography (#61), footer layout (#62).

### File map

- `klartex/page_templates.py` — `DIMENSION_PATTERN`; `MARGIN_KEYS = ("top", "bottom", "left", "right")`; header-band constant; `margins` entry in `DOCUMENT_SETTINGS` (object schema, `additionalProperties: false`, per-key descriptions stating the text-block meaning and the header interplay); `_check_margins()` called from `load_page_template`; `margins` field + `margin_setup` property on `PageTemplate`; the D6 check after both slots resolve.
- `klartex/templates/_page_template.tex.jinja` — emit `\VAR{page_template.margin_setup}` in step 1, after the font/diff settings.
- `klartex/cls/klartex-footer.sty` — the two `\providecommand`ed bottom-geometry macros replacing the hardcoded `\geometry{bottom=3.6cm, footskip=2.6cm}` (D8).
- `tests/test_page_templates.py` — loader unit tests (validation + `margin_setup` output).
- `tests/test_block_engine.py` — tex-level composition locks (both regimes, ordering, custom-source precedence) + one xelatex compile.
- `tests/test_renderer.py` — cls↔Python sync test: parse `top=…` and `headheight=…` out of `klartex-base.cls`'s geometry block and assert their **sum equals the Python band constant** (asserting the literals alone would let all three values drift apart while passing); recipe-path test (faktura + margins).
- `tests/test_schemas.py` — mandatory: assert the generated `page_template` subtree carries `margins` with the four keys and the pattern (this is new public schema surface, not an optional check). `tests/test_agent_cli.py` only if its assertions enumerate settings explicitly.
- `tests/test_pdf_text_layer.py` (or a small dedicated geometry test beside it) — measurable layout checks via `pdftotext -bbox`, **delta-based** (a first word's `xMin`/`yMin` includes `\topskip` and font metrics, so absolute coordinates are brittle): render the same payload with and without `margins`, and assert the first body word moved by exactly the margin delta — horizontally for `left`, vertically for `top`, once with a rendering letterhead header and once with `header: null` — proving both regimes place the text where the contract says, not merely that the syntax compiles.
- `README.md`, `README.en.md` — margins subsection under the page-template docs; `CLAUDE.md` — one sentence in the page-templates paragraph (document-level settings list).
- `CHANGELOG.md` — at release time per the repo's release flow, not in this branch unless asked.

## Steps

1. **Model + validation in `page_templates.py`.** Add `DIMENSION_PATTERN`, `MARGIN_KEYS`, the header-band constant with its cls cross-reference comment, and the `margins` entry in `DOCUMENT_SETTINGS` with full descriptions (text-block meaning, per-key behaviour, custom-source precedence, the `top` minimum). Add `_check_margins(margins)` — reject non-object values, unknown keys, and values failing the pattern, with error messages naming the allowed keys/format in the established `ValueError` style.
2. **Loader + `PageTemplate`.** Read `overrides.get("margins")` in `load_page_template` (normalising `None` to `{}` per D3), validate, store as `margins` on `PageTemplate` (default `{}`). After both slots are resolved, apply the D6 minimum-`top` check. Implement `margin_setup`: empty string when no margins; else the `\kxreclaimtop` renewal (when `top` set), the `\kxfooterbottom`/`\kxfooterfootskip` renewals (when `bottom` set, D8), one `\geometry{…}` call with the keys present (`left`, `right`, `bottom` verbatim; `top` as the `headsep` dimexpr), and the `\headwidth` sync line when a side key is set (D4).
3. **D8 in `klartex-footer.sty`** — the two `\providecommand`s and the macro-based `\geometry` call; verify byte-identical output for a margin-less columns-footer render (the goldens/tex assertions catch drift).
4. **Composition.** Emit `margin_setup` in `_page_template.tex.jinja` step 1, guarded like the other settings, and extend the step-order comment at the top of the file.
5. **Unit tests** (`tests/test_page_templates.py`): defaults (no `margins`, `margins: null`, `margins: {}` → empty `margin_setup`, no `\geometry` in output); each validation error (non-object, unknown key, `"2,5cm"`, `"2.5"`, `"2.5em"`, negative impossible by pattern); `"0cm"` accepted for a side key; `top` ≤ 2.1cm (including exactly `"2.1cm"` and the cross-unit boundary `"21mm"`) rejected with a letterhead header carrying `org_name` and with a `logo` header carrying `logo`, accepted with `header: null` and with a content-less letterhead; `margin_setup` exact output for single-key and all-key inputs, including the `\headwidth` sync appearing only when a side key is set.
6. **Tex-level tests** (`tests/test_block_engine.py`, `TestPageTemplateSlots` style): with a rendering header, `headsep=\dimexpr` present and `\renewcommand{\kxreclaimtop}` before the reclaim block; with `header: null`, the reclaim resolves the user's top through `\kxreclaimtop`; margins emitted before a custom `header_source`; `left`/`right`/`bottom` pass through verbatim; with `bottom` set, the `\kxfooterbottom`/`\kxfooterfootskip` renewals appear before the footer slot (D8), and without `margins` they are absent. One `@pytest.mark.skipif(not HAS_XELATEX)` compile of a payload with all four margins and a columns footer.
7. **Recipe + cls↔Python sync tests** (`tests/test_renderer.py`): faktura render with `margins` in `data.page_template` emits the geometry after `\documentclass[narrowmargins]`; the sum-comparison test from the file map (parse the cls geometry values, compare their sum to the imported Python constant).
8. **Measurable layout test** (`tests/test_pdf_text_layer.py` or beside it): the delta-based `pdftotext -bbox` checks from the file map — the body text moves by exactly the margin delta in both top regimes.
9. **Schema surface.** Assert in `tests/test_schemas.py` that the generated `page_template` subtree includes `margins` (object-or-null, keys + pattern) and that a payload with `margins: null` passes schema validation; adjust `tests/test_agent_cli.py` only if it enumerates settings explicitly. Add `margins` to the canonical example only if the example payload enumerates page-template settings today — don't force it in.
10. **Docs.** README/README.en.md page-template sections + the `CLAUDE.md` page-templates paragraph.
11. **Full suite** (`pytest -n auto`) with xelatex, as CI will run it.

## Risks

- **Geometry interplay regressions.** The reclaim override order (settings → slots → reclaim) is load-bearing; emitting the `\kxreclaimtop` renewal anywhere after step 4's reclaim would break the empty-header regime. Locked by the step-5 ordering tests.
- **Constant drift.** The Python-side `2.1cm` mirrors `top=0.9cm + headheight=1.2cm` in the cls; the extended cls-lock test turns silent drift into a test failure.
- **Small `bottom` vs. any footer.** Every fancyhdr footer hangs `footskip` (1cm) below the text block — a `bottom` under ~1cm clips even the plain page-number line, and the multi-line `columns` footer needs more still. Not validated (the footer's height is content-dependent and zero margins are a legitimate edge); documented in the schema description as "leave room for the footer". Same class of risk as today's fixed geometry, now merely reachable.
- **Custom-source expectations.** A custom slot source that assumed klartex's fixed geometry now renders under user margins when the payload sets them (settings precede sources, source wins if it emits its own `\geometry`). Consistent with how `font` already behaves; documented.
- **Sibling issues touching the same surface.** #61 (typography) will add more `DOCUMENT_SETTINGS` entries, #67 moves `page_numbers`, #62 reshapes the footer, #79 moves faktura/kvitto's top-level `footer` into the footer slot (merge-coordination overlap in the same files, not a blocker), #85 may reinstate a whole-page source (whose interaction with document-level settings is that issue's planning question), #84 fixes letterhead column layout (wider text under narrow side margins slightly shifts its symptoms, not its cause). None has an open plan; no file conflicts today, but land order matters for merge friction in `page_templates.py`.
- Consumer `swedev/klartex.se` is unaffected until it chooses to send `margins`; nothing existing changes shape (additive key, no defaults change).

## Test Plan

- `pytest tests/test_page_templates.py` — loader validation and `margin_setup` unit coverage (fast, no TeX).
- `pytest tests/test_block_engine.py -k margin` — tex-level composition locks + the compile test (needs xelatex).
- `pytest tests/test_renderer.py` — cls↔Python band-sum sync test and the faktura/narrowmargins override test.
- `pytest tests/test_pdf_text_layer.py -k margin` — the `pdftotext -bbox` layout check, both top regimes (needs xelatex + poppler).
- `pytest -n auto` — full suite, including all fixture compilations, before the PR.
- Manual smoke: `klartex -d tests/fixtures/block_kallelse.json -o /tmp/out.pdf` with an added `margins` object, once with a letterhead header and once with `header: null`, and eyeball the PDF margins.
