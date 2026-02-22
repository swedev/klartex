> **Svensk version:** [README.md](README.md)

# Klartex

PDF generation via LaTeX — structured data in, professional documents out.

Klartex takes JSON data + template name + optional branding and produces PDF via XeLaTeX. Can be used as a Python library, CLI tool, or HTTP service.

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

pdf_bytes = render("protokoll", data, branding="default")
```

### As CLI

```bash
# Render a template
klartex render --template protokoll --data data.json -o output.pdf

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

# List templates
curl http://localhost:8000/templates

# Get schema
curl http://localhost:8000/templates/protokoll/schema
```

## Branding

Create a YAML file in `branding/`:

```yaml
name: "My Organization"
org_number: "802481-1234"
address:
  line1: "Main Street 12"
  line2: "123 45 City"
logo: "logos/logo.pdf"
colors:
  primary: "2E7D32"
  secondary: "666666"
  accent: "0066CC"
lang: "en"
```

Then use `--branding myorg` or `"branding": "myorg"` in API calls.

## Architecture

Klartex uses a three-layer architecture:

1. **Document level** — `klartex-base.cls` handles page setup, branding, headers/footers
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
