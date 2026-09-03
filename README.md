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
| `faktura` | Faktura med rader, moms och betalningsuppgifter |
| `kvitto` | Kvitto med radlista, betalsätt och totalbelopp |
| `resultatrakning` | Resultaträkning med jämförelseår och noter |
| `balansrakning` | Balansräkning med tillgångar och skulder/eget kapital |
| `budgetrapport` | Budgetrapport med kontokoder, budget och utfall |
| `sie-exportrapport` | Läsbar PDF av SIE4-bokföringsdata |

`klartex templates` listar mallarna, `klartex schema <mall>` visar vad varje mall kräver och `klartex example <mall>` ett komplett exempel — schemat är den auktoritativa beskrivningen av varje mall.

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

# BasicTeX eller en minimal TeX Live (t.ex. Debian/Ubuntu)
tlmgr install $(grep -v '^#' .github/tl_packages)
```

`.github/tl_packages` är den exakta listan över TeX Live-paket som behövs — det är vad CI installerar. Distributionens `texlive-xetex` ensamt räcker inte.

### Färdig renderingsmiljö (containerimage)

Den miljö klartex släpps mot publiceras som `ghcr.io/swedev/klartex-base`: full TeX Live, en garanterad teckensnittsuppsättning och den Python-runtime som behövs för att installera paketet. Tjänster som renderar med klartex bygger vidare på den i stället för att återskapa apt-listan.

De garanterade teckensnittsfamiljerna — det `page_template.font` och `page_template.header_font` kan sättas till utan att veta något om maskinen som renderar — står i schemabeskrivningarna för `font` och `header_font` (`klartex schema _block`); imagebygget faller om någon familj saknas. Andra fontspec-namn fungerar bara där teckensnittet råkar vara installerat.

Ett teckensnitt utanför listan kan i stället följa med anropet: `font` och `header_font` tar också ett objekt med filnamn — `{"file": "Inter-Regular.ttf", "bold": "Inter-Bold.ttf", "italic": "Inter-Italic.ttf", "bold_italic": "Inter-BoldItalic.ttf"}`. Filerna slås upp i `asset_dir` (över `klartex serve`: i anropets `assets`), och bara `file` krävs — ett snitt vars fil inte skickats med renderas i det ordinarie snittet. Filnamnet är ett rent filnamn som slutar på `.ttf` eller `.otf`, utan understreck eller andra LaTeX-tecken.

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

# Med egen sidmall (hela sidan i en fil)
klartex -d data.json --page-template sidmall.tex.jinja

# Med egen sidmall (en slot i taget)
klartex -d data.json --header-template sidhuvud.tex.jinja

# Lista mallar
klartex templates

# Visa JSON Schema för en mall
klartex schema protokoll
```

### Som HTTP-tjänst (`klartex serve`)

Samma renderare bakom en liten HTTP-yta: `POST /render` (JSON in, PDF ut) och `GET /health`. Ligger bakom extran `serve`.

```bash
pip install 'klartex[serve]'
klartex serve --host 127.0.0.1 --port 8000
```

Mall, data och eventuella mallkällor — `page_template_source` för hela sidan, `header_source`/`footer_source` per slot — går i samma JSON-objekt. Assets följer med som base64 och skrivs till en temporärkatalog som lever precis så länge anropet gör det.

```json
{
  "template": "_block",
  "data": {"body": [{"type": "heading", "text": "Hej"}]},
  "header_source": "\\fancyhead[R]{\\includegraphics[height=1cm]{logo.png}}",
  "assets": {"logo.png": "<base64>"}
}
```

Svaret är `application/pdf`, eller ett fel vars `detail.type` är `input_error`, `validation_error`, `payload_too_large`, `render_error` eller `overloaded`. Schema- och blockfel bär dessutom `detail.path` — en lista som `["body", 1, "items", 0, "text"]` som pekar ut noden som fallerade.

| Miljövariabel | Betydelse |
|---------------|-----------|
| `KLARTEX_MAX_CONCURRENT` | Samtidiga xelatex-körningar. Fler samtidiga anrop får `503` med `Retry-After`. |
| `KLARTEX_MAX_BODY_MB` | Största begäran som läses. Kontrollen sker på `Content-Length` innan kroppen läses, så gränsen gäller den storlek anroparen uppger. |

Defaultvärdena står i `klartex/server/app.py`.

Tjänsten har varken autentisering eller rate limiting — den är ett kompileringslager och ska stå bakom en anropare som äger båda. Därför binder den till `127.0.0.1` om inget annat anges. Ett `latex`-block i indata kör godtycklig LaTeX i renderingsprocessen; kör tjänsten avskild från allt som inte tål det.

