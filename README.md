> **English version:** [README.en.md](README.en.md)

# Klartex

PDF-generering via LaTeX — strukturerad data in, professionella dokument ut.

Klartex tar JSON-data + mallnamn + valfri branding och producerar PDF via XeLaTeX. Kan användas som Python-bibliotek, CLI-verktyg eller HTTP-tjänst.

## Mallar

| Mall | Beskrivning |
|------|-------------|
| `protokoll` | Mötesprotokoll med dagordning, beslut och justerare |
| `faktura` | Faktura med rader, moms och betalningsinformation |
| `_block` | Universell blockmotor — agenten komponerar dokumentet fritt |

## Installation

```bash
pip install klartex
```

Kräver XeLaTeX (`brew install --cask mactex` eller `apt install texlive-xetex`).

## Användning

### Som Python-bibliotek

```python
from klartex import render

pdf_bytes = render("protokoll", data, branding="default")
```

### Som CLI

```bash
# Rendera en mall
klartex render --template protokoll --data data.json -o output.pdf

# Lista mallar
klartex templates

# Visa JSON Schema för en mall
klartex schema protokoll

# Starta HTTP-server
klartex serve
```

### Som HTTP-tjänst

```bash
klartex serve --port 8000
```

```bash
# Rendera PDF
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -d '{"template": "protokoll", "data": {...}}' \
  -o output.pdf

# Lista mallar
curl http://localhost:8000/templates

# Hämta schema
curl http://localhost:8000/templates/protokoll/schema
```

## Branding

Skapa en YAML-fil i `branding/`:

```yaml
name: "Min Förening"
org_number: "802481-1234"
address:
  line1: "Storgatan 12"
  line2: "123 45 Staden"
logo: "logos/logo.pdf"
colors:
  primary: "2E7D32"
  secondary: "666666"
  accent: "0066CC"
lang: "sv"
```

Använd sedan `--branding minforening` eller `"branding": "minforening"` i API-anrop.

## Arkitektur

Klartex har en trelagers-arkitektur:

1. **Dokumentnivå** — `klartex-base.cls` hanterar siduppställning, branding, sidhuvud/sidfot
2. **Komponentnivå** — Återanvändbara `.sty`-paket som ger strukturerade LaTeX-makron (t.ex. `klartex-signaturblock.sty`, `klartex-klausuler.sty`, `klartex-titelsida.sty`)
3. **Receptnivå** — YAML-filer som deklarerar vilka komponenter och innehållsfält som ska kombineras

### Renderingsvägar

- **Recipe-mallar** (`protokoll`, `faktura`, `avtal`) — YAML-recept som deklarerar komponenter och mappningar
- **Block engine** (`_block`) — Agenten komponerar `body[]` fritt från typade block

### Skapa en YAML-receptmall

Skapa en `recipe.yaml` i mallens katalog (t.ex. `templates/min-mall/recipe.yaml`):

```yaml
template:
  name: min-mall
  description: "Beskrivning av mallen"
  lang: sv

document:
  title: "{{ data.title }}"
  page_template: formal
  metadata:
    - label: "Datum:"
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

Tillgängliga komponenter: `heading`, `metadata_table`, `attendees`, `klausuler`, `signaturblock`, `titelsida`, `adjuster_signatures`, `invoice_header`, `invoice_recipient`, `invoice_table`, `payment_info`, `invoice_note`.

## Licens

MIT
