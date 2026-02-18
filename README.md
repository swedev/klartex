> **English version:** [README.en.md](README.en.md)

# Klartex

PDF-generering via LaTeX — strukturerad data in, professionella dokument ut.

Klartex tar JSON-data + mallnamn + valfri branding och producerar PDF via XeLaTeX. Kan användas som Python-bibliotek, CLI-verktyg eller HTTP-tjänst.

## Mallar

| Mall | Beskrivning |
|------|-------------|
| `protokoll` | Mötesprotokoll med dagordning, beslut och justerare |
| `faktura` | Faktura med rader, moms och betalningsinformation |
| `avtal` | Avtal med klausuler, underparagrafer och signaturer |

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

1. **Dokumentniva** -- `klartex-base.cls` hanterar siduppstallning, branding, sidhuvud/sidfot
2. **Komponentniva** -- Atervandningsbara `.sty`-paket som ger strukturerade LaTeX-makron (t.ex. `klartex-signaturblock.sty`, `klartex-klausuler.sty`, `klartex-titelsida.sty`)
3. **Receptniva** -- YAML-filer som deklarerar vilka komponenter och innehallsfalt som ska kombineras

Befintliga monolitiska `.tex.jinja`-mallar fungerar som tidigare. Nya mallar kan defineras som YAML-recept istallet for att skriva fullstandiga LaTeX/Jinja-filer.

### Renderingsmotor

Parametern `engine` styr vilken renderingsvag som anvands:

- `auto` (standard): Anvander `.tex.jinja` om den finns, annars `recipe.yaml`
- `legacy`: Tvingas anvanda `.tex.jinja`
- `recipe`: Tvingas anvanda `recipe.yaml`

```bash
# CLI
klartex render --template protokoll --data data.json --engine recipe

# API
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -d '{"template": "protokoll", "data": {...}, "engine": "recipe"}'
```

```python
# Python
pdf_bytes = render("protokoll", data, engine="recipe")
```

### Skapa en YAML-receptmall

Skapa en `recipe.yaml` i mallens katalog (t.ex. `templates/min-mall/recipe.yaml`):

```yaml
template:
  name: min-mall
  description: "Beskrivning av mallen"
  lang: sv

document:
  title: "{{ data.title }}"
  header: standard
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

Tillgangliga komponenter: `heading`, `metadata_table`, `attendees`, `klausuler`, `signaturblock`, `titelsida`, `adjuster_signatures`.

## Licens

MIT