### Renderingstjänsten som image

Varje release publicerar också `ghcr.io/swedev/klartex-render:X.Y.Z` — samma pinnade bas som releasegrinden testar i, med releasens wheel-paket installerat. Taggen är alltid lika med klartex-versionen, och det finns ingen `latest`: pinna den version som motsvarar din `klartex==`-pin.

```bash
docker run --rm -p 127.0.0.1:8000:8000 \
  --read-only --tmpfs /tmp --tmpfs /home/render \
  ghcr.io/swedev/klartex-render:X.Y.Z
```

Imagen kör som icke-root och binder till `0.0.0.0` inuti containern — publicera porten bara på det nät anroparen finns på.

## Sidmallar (Page Templates)

En sidmall består av två oberoende delar: **header** (sidhuvud) och **footer** (sidfot). Varje del väljs för sig — en färdig variant, ett objekt med uppgifterna som ska stå där, eller `null` för tomt. Strukturerade inställningar fortsätter gälla för den del som är fördefinierad, även när den andra delen har egen LaTeX.

| Slot | Variant | Innehåll |
|------|---------|----------|
| `header` | `letterhead` | Organisationsuppgifter till vänster, logotyp till höger |
| `header` | `logo` | Enbart logotyp till höger |
| `header` | `null` | Tomt sidhuvud — sidhuvudets utrymme återtas |
| `footer` | `pagenumber` | Sidnummer centrerat, valfritt med dokumenttiteln före (`title`) |
| `footer` | `columns` | Flerkolumnsfot med företags-, kontakt- och betalningsuppgifter (`fields`) |
| `footer` | `null` | Tom sidfot |

En del som utelämnas får ytans default: blockmotorn har tomt sidhuvud och sidnummerfoten, recepten letterhead-sidhuvudet och sidnummerfoten med dokumenttiteln före sidnumret (`footer: {"variant": "pagenumber", "title": true}`). Ett recept kan deklarera egna defaultdelar: `faktura` och `kvitto` har kolumnfoten, med företag, adress, org.nr och betalningsuppgifter härledda ur `sender` och betalfälten i själva payloaden. Skickar producenten en egen kolumnfot vinner varje fält den sätter, fält för fält; en annan variant, `null` eller en egen källa används precis som den skickas. `klartex schema <mall>` beskriver mallens egen default.

```json
"page_template": {
  "header": {
    "variant": "letterhead",
    "fields": {
      "org_name": "Min Förening",
      "address": "Storgatan 1, 123 45 Stad",
      "web": "minforening.se",
      "email": "styrelsen@minforening.se",
      "logo": "logo.pdf"
    }
  },
  "footer": {
    "variant": "columns",
    "fields": {
      "company": "Min Förening",
      "org_number": "802000-0000",
      "bankgiro": "1234-5678"
    }
  }
}
```

```json
"page_template": { "header": "logo", "footer": null }
```

Objektformen av `letterhead` kräver `fields.org_name` — namnet är det som sidhuvudet byggs runt, och utan det skulle övriga uppgifter inte skrivas ut. Ett sidhuvud helt utan uppgifter anges som variantnamnet självt (`"header": "letterhead"`). `logo` är ett filnamn utan blanktecken och LaTeX-specialtecken; schemat anger mönstret. Kontaktkolumnen är smal och avstavar inte, så en lång `web` eller `email` radbryts efter `@`, `.` och `/` för att rymmas.

Utöver sloten finns inställningar på dokumentnivå — `font`, `header_font`, `diff_style` och `margins` — som gäller oavsett om en slot har egen LaTeX, plus `page_numbers` och `first_page_header`.

### Marginaler

`margins` anger avståndet från papperskanten till **brödtexten**, en nyckel per sida. Varje nyckel är valfri och verkar för sig; värdet är ett LaTeX-mått med utskriven enhet (`cm`, `mm`, `pt`, `in`).

```json
"page_template": {
  "margins": { "top": "3.4cm", "bottom": "2cm", "left": "3cm", "right": "3cm" }
}
```

Chromet anpassar sig efter måtten i stället för tvärtom: `top` mäts till första textraden, så med ett sidhuvud står bandet kvar där det står och glappet mellan sidhuvud och text växer eller krymper — därför måste `top` överstiga bandets nederkant (måttet står i schemabeskrivningen, och laddaren avvisar ett för litet värde). Är sidhuvudet tomt (eller saknar innehåll) återtas dess utrymme och vilket positivt `top` som helst fungerar. `bottom` mäts till sista textraden och sidfoten hänger under den, så lämna plats åt den — ett litet värde klipper foten. `left` och `right` flyttar även sidhuvudets och sidfotens band, som följer textbredden.

