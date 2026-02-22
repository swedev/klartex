> **Svensk version:** [README.md](README.md)

# Klartex

PDF generation via LaTeX — structured data in, professional documents out.

Klartex takes JSON data + template name and produces PDF via XeLaTeX. Can be used as a Python library, CLI tool, or HTTP service.

## Templates

| Template | Description |
|----------|-------------|
| `protokoll` | Meeting minutes with agenda, decisions, and adjusters |
| `faktura` | Invoice with line items, VAT, and payment information |
| `_block` | Universal block engine — the agent composes the document freely |

## Installation

```bash
pip install klartex
```

Requires XeLaTeX (`brew install --cask mactex` or `apt install texlive-xetex`).

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

# With external page template
klartex -d data.json --page-template myorg.tex.jinja

# List templates
klartex templates

# Show JSON Schema for a template
klartex schema protokoll

# Start HTTP server
klartex serve
```

### As HTTP service

```bash
klartex serve --port 8000
```

```bash
# Render PDF
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -d '{"template": "protokoll", "data": {...}}' \
  -o output.pdf

# Render with external page template
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -d '{"template": "_block", "data": {...}, "page_template_source": "\\definecolor{brandprimary}{HTML}{2E5A1C}\\n..."}' \
  -o output.pdf

# List templates
curl http://localhost:8000/templates

# Get schema
curl http://localhost:8000/templates/protokoll/schema
```

## Page Templates

Page templates control headers, footers, colors, and logos. Three built-in templates are available:

| Page Template | Description |
|---------------|-------------|
| `formal` | Org name and contact info in header, logo, page numbers in footer |
| `clean` | Logo only in header, page numbers in footer |
| `none` | No header, page numbers only in footer |

### Custom page template

Create a `.tex.jinja` file that defines `\fancyhead`/`\fancyfoot`:

```latex
\definecolor{brandprimary}{HTML}{2E5A1C}
\definecolor{brandsecondary}{HTML}{555555}
\providecommand{\orgname}{}
\renewcommand{\orgname}{My Organization}
\makeatletter
\fancyhead[L]{\fontsize{6pt}{9pt}\selectfont\textbf{\orgname}}
\fancyhead[R]{\includegraphics[height=0.855cm]{logo.pdf}}
\fancyfoot[C]{%
    \kx@setlang%
    \fontsize{6pt}{9pt}\selectfont\color{brandsecondary}%
    \doctitle\ \textbullet\ \kx@page\ \thepage\ \kx@of\ \pageref{LastPage}%
}
\makeatother
```

Then use `--page-template myorg.tex.jinja` in CLI or `"page_template_source": "..."` in API calls. Logos and other files are resolved relative to the working directory.

## Architecture

Klartex uses a three-layer architecture:

1. **Document level** — `klartex-base.cls` handles page setup and basic headers/footers. Page templates (`.tex.jinja`) are injected into the preamble and control colors, logos, and layout.
2. **Component level** — Reusable `.sty` packages providing structured LaTeX macros (e.g. `klartex-signaturblock.sty`, `klartex-klausuler.sty`, `klartex-titelsida.sty`)
3. **Recipe level** — YAML files that declare which components and content fields to combine

### Rendering paths

- **Recipe templates** (`protokoll`, `faktura`, `avtal`) — YAML recipes declaring components and data mappings
- **Block engine** (`_block`) — The agent composes `body[]` freely from typed blocks

### Creating a YAML Recipe Template

Create a `recipe.yaml` in the template directory (e.g. `templates/my-template/recipe.yaml`):

```yaml
template:
  name: my-template
  description: "Template description"
  lang: en

document:
  title: "{{ data.title }}"
  page_template: formal
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

Available components: `heading`, `metadata_table`, `attendees`, `klausuler`, `signaturblock`, `titelsida`, `adjuster_signatures`, `invoice_header`, `invoice_recipient`, `invoice_table`, `payment_info`, `invoice_note`.

## License

MIT
