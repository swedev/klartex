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
| `faktura` | Invoice with line items, VAT, and payment information |
| `kvitto` | Receipt with a simple items list, payment method, and total |
| `resultatrakning` | Income statement with comparison years and notes |
| `balansrakning` | Balance sheet with assets and liabilities/equity sections |
| `budgetrapport` | Budget report with account codes, budget, and actuals |
| `sie-exportrapport` | Human-readable PDF of SIE4 accounting data |

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

# Debian/Ubuntu
sudo apt install texlive-xetex texlive-fonts-recommended \
  texlive-latex-extra texlive-latex-recommended texlive-science texlive-plain-generic
```

The Debian/Ubuntu package set is the one CI installs on every push — a fast approximation of the render environment. `texlive-xetex` alone is not enough — rendering needs `ulem` (in `texlive-plain-generic`), `tcolorbox` and `siunitx`, among others.

### Ready-made render environment (container image)

The environment klartex is released against is published as `ghcr.io/swedev/klartex-base`: full TeX Live plus Microsoft core fonts (Georgia, Arial, Times New Roman, …) and the Python runtime needed to install the package. Services that render with klartex build on it instead of reconstructing the apt list.

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

Template, data and any slot sources travel in one JSON object. Assets come along as base64 and are written to a temporary directory that lives exactly as long as the call does.

```json
{
  "template": "_block",
  "data": {"body": [{"type": "heading", "text": "Hello"}]},
  "header_source": "\\fancyhead[R]{\\includegraphics[height=1cm]{logo.png}}",
  "assets": {"logo.png": "<base64>"}
}
```

The answer is `application/pdf`, or an error whose `detail.type` is `input_error`, `validation_error`, `payload_too_large`, `render_error` or `overloaded`. Schema and block errors additionally carry `detail.path` — a list like `["body", 1, "items", 0, "text"]` addressing the node that failed.

| Environment variable | Default | Meaning |
|----------------------|---------|---------|
| `KLARTEX_MAX_CONCURRENT` | `2` | Concurrent xelatex runs. Further concurrent calls get `503` with `Retry-After`. |
| `KLARTEX_MAX_BODY_MB` | `80` | Largest request read. The check happens on `Content-Length` before the body is read, so the limit applies to the size the caller declares. |

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

A slot that is left out takes the surface's default: the block engine has an empty header and the page-number footer, recipes the letterhead header and the page-number footer with the document title before the page number (`footer: {"variant": "pagenumber", "title": true}`).

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

The object form of `letterhead` requires `fields.org_name` — the name is what the header is built around, and without it the other details would not be printed. A header with no details at all is written as the variant name on its own (`"header": "letterhead"`). `logo` is a filename free of LaTeX-special characters (`\ # $ % & _ { } ~ ^`).

Beside the slots there are document-level settings — `font`, `header_font` and `diff_style` — which apply whether or not a slot has its own LaTeX, plus `page_numbers` and `first_page_header`.

### Custom page template

Raw LaTeX is supplied per slot, not in the JSON:

```bash
klartex -d data.json --header-template header.tex.jinja
klartex -d data.json --header-template header.tex.jinja --footer-template footer.tex.jinja
```

```python
render("_block", data, header_source=Path("header.tex.jinja").read_text())
```

Both files must live in the same directory — that directory becomes the template directory files resolve against.

A slot file defines its own part of the chrome:

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

- **CLI with a file-based page template** (`--header-template`, `--footer-template`): files are resolved relative to the slot files' own directory, with the working directory as fallback. A template and its logos can therefore live together in e.g. a `Branding/` folder and be used from any working directory. For a symlinked file, the target's directory applies.
- **API with `header_source` or `footer_source`**: the parameters take raw text with no path, so there is no template directory to work from. Callers who need files outside the working directory pass `asset_dir=<directory>` to `render()`; otherwise the working directory applies.

> **Both `\includegraphics{logo.pdf}` and `\includegraphics{./logo.pdf}` work**, as does `\input{../shared/colors.tex}` — relative references resolve against the template's directory (or `asset_dir`, otherwise the working directory). One asymmetry remains: names starting with `./` or `../` do **not** fall back to the working directory. TeX's file lookup (Kpathsea) never searches for such names; it tries them as-is against xelatex's working directory — which is precisely the template's directory. Plain names, by contrast, go through the full search chain and are found even if the file only exists in the working directory.

## Architecture

Klartex uses a three-layer architecture:

1. **Document level** — `klartex-base.cls` handles page setup and basic headers/footers. Page templates (`.tex.jinja`) are injected into the preamble and control colors, logos, and layout.
2. **Component level** — Reusable `.sty` packages providing structured LaTeX macros (e.g. `klartex-signatureblock.sty`, `klartex-klausuler.sty`, `klartex-agenda.sty`)
3. **Recipe level** — YAML files that declare which components and content fields to combine

### Rendering paths

- **Recipe templates** (`protokoll`, `faktura`, `kvitto`) — YAML recipes declaring components and data mappings
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
  - type: klausuler
    data_map:
      items: agenda_items
    options:
      item_title_field: title
      item_body_field: body

schema: schema.json
```

Available recipe components: `heading`, `description_list`, `agenda`, `text`, `resultatrakning`, `budgettabell`, `notapparat`, `invoice_header`, `invoice_recipient`, `invoice_table`, `payment_info`, `invoice_note`, `receipt_header`, `receipt_table`. The shared types (`agenda`, `description_list`, `heading`, `resultatrakning`, `budgettabell`, `notapparat`, `text`) render through the same macros as the block-engine path.

Block engine blocks: `heading`, `text`, `list`, `table`, `callout`, `quote`, `title_page`, `parties`, `clause`, `signatures`, `description_list`, `form`, `columns`, `agenda`, `name_roster`, `resultatrakning`, `budgettabell`, `notapparat`, `page_break`, `latex`.

## Annual Meeting Package

The block engine can compose all documents needed for a Swedish association's annual meeting:

| Document | Block types |
|----------|-----------|
| Summons + agenda | heading, description_list, agenda |
| Annual report | heading, name_roster, text, signatures |
| Financial report | heading, text, resultatrakning, notapparat, signatures |
| Audit report | heading, text, signatures |
| Budget | heading, budgettabell |
| Nomination proposal | heading, name_roster, signatures |
| Motion | heading, text, clause, signatures |
| Board response | heading, text, signatures |

The agent selects and orders blocks for each document — no separate templates needed. See `tests/fixtures/block_kallelse.json` etc. for complete examples.

## License

MIT
