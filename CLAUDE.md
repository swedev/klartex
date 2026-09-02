# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the full test suite (requires xelatex on PATH); -n auto spreads the ~80
# xelatex compilations over all cores (pytest-xdist, in the dev extras)
pytest -n auto

# Run a single test
pytest tests/test_block_engine.py::TestPrepareBlockContext::test_default_page_template

# Run only fast tests (skip xelatex compilation tests)
pytest -k "not xelatex" -m "not slow"

# Render via the CLI in dev (block engine is default; -t selects recipe)
klartex -d tests/fixtures/block_kallelse.json -o /tmp/out.pdf
cat data.json | klartex                       # stdin → output.pdf in cwd

# Discovery commands the agent uses
klartex templates                              # list all templates
klartex blocks                                 # list block-engine block types
klartex schema _block                          # full block-engine JSON Schema (with oneOf union)
klartex example _block                         # canonical example payload

# HTTP surface (needs the serve extra: pip install '.[dev,serve]')
klartex serve --port 8000
```

`xelatex` is required for ~all rendering tests, and `pdftotext` (poppler-utils) for the text-layer round-trip tests in `tests/test_pdf_text_layer.py`. CI explicitly fails if any xelatex-tagged or `test_server` test is skipped (`.github/workflows/ci.yml`), so don't add `pytest.skip` shortcuts to silence local failures — install TeX Live instead: `brew install --cask mactex` on macOS, or on Debian/Ubuntu the package set in `README.md` (`texlive-xetex` alone is missing `ulem`, `tcolorbox` and `siunitx`). CI installs a minimal TeX Live from `.github/tl_packages` (cached via `zauguin/install-texlive`); that list must be transitively complete, so a new `\RequirePackage` may need a new entry there — the file header says how the list is derived.

The render environment klartex is developed against lives in `docker/Dockerfile.base` and is published as `ghcr.io/swedev/klartex-base` by `.github/workflows/base-image.yml`, which runs the full suite inside the freshly built amd64 image before pushing. `.github/workflows/publish.yml` pins a `tag@digest` from that registry and runs the suite inside it as the release gate, so a version only reaches PyPI after passing in the render environment. Changing the Dockerfile therefore implies a follow-up PR that moves the pin in `publish.yml` **and** `docker/Dockerfile.render` — the release refuses to publish an image when those two diverge — plus every external consumer; copy it from the build's step summary.

## Releases

1. Releases are always initiated by the user.
2. When the user asks to publish a release:
   1. Bump `version` in `pyproject.toml`.
   2. Add a dated entry at the top of `CHANGELOG.md` (groups: `Breaking changes` / `New features` / `Fixes` / `Spacing`).
   3. Commit as `Release vX.Y.Z: <summary>` and push to `main`.
   4. `gh release create vX.Y.Z --generate-notes` pushes the tag and creates the release, which triggers `.github/workflows/publish.yml` — runs the suite inside the pinned base image, builds the package, publishes to PyPI and pushes `ghcr.io/swedev/klartex-render:X.Y.Z`.

## Architecture

Klartex is a two-path PDF renderer: structured JSON in, PDF bytes out via XeLaTeX. The two paths share escaping, page templates, and the LaTeX class layer; they diverge in how blocks/components are dispatched.

### Rendering pipeline (`klartex/renderer.py::render`)

```
JSON data
  → jsonschema.validate against template schema
  → per-block validation against klartex/schemas/blocks/<type>.schema.json (block engine only)
  → escape_data() recursively LaTeX-escapes every string
  → _restore_block_types() re-injects unescaped `type` discriminators and raw `latex.source`
       (escaping turns "description_list" → "description\_list", which would break dispatch)
  → Jinja render → .tex source
  → tempdir + symlinked klartex/cls/ + TEXINPUTS=<tmpdir>:cls:[asset_dir:]cwd
  → xelatex run twice (page references), cwd=asset_dir-or-cwd,
       -output-directory=<tmpdir> → PDF bytes
```

Two consequences of the escape→restore pattern matter when adding blocks:
- The escaped copy is what the Jinja templates iterate over, but `block.type` and any raw-LaTeX field must be restored from the original. `_restore_block_types` recurses through `list.items[].content[]`, `columns.items[][]`, and `clause.content[]`. **Any new block that nests other blocks must be added to that recursion.**
- LaTeX-safe Jinja delimiters: `\BLOCK{…}`, `\VAR{…}`, `\#{…}` (configured in `renderer.py::_jinja_env`). The `| inline` filter parses inline markup against the document language and is the only sanctioned way to render user text inside a paragraph.

