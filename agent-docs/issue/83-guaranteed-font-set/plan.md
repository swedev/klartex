# Plan: Issue #83 — Guaranteed font set in the render environment, and a path for external fonts

## Goal

Callers (and agents reading `klartex schema _block`) can pick a `font` / `header_font` knowing it exists where rendering happens. Concretely:

1. The render environment (`ghcr.io/swedev/klartex-base`) guarantees a curated font set: the Microsoft core fonts it already ships plus a set of open families from Debian packages, verified at image build time and enforced by the release gate.
2. The guaranteed families are enumerated in the `font` / `header_font` JSON Schema descriptions — the agent discovery surface — generated from one constant, not duplicated prose.
3. There is a designed path for external fonts per render call: `font` / `header_font` accept a file form that loads `.ttf`/`.otf` files travelling as assets (already supported by `render(asset_dir=…)` and `klartex serve`'s base64 `assets`).

Provenance: the guaranteed set and the wish for external/Google fonts are a user decision (issue #83, conversation 2026-08-31). The specific package list, the fail-closed release-gate behaviour between phases, the file-form API shape, and the missing-face behaviour below are agent suggestions — open to question, see Risks.

## Approach

Three phases. A and B are the guarantee; C is the external-font path and ships as its own PR.

**Phase A — one PR: constant, schema, tests, Dockerfile, workflows.** A `GUARANTEED_FONTS` tuple in `klartex/page_templates.py` becomes the single source: the `font`/`header_font` descriptions in `DOCUMENT_SETTINGS` enumerate it, and a parametrized xelatex test renders every family. The test follows the existing Georgia pattern exactly (`tests/test_renderer.py::test_header_font_georgia_renders`): skip when the family is absent locally, with a skip reason that avoids the word "xelatex" so the CI skip guard is not tripped, and a `KLARTEX_REQUIRE_FONTS=1` env (replacing `KLARTEX_REQUIRE_GEORGIA` — no alias, per repo policy) that turns the skip into a failure in environments that must render like production. Each parametrized case sets the family as both `font` and `header_font`, so body text and the `\newfontfamily` path are both exercised. `docker/Dockerfile.base` installs the Debian font packages and verifies **every** guaranteed family — the retained Microsoft families included — with exact family-name matches parsed from `fc-list : family` (substring grep would let `Noto Sans Arabic` satisfy a `Noto Sans` check). Both workflows (`base-image.yml` self-test, `publish.yml` release gate) switch to the new env name in the same PR.

Consequence, deliberate: between merging Phase A and completing Phase B, a release would fail its gate — the pinned base does not yet contain the fonts the suite requires. That is fail-closed and correct (the guarantee is not yet in the shipped environment), but Phase B should follow immediately. Releases are user-initiated, so the window is controllable.

**Phase B — release chore, follow-up PR.** Merging Phase A triggers `base-image.yml` (it fires on pushes touching `docker/`), which builds the new base, runs the full suite inside it with `KLARTEX_REQUIRE_FONTS=1`, and pushes a new tag. Then one PR moves the pin — `container.image` in `.github/workflows/publish.yml` **and** `FROM` in `docker/Dockerfile.render`, same commit, copied from the base-image run's step summary — exactly the chore CLAUDE.md documents. The klartex.se consumer gets the guarantee only once it moves its own pin, on its own schedule.

**Phase C — file form for `font` / `header_font`.** Accept an object alongside the string form:

```json
"font": {"file": "Inter-Regular.ttf", "bold": "Inter-Bold.ttf", "italic": "Inter-Italic.ttf", "bold_italic": "Inter-BoldItalic.ttf"}
```

`file` required; the three face keys optional. A face key that is absent is simply not passed to fontspec — no `BoldFont`/`ItalicFont` option, no auto-fake features — so `\textbf`/`\textit` fall back to the regular face (with a fontspec log warning). The schema description states this plainly: supply the face files for the styles the document uses. (Agent judgment, open: the alternatives — synthetic `AutoFakeBold`/`AutoFakeSlant`, or rejecting documents that use unsupplied styles — trade print quality or simplicity for it.)

Filenames validate against `FONT_FILENAME_PATTERN`: `^[A-Za-z0-9][A-Za-z0-9.-]{0,123}\.(ttf|otf)$` — basename only (no path separators), lowercase extension, ≤128 chars, and **no underscore or any other LaTeX special**, so a value passes `escape_data()` byte-identical (the same trick `DIMENSION_PATTERN` and `FILENAME_PATTERN` use; no `_restore_block_types` involvement). Underscores are common in font filenames, so the schema description says to rename such a file — stricter than the server's `ASSET_NAME_RE`, which means everything the schema admits, the endpoint accepts, never the reverse.

Resolution happens in Python, following the `margin_setup` precedent: `load_page_template` turns either form into ready LaTeX (`\setmainfont{Inter-Regular.ttf}[Path=./, BoldFont=…]` for `font`, the `\newfontfamily\kxheaderfontfamily` equivalent for `header_font`), exposed as `font_setup` / `header_font_setup` properties on `PageTemplate`, and `_page_template.tex.jinja` emits those instead of building the commands inline. `Path=./` resolves against xelatex's process cwd, which `_compile_tex` already sets to the asset root — file fonts follow the exact asset-resolution contract explicitly-relative assets have (no fallback chain: the file must be in `asset_dir`, else the caller's cwd). Asset-root resolution is factored into a shared `_resolve_asset_root()` helper used by both `_compile_tex` and a new preflight in `render()`: every referenced face file must exist as a readable regular file under the asset root, else a `ValueError` names the missing file and the contract — instead of a cryptic xelatex failure.

`klartex serve` needs no code change: font files ride the existing `assets` map, and the preflight `ValueError` maps through the endpoint's existing ValueError handling into a structured 4xx. The schema description mentions the endpoint's per-request limits (5 MB/file, 10 files) so callers with heavy font sets are not surprised.

### Curated font list (agent suggestion — the issue explicitly leaves this open)

Keep the MS core fonts (Georgia, Arial, Times New Roman, Verdana, Trebuchet MS, Courier New) and add:

| Debian package | Families guaranteed |
|---|---|
| `fonts-roboto` | Roboto |
| `fonts-lato` | Lato |
| `fonts-open-sans` | Open Sans |
| `fonts-noto-core` | Noto Sans, Noto Serif |
| `fonts-ibm-plex` | IBM Plex Sans, IBM Plex Serif, IBM Plex Mono |
| `fonts-crimson-pro` | Crimson Pro |
| `fonts-inter` | Inter |
| `fonts-ebgaramond` | EB Garamond |

Rationale: covers modern sans (Roboto, Lato, Open Sans, Inter), workhorse serif + sans + mono as one coherent family (IBM Plex), text serifs for long documents (Crimson Pro, EB Garamond, Noto Serif). All are OFL/Apache-licensed Debian packages, tens of MB against a ~7 GB image. The table is a proposal, not a fact: step 1 verifies it inside the actual base image before anything else builds on it.

## Steps

1. **Verify the package list first** (blocks the rest of Phase A): inside `texlive/texlive:latest`, `apt-get install` each proposed package and read the family names from `fc-list : family`. Drop or substitute packages that don't exist in the image's Debian release (watch `fonts-inter` — some releases ship only `fonts-inter-variable`, and variable fonts behave differently under fontspec; if the static package is absent, drop Inter rather than special-case it). The verified family names become `GUARANTEED_FONTS`.
2. **`klartex/page_templates.py`**: add `GUARANTEED_FONTS: tuple[str, ...]`. Rewrite the `font` and `header_font` descriptions in `DOCUMENT_SETTINGS` to (a) enumerate the guaranteed families from the constant, (b) say other fontspec family names work only where locally installed, (c) after Phase C, describe the file form.
3. **`docker/Dockerfile.base`**: add the font packages to the mscorefonts `apt-get install` layer (it already runs `fc-cache -f`). Replace the two `grep -qi` font checks with an exact-match check over every guaranteed family, e.g. a small loop comparing against `fc-list : family` output split on commas — runs per platform at build time, so both architectures are covered.
4. **`tests/test_renderer.py`**: replace `REQUIRE_GEORGIA`/`test_header_font_georgia_renders` with a test parametrized over `GUARANTEED_FONTS` (Georgia stays via the MS core set), each case setting the family as both `font` and `header_font` on a minimal payload that includes `\textbf`/`\textit`-producing inline markup. Keep the skip-reason wording rule; gate on `KLARTEX_REQUIRE_FONTS=1`. ~12 extra xelatex compiles, spread by `pytest -n auto`.
5. **`tests/test_schemas.py`** (or `test_page_templates.py`): assert the generated `_block` schema's `font` description names every family in `GUARANTEED_FONTS` — locks the constant to the discovery surface.
6. **Workflows**: `KLARTEX_REQUIRE_GEORGIA` → `KLARTEX_REQUIRE_FONTS` in `.github/workflows/base-image.yml` (docker-run env in the self-test step) and `.github/workflows/publish.yml` (gate job env), plus the comments that name it.
7. **`README.md`**: extend the render-environment paragraph (Swedish) with the guaranteed families and a pointer to the schema descriptions as the authoritative list.
8. Merge Phase A → `base-image.yml` builds, self-tests with the new suite, pushes `ghcr.io/swedev/klartex-base:<new tag>`.
9. **Phase B PR**: move the pin in `.github/workflows/publish.yml` (`container.image`) and `docker/Dockerfile.render` (`FROM`) in the same commit, copying tag@digest from the step summary.
10. **Phase C — schema**: `font`/`header_font` become `oneOf` [string, object]; object has `file` (required), `bold`, `italic`, `bold_italic`, `additionalProperties: false`, each matching `FONT_FILENAME_PATTERN` (step definition above). Descriptions cover the missing-face behaviour, the asset-root resolution, the no-underscore rule, and the serve limits.
11. **Phase C — `load_page_template`**: validate both forms (mirroring `_check_margins`' hand-rolled errors), store the parsed value, add `font_setup` / `header_font_setup` properties emitting the LaTeX; `header_font` keeps defaulting to `font` in both forms (a file-form `font` with no `header_font` reuses the same files for `\kxheaderfontfamily`).
12. **Phase C — `klartex/templates/_page_template.tex.jinja`**: emit `\VAR{page_template.font_setup}` / `\VAR{page_template.header_font_setup}` in place of the inline `\setmainfont` / `\newfontfamily` blocks — string form must produce byte-identical output (asserted by the golden-preamble test).
13. **Phase C — `klartex/renderer.py`**: factor `_resolve_asset_root()` out of `_compile_tex` and preflight file-form fonts against it: every referenced face file must be a readable regular file there, else `ValueError` naming the file and the asset-dir contract — raised before xelatex starts, and before the `shutil.which("xelatex")` check so it is testable without TeX.
14. **Phase C — tests**: tex-level assertions for the emitted fontspec commands (all four faces; regular only; header reuse). Preflight coverage: missing regular face, missing optional face, no `asset_dir` (cwd used), invalid `asset_dir`. Xelatex round-trip: locate a TeX-shipped OpenType file deterministically via `kpsewhich lmroman10-regular.otf` (present wherever xelatex is — no conditional skip beyond the existing xelatex gate), copy it into a tmp `asset_dir` under a pattern-conformant name, render with the file form. `tests/test_server.py`: one test sending a font file through `assets` with a file-form `font`, and one asserting a file-form `font` whose file is absent from `assets` returns the structured 4xx the ValueError mapping produces.
15. **CHANGELOG**: entry at the next release, per release flow (user-initiated).

## Risks

- **Release window between A and B**: a release cut after Phase A but before Phase B fails its gate. Deliberate (fail-closed — the pinned environment doesn't yet honour the guarantee), but Phase B must follow promptly. Agent judgment, open to question; the alternative (keep the Georgia-only env until B) leaves the guarantee unenforced at the gate.
- **Package/family-name drift**: mitigated by step 1 (verify inside the image before writing `GUARANTEED_FONTS`) and locked afterwards by the Dockerfile exact-match check and the parametrized test.
- **CI on GitHub runners**: the minimal TeX Live env in `ci.yml` lacks these fonts, so the parametrized family tests skip there — the skip-reason wording (no "xelatex") keeps the skip guard quiet. Enforcement lives in the base-image self-test and the release gate, as it already does for Georgia. The Phase C file-form tests do **not** skip conditionally: their font comes from `kpsewhich`, available wherever xelatex is.
- **Missing-face behaviour**: "absent face key → regular face, no synthesis" is an agent decision, open to question; it is the least magical option and is documented on the discovery surface, but callers who expect faux bold will be surprised.
- **`Path=./` semantics**: file fonts resolve against the single asset root (xelatex's cwd), not `TEXINPUTS` — same contract as other explicitly-relative assets; the preflight converts the sharp edge into a clear error and the schema description states the contract.
- **Overlap with #61** ("Expand the page-template typography surface beyond font and header_font", open): touches the same `DOCUMENT_SETTINGS` area of `klartex/page_templates.py`. No dependency either way; whoever lands second rebases. The `oneOf` shape chosen here adds no obstacle — #61 adds sibling keys, not new font forms.
- **klartex.se**: the sole consumer sees the guarantee only after moving its own base pin; until then its environment matches the old base. Coordinate the pin move there after Phase B.

## Test Plan

- `pytest -n auto` locally: string-form behaviour unchanged (golden preamble byte-identical), new tex-level and loader tests pass; guaranteed-family renders skip for families not installed locally, run for those that are.
- Schema lock: the `font` description enumerates `GUARANTEED_FONTS`; `klartex schema _block` shows it.
- File form end to end: the `kpsewhich`-sourced `.otf` copied to a tmp `asset_dir` renders via `render()`, and via `POST /render` with the font in `assets`; bold/italic-bearing content compiles with and without face files supplied.
- Preflight: file-form font with no such file in the asset root raises `ValueError` naming the file, without invoking xelatex (and without needing xelatex installed); the endpoint maps it to a structured 4xx.
- Environment guarantee: `base-image.yml` self-test (full suite, `KLARTEX_REQUIRE_FONTS=1`, inside the fresh image) proves every guaranteed family renders; the release gate proves the same in the pinned image after Phase B.
- Negative guard: the Dockerfile build fails if any guaranteed family — MS core included — is missing from `fc-list : family` as an exact name, on either architecture; a silently dropped Debian package cannot publish a base image.
