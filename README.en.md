> **Svensk version:** [README.md](README.md)

# Klartex

PDF generation via LaTeX — structured data in, professional documents out.

Klartex takes JSON data + template name + optional branding and produces PDF via XeLaTeX. Can be used as a Python library, CLI tool, or HTTP service.

## Templates

| Template | Description |
|----------|-------------|
| `protokoll` | Meeting minutes with agenda, decisions, and adjusters |
| `faktura` | Invoice with line items, VAT, and payment information |
| `avtal` | Agreement with clauses, subclauses, and signatures |

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

## License

MIT
