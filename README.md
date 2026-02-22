> **English version:** [README.en.md](README.en.md)

# Klartex

PDF-generering via LaTeX — strukturerad data in, professionella dokument ut.

Klartex tar JSON-data + mallnamn och producerar PDF via XeLaTeX. Kan användas som Python-bibliotek, CLI-verktyg eller HTTP-tjänst.

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

pdf_bytes = render("protokoll", data)
```

### Som CLI

```bash
# Rendera (block engine är default)
klartex -d data.json

# Pipe JSON via stdin
cat data.json | klartex

# Med explicit mall
klartex -d data.json -t protokoll

# Med extern sidmall
klartex -d data.json --page-template minforening.tex.jinja

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

# Rendera med extern sidmall
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -d '{"template": "_block", "data": {...}, "page_template_source": "\\definecolor{brandprimary}{HTML}{2E5A1C}\\n..."}' \
  -o output.pdf

# Lista mallar
curl http://localhost:8000/templates

# Hämta schema
curl http://localhost:8000/templates/protokoll/schema
```

## Sidmallar (Page Templates)

Sidmallar styr sidhuvud, sidfot, färger och logotyp. Tre inbyggda finns:

| Sidmall | Beskrivning |
|---------|-------------|
| `formal` | Organisationsnamn och kontaktinfo i sidhuvud, logotyp, sidnummer i sidfot |
| `clean` | Enbart logotyp i sidhuvud, sidnummer i sidfot |
| `none` | Inget sidhuvud, enbart sidnummer i sidfot |

### Egen sidmall

Skapa en `.tex.jinja`-fil som definierar `\fancyhead`/`\fancyfoot`:

```latex
\definecolor{brandprimary}{HTML}{2E5A1C}
\definecolor{brandsecondary}{HTML}{555555}
\providecommand{\orgname}{}
\renewcommand{\orgname}{Min Förening}
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

Använd sedan `--page-template minforening.tex.jinja` i CLI eller `"page_template_source": "..."` i API-anrop. Logotyper och andra filer hittas relativt till arbetsmappen.

## Arkitektur

Klartex har en trelagers-arkitektur:

1. **Dokumentnivå** — `klartex-base.cls` hanterar siduppställning och grundläggande sidhuvud/sidfot. Sidmallar (`.tex.jinja`) injiceras i preambeln och styr färger, logotyp och layout.
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
