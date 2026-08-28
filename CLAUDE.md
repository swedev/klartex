# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the full test suite (requires xelatex on PATH)
pytest

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
```

`xelatex` is required for ~all rendering tests, and `pdftotext` (poppler-utils) for the text-layer round-trip tests in `tests/test_pdf_text_layer.py`. CI explicitly fails if any xelatex-tagged test is skipped (`.github/workflows/ci.yml`), so don't add `pytest.skip` shortcuts to silence local failures — install TeX Live instead: `brew install --cask mactex` on macOS, or on Debian/Ubuntu the package set in `README.md`, which mirrors the one `.github/workflows/ci.yml` installs (`texlive-xetex` alone is missing `ulem`, `tcolorbox` and `siunitx`).

The render environment klartex is released against lives in `docker/Dockerfile.base` and is published as `ghcr.io/swedev/klartex-base` by `.github/workflows/base-image.yml`, which runs the full suite inside the freshly built amd64 image before pushing. Changing the Dockerfile therefore implies a follow-up PR that moves the pinned `tag@digest` — copy it from the build's step summary.

## Releases

1. Releases are always initiated by the user.
2. When the user asks to publish a release:
   1. Bump `version` in `pyproject.toml`.
   2. Add a dated entry at the top of `CHANGELOG.md` (groups: `Breaking changes` / `New features` / `Fixes` / `Spacing`).
   3. Commit as `Release vX.Y.Z: <summary>` and push to `main`.
   4. `gh release create vX.Y.Z --generate-notes` pushes the tag and creates the release, which triggers `.github/workflows/publish.yml` — runs tests and publishes to PyPI.

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

**Block engine** (primary surface) — virtual template name `_block`. Caller composes `body[]` freely from typed blocks; `_block_engine.tex.jinja` dispatches each block to its render macro. No fixed document structure — the document type emerges from what blocks are placed. Almost all active development happens here, and most user-authored documents go through this path.

**Recipe path** (specialized surface for stable transactional document types) — `klartex/templates/<name>/recipe.yaml` declares which components and metadata fields make up a fixed document type. `recipe.py::prepare_recipe_context` resolves dot-paths (e.g. `data_map: {items: agenda_items}`) and hands a context to `_recipe_base.tex.jinja`. Used by `protokoll`, `faktura`, `balansrakning`, `resultatrakning`, `budgetrapport`, `sie-exportrapport`. The value is letting producers send domain-shaped JSON (e.g. an invoice with `lines[]`) without describing layout — useful for upstream systems with stable contracts.

The two paths share rendering logic via `_block_macros.tex.jinja` and `_financial_macros.tex.jinja`. Block-engine equivalents exist for almost every recipe component (`agenda` covers protokoll's items, `title_page` covers title pages, `resultatrakning`/`budgettabell`/`notapparat` are dual-purpose). Only the `invoice_*` components are recipe-only today.

`registry.py::discover_templates` scans `templates/*/schema.json + recipe.yaml` for recipes and registers `_block` as a virtual template. For `_block` it builds two schemas: `validation_schema` (base, no `oneOf`) used at runtime so per-block error messages stay readable, and `schema` (with `oneOf` union of all block schemas) shown by `klartex schema _block` for agent introspection.

### Component registry (`klartex/components.py`)

Single source of truth for block types: `_COMPONENTS` maps each name to its `.sty` package (if any) and JSON-Schema file. To add a block:

1. Drop a schema at `klartex/schemas/blocks/<type>.schema.json`.
2. Add a `ComponentSpec` entry in `_COMPONENTS`.
3. Add a `\BLOCK{ if block.type == "<type>" }` arm in `klartex/templates/_block_engine.tex.jinja`.
4. If it needs custom LaTeX, add a `klartex-<type>.sty` to `klartex/cls/` (it is auto-loaded via the component spec; `klartex-base.cls` is the document class).
5. If the block can nest other blocks, extend `renderer.py::_restore_block_types`.

`KNOWN_BLOCK_TYPES` in `block_engine.py` is derived from components that have a `block_schema_path`. Recipe-only components (`invoice_*`) intentionally have no schema and aren't visible to the block engine.

### Page templates (`klartex/page_templates.py`)

A page template is a `.tex.jinja` fragment that defines `\fancyhead`/`\fancyfoot`, colors, logo. Three built-ins (`formal`, `clean`, `none`) live in `klartex/page_templates/`. Resolution priority in the CLI:

1. Explicit `--page-template path` flag.
2. `<data-stem>.tex.jinja` next to the data file (auto-detected).
3. `./page_template.tex.jinja` in cwd (auto-detected).
4. Built-in name from `data.page_template` (`"formal"` / `"clean"` / `"none"` / dict with overrides).
5. Default `"none"`.

When a caller supplies raw page-template source (CLI flag, auto-detect, or `page_template_source` API field) the loader uses `"none"` defaults so the caller owns header/footer entirely.

Assets referenced from a page template (`\includegraphics{logo.pdf}`, `\input{…}`, fonts) resolve through **two** mechanisms, because Kpathsea treats the two name shapes differently:

- **Plain names** (`logo.pdf`) go through `TEXINPUTS=<tmpdir>:cls:[asset_dir:]cwd:<inherited>` — a real search chain, so a plain name found in neither `asset_dir` nor cwd still falls back.
- **Explicitly relative names** (`./logo.pdf`, `../shared/x.tex`) are never looked up on `TEXINPUTS`; Kpathsea tries them as-is against xelatex's process cwd. `_compile_tex` therefore runs xelatex with `cwd=<asset root>` — the resolved `asset_dir`, else the caller's cwd — and redirects every build artifact to the tempdir with `-output-directory`. There is no fallback chain here (a process has one cwd), so a `./` reference missing from `asset_dir` fails even if the file exists in cwd. A `./` inside a *nested* included file also resolves against that same single root, not the including file's directory.

`asset_dir` is the optional `render(asset_dir=…)` directory. For the CLI's three file-based branches, `cli.py::main` sets it to the resolved page-template file's parent, so a template and its assets can live together in one directory and be used from any cwd. `.resolve()` is deliberate — assets follow a symlinked template to its target's directory (canonical template bundles), and the path must be absolute since it is both a `TEXINPUTS` entry and the subprocess cwd. A non-directory `asset_dir` raises `ValueError` (validated before the `shutil.which("xelatex")` check, so it is testable without TeX). The API's `page_template_source` is raw text with no path, so API callers must pass `asset_dir` themselves.

Two invariants worth not breaking:

- The leading `TEXINPUTS` entry is the **absolute tempdir**, not `.`. Since cwd is now the asset root, a bare `.` would place the asset root ahead of the bundled `cls/` and let a template-dir file hijack a klartex `.sty`. Locked by `tests/test_renderer.py::test_asset_dir_cannot_shadow_bundled_sty`.
- `-output-directory` means a render never writes into the template dir or cwd, and the second xelatex run finds the first run's `.aux` there. Locked by the two no-artifacts tests and `test_second_run_finds_aux_from_first_run`.

### LaTeX layer (`klartex/cls/`)

`klartex-base.cls` sets up geometry, fancyhdr, language switching (`\kx@setlang`), and shared macros. Each component that needs custom LaTeX ships its own `.sty` (`klartex-signatureblock.sty`, `klartex-callout.sty`, …). At compile time the renderer symlinks the entire `cls/` dir into the tempdir and additionally exposes `klartex-base.cls` at top level so `\documentclass{klartex-base}` resolves.

Spacing fixes accumulate in `_block_engine.tex.jinja` as `\kxneedspace` glue tricks and `\nopagebreak[4]` / `\penalty` interactions to manage break points (orphan protection, sibling label-width via `\settowidth{\kxgrouplabelw}{…}`). When changing spacing, read the recent CHANGELOG entries — most fixes have a documented rationale that is easy to undo accidentally.

## Tests

`tests/fixtures/*.json` are real-shape payloads that render to PDF via xelatex; they are the canonical examples for each block. When changing block semantics, the fixture is usually the right thing to update first, then assert against. Tests categorise loosely:

- `test_block_engine.py` — context preparation + xelatex compilation per block type
- `test_renderer.py` — full pipeline including escape/restore
- `test_page_templates.py` / `test_cli_page_template.py` — page-template resolution
- `test_schemas.py` — schema validity and oneOf coverage of all block types
- `test_agent_cli.py` — agent-discovery CLI commands (`templates`, `blocks`, `schema`, `example`)

## Languages

User-facing messages, schema descriptions, and CHANGELOG/README are in Swedish; code, identifiers, and Python docstrings are in English. GitHub issues and pull requests are in English, title and body alike, with Swedish domain terms (`valsedel`, `resultaträkning`, `stadgeändringar`) kept as terms inside the English text. The user (`Martin Söderholm`) communicates in Swedish — match the language of the user's message in replies.