### Two surfaces, one renderer

**Block engine** (free-form surface) — virtual template name `_block`. Caller composes `body[]` freely from typed blocks; `_block_engine.tex.jinja` dispatches each block to its render macro. No fixed document structure — the document type emerges from what blocks are placed. Most development so far has happened here, but that reflects which documents have been worked on — neither path is the primary one by decision.

**Recipe path** (specialized surface for stable transactional document types) — `klartex/templates/<name>/recipe.yaml` declares which components and metadata fields make up a fixed document type. `recipe.py::prepare_recipe_context` resolves dot-paths (e.g. `data_map: {items: agenda_items}`) and hands a context to `_recipe_base.tex.jinja`. Used by `protokoll`, `faktura`, `balansrakning`, `resultatrakning`, `budgetrapport`, `sie-exportrapport`. The value is letting producers send domain-shaped JSON (e.g. an invoice with `lines[]`) without describing layout — useful for upstream systems with stable contracts.

The two paths share rendering logic via `_block_macros.tex.jinja` and `_financial_macros.tex.jinja`. Block-engine equivalents exist for almost every recipe component (`agenda` covers protokoll's items, `title_page` covers title pages, `resultatrakning`/`budgettabell`/`notapparat` are dual-purpose). Only the `invoice_*` components are recipe-only.

`registry.py::discover_templates` scans `templates/*/schema.json + recipe.yaml` for recipes and registers `_block` as a virtual template. For `_block` it builds two schemas: `validation_schema` (base, no `oneOf`) used at runtime so per-block error messages stay readable, and `schema` (with `oneOf` union of all block schemas) shown by `klartex schema _block` for agent introspection.

### Component registry (`klartex/components.py`)

Single source of truth for block types: `_COMPONENTS` maps each name to its `.sty` package (if any) and JSON-Schema file. To add a block:

1. Drop a schema at `klartex/schemas/blocks/<type>.schema.json`.
2. Add a `ComponentSpec` entry in `_COMPONENTS`.
3. Add a `\BLOCK{ if block.type == "<type>" }` arm in `klartex/templates/_block_engine.tex.jinja`.
4. If it needs custom LaTeX, add a `klartex-<type>.sty` to `klartex/cls/` (it is auto-loaded via the component spec; `klartex-base.cls` is the document class).
5. If the block can nest other blocks, extend `renderer.py::_restore_block_types`.

`KNOWN_BLOCK_TYPES` in `block_engine.py` is derived from components that have a `block_schema_path`. Recipe-only components (`invoice_*`) have no schema and aren't visible to the block engine.

### Page templates (`klartex/page_templates.py`)

A page template is composed of two independent slots, **header** and **footer**. Each slot is a predefined variant, a custom `.tex.jinja` source, or empty. The slot model is typed and defined once, at the top of `page_templates.py`: a `FieldType` says how a value validates (`TEXT`, `BOOL`, `FILENAME`, composed with `|` and `list_of()` — the footer address is `TEXT | list_of(TEXT)`), a `Field` is a named use of a type in a variant — its description plus how it renders: the header contract macro it sets, or the `\kxfooter` keyval it becomes (defaulting to the field name) — and a `Variant` composes named `Field`s with its own settings and required fields (`HEADER_VARIANTS`, `FOOTER_VARIANTS`; document-level keys in `DOCUMENT_SETTINGS`). `LOGO` is one `Field` shared by both header variants. Everything else derives from it: the loader validates against it, `_page_template.tex.jinja` and the fragments iterate it (`PageTemplate.header_macros`, `footer_keyvals`), `list_slot_variants()` lists it, and `page_template_schema()` generates the `page_template` JSON Schema subtree that `registry.py` injects into every template schema at load time — the schema files carry only a `$comment` placeholder there, so a new field or variant is one table entry. The variants live as fragments in `klartex/page_templates/<slot>/<variant>.tex.jinja` — header: `letterhead`, `logo`; footer: `pagenumber`, `columns`. A slot the payload leaves out takes the surface's default (`BLOCK_DEFAULT_SLOTS`: empty header + `pagenumber` footer; `RECIPE_DEFAULT_SLOTS`: letterhead + `pagenumber` footer with the document title). `_page_template.tex.jinja` composes them in a fixed order: document-level settings → header → footer → header-space reclaim → first-page style. The reclaim comes after both slots because its `\ifdefempty` test must see the final value of the contract macros.

`DOCUMENT_SETTINGS` holds `page_numbers`, `first_page_header`, `font`, `header_font`, `diff_style` and `margins`. `margins` is text-block geometry — paper edge to body text — validated against `DIMENSION_PATTERN` (a number plus `cm`/`mm`/`pt`/`in`, no LaTeX special character, so it survives `escape_data()`) and rendered by `PageTemplate.margin_setup` into the settings step. Because the top regime is chosen at LaTeX time by the reclaim, a set `top` emits **both** pieces at once: a `headsep` `\dimexpr` measured from `HEADER_BAND_BOTTOM` (the cls geometry's `top` + `headheight`, locked by a sum test in `tests/test_renderer.py`) and a `\kxreclaimtop` renewal. `\kxfooterbottom` / `\kxfooterfootskip` in `klartex-base.cls` late-bind the bottom geometry that `klartex-footer.sty` enlarges to, so `margins.bottom` wins over the columns footer's band; `left`/`right` also emit `\setlength{\headwidth}{\textwidth}`, since fancyhdr does not track a later `\textwidth`. The loader rejects a `top` at or below the band only when a predefined header actually carries content — a reclaimed header and a custom source take any positive value.

The contract macros (`\orgname`, `\orgaddress`, `\orgwebsite`, `\orgemail`, `\orgphone`, `\brandlogo`) are `\providecommand`-ed in `klartex-base.cls`, so any slot on either path can `\renewcommand` them. Both slots carry their content under `fields`: the `letterhead` variant's (`org_name`, `address`, `web`, `email`, `phone`, `logo`) are emitted as `\renewcommand`s before its fragment. Its object form requires `fields.org_name`, since both the fragment and the reclaim test key off `\orgname`; the bare variant name stays the way to ask for an empty letterhead. Contact lines are stacked with `\kx@hdrline` (in `klartex-base.cls`), which emits the `\\` separator only between lines that render — an unconditional one breaks a column whose leading field is empty.

Custom sources come in two forms. Per-slot sources come from `--header-template` / `--footer-template` on the CLI (one slot each; both files must share a directory, which becomes `asset_dir`) or `header_source` / `footer_source` on `render()`: a custom slot owns its own chrome, the other slot still comes from `data.page_template`. A whole-page source — `--page-template` on the CLI, `page_template_source` on `render()` — owns both slots from one file; the payload's `header`/`footer` are then not read for composition (they stay schema-validated), and `load_page_template()` raises `ValueError` if it is combined with a per-slot source. In both forms the document-level settings (`font`, `header_font`, `diff_style`, `margins`) still come from `data.page_template` and are emitted before the source, so the source's own `\geometry` and font commands win. The CLI autodetects a whole-page template when no template flag is given: `<data-stem>.tex.jinja` beside the data file, then `./page_template.tex.jinja` in cwd, announced on stderr; any slot flag suppresses autodetection. Slot content lives under `fields` on both slots (`footer: {"variant": "columns", "fields": {"company": …}}`); a variant's own settings, like `pagenumber`'s `title`, sit beside `variant`.

Assets referenced from a page template (`\includegraphics{logo.pdf}`, `\input{…}`, fonts) resolve through **two** mechanisms, because Kpathsea treats the two name shapes differently:

- **Plain names** (`logo.pdf`) go through `TEXINPUTS=<tmpdir>:cls:[asset_dir:]cwd:<inherited>` — a real search chain, so a plain name found in neither `asset_dir` nor cwd still falls back.
- **Explicitly relative names** (`./logo.pdf`, `../shared/x.tex`) are never looked up on `TEXINPUTS`; Kpathsea tries them as-is against xelatex's process cwd. `_compile_tex` therefore runs xelatex with `cwd=<asset root>` — the resolved `asset_dir`, else the caller's cwd — and redirects every build artifact to the tempdir with `-output-directory`. There is no fallback chain here (a process has one cwd), so a `./` reference missing from `asset_dir` fails even if the file exists in cwd. A `./` inside a *nested* included file also resolves against that same single root, not the including file's directory.

`asset_dir` is the optional `render(asset_dir=…)` directory. For the CLI's template flags, `cli.py::main` sets it to the resolved template file's parent (the slot flags' shared parent), so a template and its assets can live together in one directory and be used from any cwd. `.resolve()` is deliberate — assets follow a symlinked template to its target's directory (canonical template bundles), and the path must be absolute since it is both a `TEXINPUTS` entry and the subprocess cwd. A non-directory `asset_dir` raises `ValueError` (validated before the `shutil.which("xelatex")` check, so it is testable without TeX). The API's `page_template_source` / `header_source` / `footer_source` are raw text with no path, so API callers must pass `asset_dir` themselves.

Two invariants worth not breaking:

- The leading `TEXINPUTS` entry is the **absolute tempdir**, not `.`. Since cwd is now the asset root, a bare `.` would place the asset root ahead of the bundled `cls/` and let a template-dir file hijack a klartex `.sty`. Locked by `tests/test_renderer.py::test_asset_dir_cannot_shadow_bundled_sty`.
- `-output-directory` means a render never writes into the template dir or cwd, and the second xelatex run finds the first run's `.aux` there. Locked by the two no-artifacts tests and `test_second_run_finds_aux_from_first_run`.

### LaTeX layer (`klartex/cls/`)

`klartex-base.cls` sets up geometry, fancyhdr, language switching (`\kx@setlang`), and shared macros. Each component that needs custom LaTeX ships its own `.sty` (`klartex-signatureblock.sty`, `klartex-callout.sty`, …). At compile time the renderer symlinks the entire `cls/` dir into the tempdir and additionally exposes `klartex-base.cls` at top level so `\documentclass{klartex-base}` resolves.

Spacing fixes accumulate in `_block_engine.tex.jinja` as `\kxneedspace` glue tricks and `\nopagebreak[4]` / `\penalty` interactions to manage break points (orphan protection, sibling label-width via `\settowidth{\kxgrouplabelw}{…}`). When changing spacing, read the recent CHANGELOG entries — most fixes have a documented rationale that is easy to undo accidentally.

### HTTP surface (`klartex/server/`)

`klartex serve` runs a small FastAPI app — `POST /render` (JSON in, PDF out) and `GET /health` — behind the optional `serve` extra. `app.py` holds the app, the Content-Length limit and the handlers that keep a malformed envelope inside the documented error contract instead of FastAPI's default 422; `render.py` holds the endpoint: `page_template_source` and the per-slot sources, base64 assets written to a per-request tempdir, the `BoundedSemaphore` that caps concurrent xelatex runs, and the mapping from core exceptions to `detail.type` + `detail.path`. Config is environment-only (`KLARTEX_MAX_CONCURRENT`, `KLARTEX_MAX_BODY_MB`), read when the modules are imported. The CLI imports the package lazily, so nothing here loads without the extra — and `tests/test_server.py` `importorskip`s itself away without it, which is why the workflows install `.[dev,serve]` and their skip guard covers `test_server` as well as `xelatex`.

Block-path extraction in `render.py` parses the message text `renderer._validate_blocks` raises. It is a stopgap: when the core grows a structured block-validation exception, that becomes the source and the regex goes.

Every release publishes the service as `ghcr.io/swedev/klartex-render:X.Y.Z` from `docker/Dockerfile.render` — the `image` job in `publish.yml`, multi-arch, one immutable tag per release and no `latest`. It builds `FROM` the same pinned base the release gate tests in, and the job refuses to run when those two pins diverge: **a base bump must move `container.image` in `publish.yml` and `FROM` in `Dockerfile.render` in the same commit.** Retrying a failed image publish means dispatching `publish.yml` from the release tag; a dispatch from a branch runs the gate and stops. The first publish of the package is private — make it public manually, there is no API for it.

## Tests

`tests/fixtures/*.json` are real-shape payloads that render to PDF via xelatex; they are the canonical examples for each block. When changing block semantics, the fixture is usually the right thing to update first, then assert against. Tests categorise loosely:

- `test_block_engine.py` — context preparation + xelatex compilation per block type
- `test_renderer.py` — full pipeline including escape/restore
- `test_page_templates.py` / `test_cli_page_template.py` — page-template resolution
- `test_schemas.py` — schema validity and oneOf coverage of all block types
- `test_agent_cli.py` — agent-discovery CLI commands (`templates`, `blocks`, `schema`, `example`)
- `test_server.py` — the `klartex serve` endpoint: error contract, limits, concurrency cap (skipped without the `serve` extra)

## Languages

Swedish only where Swedish is the content: text that ends up in the rendered PDF (recipe labels, the language strings in `klartex-base.cls`), README and CHANGELOG. Everything aimed at code, agents or developers is English: identifiers, docstrings, comments, error and CLI messages, and every `description` in the JSON schemas — the schema is the agent's discovery surface and its keys are English. GitHub issues and pull requests are in English, title and body alike, with Swedish domain terms (`valsedel`, `resultaträkning`, `stadgeändringar`) kept as terms inside the English text. The user (`Martin Söderholm`) communicates in Swedish — match the language of the user's message in replies.
