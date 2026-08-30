> **English version:** [README.en.md](README.en.md)

# Klartex

PDF-generering via LaTeX — strukturerad data in, professionella dokument ut.

[klartex.se](https://klartex.se) · [PyPI](https://pypi.org/project/klartex/) · [GitHub](https://github.com/swedev/klartex)

Klartex tar JSON-data + mallnamn och producerar PDF via XeLaTeX. Kan användas som Python-bibliotek eller CLI-verktyg.

## Mallar

| Mall | Beskrivning |
|------|-------------|
| `_block` | Universell blockmotor — agenten komponerar dokumentet fritt |
| `protokoll` | Mötesprotokoll med dagordning, beslut och justerare |
| `faktura` | Faktura med rader, moms och betalningsinformation |
| `kvitto` | Kvitto med enkel radlista, betalsätt och totalbelopp |
| `resultatrakning` | Resultaträkning med jämförelseår och noter |
| `balansrakning` | Balansräkning med tillgångar och skulder/eget kapital |
| `budgetrapport` | Budgetrapport med kontokoder, budget och utfall |
| `sie-exportrapport` | Läsbar PDF av SIE4-bokföringsdata |

## Installation

```bash
# Som globalt CLI-verktyg
pipx install klartex

# Eller i ett projekt
pip install klartex
```

Kräver Python ≥ 3.12 och XeLaTeX.

```bash
# macOS
brew install --cask mactex

# Debian/Ubuntu
sudo apt install texlive-xetex texlive-fonts-recommended \
  texlive-latex-extra texlive-latex-recommended texlive-science texlive-plain-generic
```

Paketuppsättningen för Debian/Ubuntu är en snabb approximation av renderingsmiljön. Den exakta listan över TeX Live-paket som behövs finns i `.github/tl_packages` — det är vad CI installerar, och med BasicTeX eller en minimal TeX Live räcker `tlmgr install $(grep -v '^#' .github/tl_packages)`. `texlive-xetex` ensamt räcker inte — bland annat `ulem` (i `texlive-plain-generic`), `tcolorbox` och `siunitx` behövs för att rendera.

### Färdig renderingsmiljö (containerimage)

Den miljö klartex släpps mot publiceras som `ghcr.io/swedev/klartex-base`: full TeX Live plus Microsoft core fonts (Georgia, Arial, Times New Roman …) och den Python-runtime som behövs för att installera paketet. Tjänster som renderar med klartex bygger vidare på den i stället för att återskapa apt-listan.

```dockerfile
FROM ghcr.io/swedev/klartex-base:<tagg>@sha256:<digest>
```

Pinna alltid tagg **och** manifest-digest — det finns ingen `latest`-tagg. Imagen byggs av `.github/workflows/base-image.yml` från `docker/Dockerfile.base`, och hela testsviten körs inuti den färdigbyggda amd64-imagen innan något publiceras — en image som klartex inte renderar i når aldrig registret.

Samma image är också releasegrind: `.github/workflows/publish.yml` kör hela testsviten inuti den pinnade imagen innan paketet byggs, så varje version som publiceras på PyPI har passerat i renderingsmiljön.

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

# Med extern sidmall (hela sidan, eller en slot i taget)
klartex -d data.json --page-template minforening.tex.jinja
klartex -d data.json --header-template sidhuvud.tex.jinja

# Lista mallar
klartex templates

# Visa JSON Schema för en mall
klartex schema protokoll
```

## Sidmallar (Page Templates)

En sidmall består av två oberoende delar: **header** (sidhuvud) och **footer** (sidfot). Varje del väljs för sig — en färdig variant, ett objekt med uppgifterna som ska stå där, eller `null` för tomt. Strukturerade inställningar fortsätter gälla för den del som är fördefinierad, även när den andra delen har egen LaTeX.

| Slot | Variant | Innehåll |
|------|---------|----------|
| `header` | `letterhead` | Organisationsuppgifter till vänster, logotyp till höger |
| `header` | `logo` | Enbart logotyp till höger |
| `header` | `null` | Tomt sidhuvud — sidhuvudets utrymme återtas |
| `footer` | `standard` | Sidnummer centrerat; med kontaktuppgifter en flerkolumnsfot |
| `footer` | `null` | Tom sidfot |

De tre namnen `formal`, `clean` och `none` är alias för färdiga kombinationer:

| Alias | Motsvarar |
|-------|-----------|
| `formal` | `header: "letterhead"` + `footer: {"title": true}` |
| `clean` | `header: "logo"` + `footer: "standard"` |
| `none` | `header: null` + `footer: "standard"` |

```json
"page_template": "formal"
```

```json
"page_template": {
  "header": {
    "variant": "letterhead",
    "org_name": "Min Förening",
    "address": "Storgatan 1, 123 45 Stad",
    "web": "minforening.se",
    "email": "styrelsen@minforening.se",
    "logo": "logo.pdf"
  },
  "footer": {
    "company": "Min Förening",
    "org_number": "802000-0000",
    "bankgiro": "1234-5678"
  }
}
```

```json
"page_template": { "header": "logo", "footer": null }
```

Ett alias kan kombineras med en slot som ersätter den sidan av kombinationen: `{"name": "clean", "footer": null}` ger logotypsidhuvudet utan sidfot.

Objektformen av `letterhead` kräver `org_name` — namnet är det som sidhuvudet byggs runt, och utan det skulle övriga uppgifter inte skrivas ut. Ett sidhuvud helt utan uppgifter anges som variantnamnet självt (`"header": "letterhead"`). `logo` är ett filnamn utan LaTeX-specialtecken (`\ # $ % & _ { } ~ ^`).

Utöver sloten finns inställningar på dokumentnivå — `font`, `header_font` och `diff_style` — som gäller oavsett om en slot har egen LaTeX, plus `page_numbers` och `first_page_header`.

### Egen sidmall

Rå LaTeX skickas per slot, inte i JSON:

```bash
klartex -d data.json --header-template sidhuvud.tex.jinja
klartex -d data.json --header-template sidhuvud.tex.jinja --footer-template sidfot.tex.jinja
```

```python
render("_block", data, header_source=Path("sidhuvud.tex.jinja").read_text())
```

Båda filerna måste ligga i samma katalog — den katalogen blir mallkatalogen som filer hittas relativt till. `--page-template` (och `"page_template_source"` i API-anrop) tar i stället över **båda** sloten med en enda fil, och kan inte kombineras med slot-flaggorna.

En slot-fil definierar sin egen del av chromet:

```latex
\definecolor{brandprimary}{HTML}{2E5A1C}
\definecolor{brandsecondary}{HTML}{555555}
\renewcommand{\orgname}{Min Förening}
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

Dessa makron är kontraktet mellan sidmallen och dokumentklassen och kan skrivas om i preamblens toppnivå: `\orgname`, `\orgaddress`, `\orgwebsite`, `\orgemail`, `\orgphone`, `\brandlogo`. Klassen definierar dem tomma, så använd `\renewcommand`. Sidhuvudets utrymme återtas i slutet av preamblen om `\orgname` och `\brandlogo` båda är tomma — ett värde som sätts senare (t.ex. i `\AtBeginDocument`) hinner inte med det testet.

Delarna skrivs ut i fast ordning: inställningar på dokumentnivå, sidhuvud, sidfot, återtaget utrymme. En egen slot bör därför inte röra den andra slotens `\fancyhead`/`\fancyfoot`-celler.

Var logotyper och andra filer hittas skiljer sig mellan de två ytorna:

- **CLI med filbaserad sidmall** (`--page-template`, `--header-template`, `--footer-template`, eller autodetekterad `<data-stem>.tex.jinja` / `page_template.tex.jinja`): filer hittas relativt till sidmallens egen katalog, med arbetsmappen som fallback. En mall och dess logotyper kan därmed ligga samlade i t.ex. en `Branding/`-mapp och användas från vilken arbetsmapp som helst. För en symlänkad mall gäller målets katalog. Autodetektering hoppas över när en slot-flagga anges.
- **API med `page_template_source`, `header_source` eller `footer_source`**: parametrarna tar rå text utan sökväg, så det finns ingen mallkatalog att utgå från. Anropare som vill hitta filer utanför arbetsmappen skickar `asset_dir=<katalog>` till `render()`; annars gäller arbetsmappen.

> **Både `\includegraphics{logo.pdf}` och `\includegraphics{./logo.pdf}` fungerar**, liksom `\input{../delat/farger.tex}` — relativa referenser utgår från mallens katalog (eller `asset_dir`, i annat fall arbetsmappen). En skillnad finns dock: namn med `./` eller `../` faller **inte** tillbaka på arbetsmappen. TeX:s filsökning (Kpathsea) söker aldrig upp sådana namn, utan provar dem rakt av mot xelatex arbetskatalog — och den katalogen är just mallens katalog. Namn utan prefix söks däremot i hela kedjan och hittas även om filen bara ligger i arbetsmappen.

## Arkitektur

Klartex har en trelagers-arkitektur:

1. **Dokumentnivå** — `klartex-base.cls` hanterar siduppställning och grundläggande sidhuvud/sidfot. Sidmallar (`.tex.jinja`) injiceras i preambeln och styr färger, logotyp och layout.
2. **Komponentnivå** — Återanvändbara `.sty`-paket som ger strukturerade LaTeX-makron (t.ex. `klartex-signatureblock.sty`, `klartex-klausuler.sty`, `klartex-agenda.sty`)
3. **Receptnivå** — YAML-filer som deklarerar vilka komponenter och innehållsfält som ska kombineras

### Renderingsvägar

- **Recipe-mallar** (`protokoll`, `faktura`, `kvitto`) — YAML-recept som deklarerar komponenter och mappningar
- **Block engine** (`_block`) — Agenten komponerar `body[]` fritt från typade block

### Skapa en YAML-receptmall

Skapa en `recipe.yaml` i mallens katalog (t.ex. `klartex/templates/min-mall/recipe.yaml`):

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

Tillgängliga recept-komponenter: `heading`, `description_list`, `agenda`, `text`, `resultatrakning`, `budgettabell`, `notapparat`, `invoice_header`, `invoice_recipient`, `invoice_table`, `payment_info`, `invoice_note`, `receipt_header`, `receipt_table`. Block-motsvarigheterna (`agenda`, `description_list`, `heading`, `resultatrakning`, `budgettabell`, `notapparat`, `text`) renderas via samma delade makron som block-engine-vägen.

Block engine-block: `heading`, `text`, `list`, `table`, `callout`, `quote`, `title_page`, `parties`, `clause`, `signatures`, `description_list`, `form`, `columns`, `agenda`, `name_roster`, `resultatrakning`, `budgettabell`, `notapparat`, `page_break`, `latex`.

## Årsmötespaket

Blockmotorn kan komponera alla dokument som behövs för ett föreningsårsmöte:

| Dokument | Blocktyper |
|----------|-----------|
| Kallelse + dagordning | heading, description_list, agenda |
| Verksamhetsberättelse | heading, name_roster, text, signatures |
| Ekonomisk årsredovisning | heading, text, resultatrakning, notapparat, signatures |
| Revisionsberättelse | heading, text, signatures |
| Budget | heading, budgettabell |
| Valberedningens förslag | heading, name_roster, signatures |
| Motion | heading, text, clause, signatures |
| Styrelsens yttrande | heading, text, signatures |

Agenten väljer och ordnar block för varje dokument — inga separata mallar behövs. Se `tests/fixtures/block_kallelse.json` m.fl. för fullständiga exempel.

## Licens

MIT