En slot med egen LaTeX som sätter sin egen geometri vinner över `margins`, precis som den gör över `font`.

### Egen sidmall

Rå LaTeX skickas som fil eller text, inte i JSON. En fil kan äga hela sidan, eller en slot i taget:

```bash
klartex -d data.json --page-template sidmall.tex.jinja
klartex -d data.json --header-template sidhuvud.tex.jinja
klartex -d data.json --header-template sidhuvud.tex.jinja --footer-template sidfot.tex.jinja
```

```python
render("_block", data, page_template_source=Path("sidmall.tex.jinja").read_text())
render("_block", data, header_source=Path("sidhuvud.tex.jinja").read_text())
```

`--page-template` äger båda slotarna och kan inte kombineras med slot-flaggorna. Slot-filerna måste ligga i samma katalog — den katalogen blir mallkatalogen som filer hittas relativt till.

Utan mallflagga letar klartex själv: först `<data-filens-stam>.tex.jinja` bredvid datafilen, sedan `page_template.tex.jinja` i arbetsmappen. Hittas en sådan fil används den som helsidesmall, och sökvägen skrivs på stderr. En slot-flagga stänger av autodetekteringen.

Inställningarna på dokumentnivå i `data.page_template` (`font`, `header_font`, `diff_style`, `margins`) gäller oavsett form och skrivs ut före mallens egen LaTeX, så mallens `\geometry` och `\setmainfont` vinner. `header` och `footer` i JSON läses inte när en helsidesmall är satt.

En mallfil definierar sitt eget chrome:

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

- **CLI med filbaserad sidmall** (`--page-template`, `--header-template`, `--footer-template`, samt en autodetekterad mall): filer hittas relativt till mallfilens egen katalog, med arbetsmappen som fallback. En mall och dess logotyper kan därmed ligga samlade i t.ex. en `Branding/`-mapp och användas från vilken arbetsmapp som helst. För en symlänkad fil gäller målets katalog.
- **API med `page_template_source`, `header_source` eller `footer_source`**: parametrarna tar rå text utan sökväg, så det finns ingen mallkatalog att utgå från. Anropare som vill hitta filer utanför arbetsmappen skickar `asset_dir=<katalog>` till `render()`; annars gäller arbetsmappen.

> **Både `\includegraphics{logo.pdf}` och `\includegraphics{./logo.pdf}` fungerar**, liksom `\input{../delat/farger.tex}` — relativa referenser utgår från mallens katalog (eller `asset_dir`, i annat fall arbetsmappen). En skillnad finns dock: namn med `./` eller `../` faller **inte** tillbaka på arbetsmappen. TeX:s filsökning (Kpathsea) söker aldrig upp sådana namn, utan provar dem rakt av mot xelatex arbetskatalog — och den katalogen är just mallens katalog. Namn utan prefix söks däremot i hela kedjan och hittas även om filen bara ligger i arbetsmappen.

## Arkitektur

Klartex har en trelagers-arkitektur:

1. **Dokumentnivå** — `klartex-base.cls` hanterar siduppställning och grundläggande sidhuvud/sidfot. Sidmallar (`.tex.jinja`) injiceras i preambeln och styr färger, logotyp och layout.
2. **Komponentnivå** — Återanvändbara `.sty`-paket som ger strukturerade LaTeX-makron (t.ex. `klartex-signatureblock.sty`, `klartex-callout.sty`, `klartex-agenda.sty`)
3. **Receptnivå** — YAML-filer som deklarerar vilka komponenter och innehållsfält som ska kombineras

### Renderingsvägar

- **Recipe-mallar** (alla namngivna mallar i `klartex templates`) — YAML-recept som deklarerar komponenter och mappningar
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
  metadata:
    - label: "Datum:"
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

Komponenterna är registrerade i `klartex/components.py`; de som har ett blockschema är också blockmotorns blocktyper (`klartex blocks`). De befintliga recepten i `klartex/templates/*/recipe.yaml` är de kompletta exemplen.

## Årsmötespaket

Blockmotorn kan komponera alla dokument som behövs för ett föreningsårsmöte — kallelse med dagordning, verksamhetsberättelse, årsredovisning, revisionsberättelse, budget, valberedningens förslag, motioner och styrelsens yttranden. Agenten väljer och ordnar block för varje dokument; inga separata mallar behövs. `tests/fixtures/block_*.json` är fullständiga exempel.

## Licens

MIT
