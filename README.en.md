> **Svensk version:** [README.md](README.md)

# Klartex

PDF generation via LaTeX — structured data in, professional documents out.

[klartex.se](https://klartex.se) · [PyPI](https://pypi.org/project/klartex/) · [GitHub](https://github.com/swedev/klartex)

Klartex takes JSON data + template name and produces PDF via XeLaTeX. Can be used as a Python library or CLI tool.

## Templates

| Template | Description |
|----------|-------------|
| `_block` | Universal block engine — the agent composes the document freely |
| `protokoll` | Meeting minutes with agenda, decisions, and adjusters |
| `faktura` | Invoice with line items, VAT, and payment details |
| `kvitto` | Receipt with an items list, payment method, and total |
| `resultatrakning` | Income statement with comparison years and notes |
| `balansrakning` | Balance sheet with assets and liabilities/equity sections |
| `budgetrapport` | Budget report with account codes, budget, and actuals |
| `sie-exportrapport` | Human-readable PDF of SIE4 accounting data |

`klartex templates` lists the templates, `klartex schema <template>` shows what each one requires and `klartex example <template>` a complete payload — the schema is the authoritative description of every template.

## Installation

```bash
# As a global CLI tool
pipx install klartex

# Or inside a project
pip install klartex
```

Requires Python ≥ 3.12 and XeLaTeX.

```bash
# macOS
brew install --cask mactex

# BasicTeX or a minimal TeX Live (e.g. Debian/Ubuntu)
tlmgr install $(grep -v '^#' .github/tl_packages)
```

`.github/tl_packages` is the exact list of TeX Live packages needed — it is what CI installs. A distribution's `texlive-xetex` alone is not enough.

### Ready-made render environment (container image)

The environment klartex is released against is published as `ghcr.io/swedev/klartex-base`: full TeX Live, a guaranteed font set and the Python runtime needed to install the package. Services that render with klartex build on it instead of reconstructing the apt list.

The guaranteed font families — what `page_template.font` and `page_template.header_font` can be set to without knowing anything about the machine that renders — are listed in the `font` / `header_font` schema descriptions (`klartex schema _block`); the image build fails if any family is missing. Other fontspec names work only where that font happens to be installed.

A font outside the list can travel with the call instead: `font` and `header_font` also take an object of file names — `{"file": "Inter-Regular.ttf", "bold": "Inter-Bold.ttf", "italic": "Inter-Italic.ttf", "bold_italic": "Inter-BoldItalic.ttf"}`. The files are looked up in `asset_dir` (over `klartex serve`: in the request's `assets`), and only `file` is required — a face whose file was not sent renders in the regular face. A name is a bare file name ending in `.ttf` or `.otf`, with no underscore or other LaTeX special character.

```dockerfile
FROM ghcr.io/swedev/klartex-base:<tag>@sha256:<digest>
```

Always pin the tag **and** the manifest digest — there is no `latest` tag. The image is built by `.github/workflows/base-image.yml` from `docker/Dockerfile.base`, and the full test suite runs inside the freshly built amd64 image before anything is published — an image klartex cannot render in never reaches the registry.

The same image is also the release gate: `.github/workflows/publish.yml` runs the full test suite inside the pinned image before the package is built, so every version published to PyPI has passed in the render environment.

## Usage

### As a Python library

```python
from klartex import render

pdf_bytes = render("protokoll", data)
```

### As CLI

```bash
# Render (block engine is default)
klartex -d data.json

# Pipe JSON via stdin
cat data.json | klartex

# With explicit template
klartex -d data.json -t protokoll

# With a custom page template (one file for the whole page)
klartex -d data.json --page-template page.tex.jinja

# With a custom page template (one slot at a time)
klartex -d data.json --header-template header.tex.jinja

# List templates
klartex templates

# Show JSON Schema for a template
klartex schema protokoll
```

### As an HTTP service (`klartex serve`)

The same renderer behind a small HTTP surface: `POST /render` (JSON in, PDF out) and `GET /health`. It lives behind the `serve` extra.

```bash
pip install 'klartex[serve]'
klartex serve --host 127.0.0.1 --port 8000
```

Template, data and any template sources — `page_template_source` for the whole page, `header_source`/`footer_source` per slot — travel in one JSON object. Assets come along as base64 and are written to a temporary directory that lives exactly as long as the call does.

```json
{
  "template": "_block",
  "data": {"body": [{"type": "heading", "text": "Hello"}]},
  "header_source": "\\fancyhead[R]{\\includegraphics[height=1cm]{logo.png}}",
  "assets": {"logo.png": "<base64>"}
}
```

The answer is `application/pdf`, or an error whose `detail.type` is `input_error`, `validation_error`, `payload_too_large`, `render_error` or `overloaded`. Schema and block errors additionally carry `detail.path` — a list like `["body", 1, "items", 0, "text"]` addressing the node that failed.

| Environment variable | Meaning |
|----------------------|---------|
| `KLARTEX_MAX_CONCURRENT` | Concurrent xelatex runs. Further concurrent calls get `503` with `Retry-After`. |
| `KLARTEX_MAX_BODY_MB` | Largest request read. The check happens on `Content-Length` before the body is read, so the limit applies to the size the caller declares. |

The defaults live in `klartex/server/app.py`.

The service owns neither authentication nor rate limiting — it is a compile layer and belongs behind a caller that owns both. That is why it binds to `127.0.0.1` unless told otherwise. A `latex` block in the input runs arbitrary LaTeX in the render process; run the service isolated from anything that cannot take that.

### The render service as an image

Every release also publishes `ghcr.io/swedev/klartex-render:X.Y.Z` — the same pinned base the release gate tests in, with the release wheel installed. The tag always equals the klartex version and there is no `latest`: pin the version that matches your `klartex==` pin.

```bash
docker run --rm -p 127.0.0.1:8000:8000 \
  --read-only --tmpfs /tmp --tmpfs /home/render \
  ghcr.io/swedev/klartex-render:X.Y.Z
```

The image runs as non-root and binds to `0.0.0.0` inside the container — publish the port only on the network the caller is on.

## Page Templates

A page template is composed of two independent slots: **header** and **footer**. Each is chosen on its own — a predefined variant, an object carrying the content that goes there, or `null` for empty. Structured settings keep applying to whichever slot stays predefined, even when the other slot has its own LaTeX.

| Slot | Variant | Content |
|------|---------|---------|
| `header` | `letterhead` | Organisation details on the left, logo on the right |
| `header` | `logo` | Logo only, on the right |
| `header` | `null` | Empty header — the header's space is reclaimed |
| `footer` | `pagenumber` | Centered page numbers, optionally preceded by the document title (`title`) |
| `footer` | `columns` | Multi-column footer with company, contact and payment details (`fields`) |
| `footer` | `null` | Empty footer |

A slot that is left out takes the surface's default: the block engine has an empty header and the page-number footer, recipes the letterhead header and the page-number footer with the document title before the page number (`footer: {"variant": "pagenumber", "title": true}`). A recipe may declare its own defaults: `faktura` and `kvitto` default to the columns footer, with company, address, org number and payment details derived from the payload's own `sender` and payment fields. A producer that sends its own columns footer wins field by field; another variant, `null` or a custom source is used exactly as sent. `klartex schema <template>` describes the template's own default.

```json
"page_template": {
  "header": {
    "variant": "letterhead",
    "fields": {
      "org_name": "My Organization",
      "address": "Storgatan 1, 123 45 Stad",
      "web": "myorg.se",
      "email": "board@myorg.se",
      "logo": "logo.pdf"
    }
  },
  "footer": {
    "variant": "columns",
    "fields": {
      "company": "My Organization",
      "org_number": "802000-0000",
      "bankgiro": "1234-5678"
    }
  }
}
```

```json
"page_template": { "header": "logo", "footer": null }
```

The object form of `letterhead` requires `fields.org_name` — the name is what the header is built around, and without it the other details would not be printed. A header with no details at all is written as the variant name on its own (`"header": "letterhead"`). `logo` is a filename free of whitespace and LaTeX-special characters; the schema states the pattern. The contact column is narrow and does not hyphenate, so a long `web` or `email` wraps after `@`, `.` and `/` to fit.

Beside the slots there are document-level settings — `font`, `header_font`, `diff_style` and `margins` — which apply whether or not a slot has its own LaTeX, plus `page_numbers` and `first_page_header`.

### Margins

`margins` is the distance from the paper edge to the **body text**, one key per side. Each key is optional and applies independently; the value is a LaTeX dimension with an explicit unit (`cm`, `mm`, `pt`, `in`).

```json
"page_template": {
  "margins": { "top": "3.4cm", "bottom": "2cm", "left": "3cm", "right": "3cm" }
}
```

The chrome adapts to the measurements rather than the other way round: `top` is measured to the first line of text, so with a header the band stays where it is and the gap between header and text grows or shrinks — which is why `top` must exceed the band's bottom edge (the measurement is in the schema description, and the loader rejects a value that is too small). With an empty (or content-less) header its space is reclaimed and any positive `top` works. `bottom` is measured to the last line of text and the footer hangs below it, so leave room for it — a small value clips the footer. `left` and `right` also move the header and footer band, which follows the text width.

A slot with custom LaTeX that sets its own geometry wins over `margins`, exactly as it does over `font`.

### Custom page template

Raw LaTeX is supplied as a file or as text, not in the JSON. One file can own the whole page, or one slot at a time:

```bash
klartex -d data.json --page-template page.tex.jinja
klartex -d data.json --header-template header.tex.jinja
klartex -d data.json --header-template header.tex.jinja --footer-template footer.tex.jinja
```

```python
render("_block", data, page_template_source=Path("page.tex.jinja").read_text())
render("_block", data, header_source=Path("header.tex.jinja").read_text())
```

`--page-template` owns both slots and cannot be combined with the slot flags. The slot files must live in the same directory — that directory becomes the template directory files resolve against.

With no template flag, klartex looks for one itself: first `<data-stem>.tex.jinja` next to the data file, then `page_template.tex.jinja` in the working directory. A file found that way is used as a whole-page template, and its path is announced on stderr. A slot flag turns autodetection off.

The document-level settings in `data.page_template` (`font`, `header_font`, `diff_style`, `margins`) apply in either form and are emitted before the template's own LaTeX, so the template's `\geometry` and `\setmainfont` win. The JSON `header` and `footer` are not read when a whole-page template is in use.

A template file defines its own chrome:

```latex
\definecolor{brandprimary}{HTML}{2E5A1C}
\definecolor{brandsecondary}{HTML}{555555}
\renewcommand{\orgname}{My Organization}
\fancyhead[L]{\fontsize{6pt}{9pt}\selectfont\textbf{\orgname}}
\fancyhead[R]{\includegraphics[height=0.855cm]{logo.pdf}}
```

```latex
\makeatletter
\fancyfoot[C]{%
    \kx@setlang%
    \fontsize{6pt}{9pt}\selectfont\color{brandsecondary}%
    \doctitle\ \textbullet\ \kx@page\ \thepage\ \kx@of\ \pageref{LastPage}%
}
\makeatother
```

These macros are the contract between a page template and the document class, and may be redefined at the top level of the preamble: `\orgname`, `\orgaddress`, `\orgwebsite`, `\orgemail`, `\orgphone`, `\brandlogo`. The class defines them empty, so use `\renewcommand`. The header's space is reclaimed at the end of the preamble when `\orgname` and `\brandlogo` are both empty — a value set later (e.g. inside `\AtBeginDocument`) is too late for that test.

The parts are emitted in a fixed order: document-level settings, header, footer, space reclaim. A custom slot should therefore leave the other slot's `\fancyhead`/`\fancyfoot` cells alone.

Where logos and other files are resolved differs between the two surfaces:

- **CLI with a file-based page template** (`--page-template`, `--header-template`, `--footer-template`, and an autodetected template): files are resolved relative to the template file's own directory, with the working directory as fallback. A template and its logos can therefore live together in e.g. a `Branding/` folder and be used from any working directory. For a symlinked file, the target's directory applies.
- **API with `page_template_source`, `header_source` or `footer_source`**: the parameters take raw text with no path, so there is no template directory to work from. Callers who need files outside the working directory pass `asset_dir=<directory>` to `render()`; otherwise the working directory applies.

> **Both `\includegraphics{logo.pdf}` and `\includegraphics{./logo.pdf}` work**, as does `\input{../shared/colors.tex}` — relative references resolve against the template's directory (or `asset_dir`, otherwise the working directory). One asymmetry remains: names starting with `./` or `../` do **not** fall back to the working directory. TeX's file lookup (Kpathsea) never searches for such names; it tries them as-is against xelatex's working directory — which is precisely the template's directory. Plain names, by contrast, go through the full search chain and are found even if the file only exists in the working directory.

## Architecture

Klartex uses a three-layer architecture:

1. **Document level** — `klartex-base.cls` handles page setup and basic headers/footers. Page templates (`.tex.jinja`) are injected into the preamble and control colors, logos, and layout.
2. **Component level** — Reusable `.sty` packages providing structured LaTeX macros (e.g. `klartex-signatureblock.sty`, `klartex-callout.sty`, `klartex-agenda.sty`)
3. **Recipe level** — YAML files that declare which components and content fields to combine

### Rendering paths

- **Recipe templates** (every named template in `klartex templates`) — YAML recipes declaring components and data mappings
- **Block engine** (`_block`) — The agent composes `body[]` freely from typed blocks

### Creating a YAML Recipe Template

Create a `recipe.yaml` in the template directory (e.g. `klartex/templates/my-template/recipe.yaml`):

```yaml
template:
  name: my-template
  description: "Template description"
  lang: en

document:
  title: "{{ data.title }}"
  metadata:
    - label: "Date:"
      field: date

components:
  - type: heading
    data_map:
      title: meeting_type
  - type: agenda
    data_map:
      items: agenda_items

schema: schema.json
```

Components are registered in `klartex/components.py`; those with a block schema are also the block engine's block types (`klartex blocks`). The shipped recipes in `klartex/templates/*/recipe.yaml` are the complete examples.

## Annual Meeting Package

The block engine can compose all documents needed for a Swedish association's annual meeting — summons with agenda, annual report, financial statements, audit report, budget, nomination proposal, motions and board responses. The agent selects and orders blocks for each document; no separate templates are needed. `tests/fixtures/block_*.json` are complete examples.

## License

MIT
