# Changelog

## 0.19.0 — 2026-09-03

### Breaking changes
- **Faktura och kvitto: det egna toppnivåfältet `footer` är borttaget.** Kontakt- och betalningsuppgifter skickas under `page_template.footer.fields` (variant `columns`) — den vanliga sidfotsslotten är den enda platsen. Ett toppnivå-`footer` avvisas av schemat med ett felmeddelande som pekar på slotten (`detail.path == ["footer"]` i `klartex serve`); `_footer_macros.tex.jinja` och template-nivåns `emit_kxfooter` är borta, och `footer_has_payment` (signalen som undertrycker `payment_info` i brödtexten) läser enbart slotten. `klartex example faktura`/`kvitto` visar slotformen. (#79)
- **Faktura och kvitto: `sender` med `name` är obligatoriskt.** En faktura utan avsändare är ingen faktura. Utan `logo` sätts `sender.name` som ordmärke i logotypplatsen, i linje med FAKTURA/KVITTO-rubriken; med `logo` ändras inget. Avsändare-blocket bredvid mottagaren är kvar. (#99)

### New features
- **Kolumnfoten renderas alltid i faktura och kvitto, med saknade uppgifter markerade.** Receptens default-sidfot är `columns`, härledd från payloaden via `fields_from` i recipe.yaml (`sender.name`/adress/orgnr, `bankgiro`/`plusgiro`/`iban`/`bic`) och mergad nyckel för nyckel under en `page_template.footer` som producenten själv skickar. Varje kolumn renderas även utan innehåll — luckan namnges i kolumnens egen typografi i grått (`kxmuted`, `#6B6A63`): *Betalningsuppgifter saknas*, *Org.nr saknas*, *Adress saknas*. Ingen hård validering; ett explicit `footer: null`, `pagenumber` eller egen sidfotskälla respekteras. Etikettläget är receptstyrt (`document.label_missing_footer_fields`) och påverkar inte blockmotorns `columns`-fot. `klartex schema faktura` beskriver härledningen; registret laddar varje recept vid uppstart, så en ogiltig `recipe.yaml` felar vid discovery i stället för vid första rendering. (#99)

### Fixes
- **Långa e-postadresser och URL:er i letterhead-sidhuvudet bryts inuti kolumnen.** Letterheadens `web` och `email` får brytmöjligheter efter varje följd av `@`, `.` och `/` (aldrig i slutet av värdet, så `https://` hålls ihop), så ett obrytbart token längre än kontaktkolumnen inte längre rinner över minipagen. Fragment, goldens och JSON-ytan är oförändrade; sidhuvudet får växa upp till sju kontaktrader i standardgeometrin, låst av test. (#98)
- **Trailing newline avvisas i logotypfilnamn.** `FILENAME_PATTERN` exkluderar all whitespace och ankras med absolut slut, och laddaren gör `fullmatch` på `logo`-fältet — `"logo.pdf\n"`, `"logo.pdf\r"` och `"logo.pdf x"` avvisas av både schema och laddare. Ett filnamn med mellanslag (`"my logo.pdf"`) är därmed inte längre giltigt. (#97)

## 0.18.0 — 2026-09-01

### Breaking changes
- **Svart default-chrome.** `brandprimary` och `brandsecondary` defaultar båda till `#000000` (tidigare `#1A1A1A` respektive `#666666`), klassbrett — sidhuvud, sidfotslinje och sidfotstext renderar svart i stället för grått, och länkar (`linkcolor`/`urlcolor` = `brandprimary`) blir svarta. Omdefinierbart som förut via `\definecolor` i egen källa. (#86)
- **Faktura/kvitto får tätare geometri via klassoptionen `narrowmargins`.** De två recepten sätter `document.class_options: narrowmargins` i sina recipe.yaml, vilket ger 2 cm sidmarginaler och 1,7 cm återtagen topp; alla andra dokumenttyper behåller klassdefaulterna 3 cm/2 cm. Explicita `page_template.margins` i payloaden overridar optionen per nyckel. (#86, #88)
- **`logo_height`-default 0,8 cm → 1 cm** i faktura och kvitto (delad fallback i `_recipe_base`); `klartex example faktura`s footer följer den godkända fältformen (`web` borttagen). (#86)

### New features
- **Sidmarginaler på sidmallsytan.** `page_template.margins` tar `top`/`bottom`/`left`/`right` som strikta dimensionssträngar (`cm|mm|pt|in`) och komponerar med sidchromet i stället för att vara fyra råa tal: `top` tolkas som textblockets marginal och emitteras för båda chrome-regimerna (justerar `headsep` när sidhuvud finns, omdefinierar `\kxreclaimtop` när det återtas), och footer-bandets geometri är sent bunden via `\kxfooterbottom`/`\kxfooterfootskip` så `margins.bottom` inte skrivs över av `\kxfooter`. Subträdet genereras in i alla mallscheman. (#65)
- **Garanterad fontuppsättning i renderingsmiljön.** `GUARANTEED_FONTS` — 16 familjer (MS core: Arial, Courier New, Georgia, Times New Roman, Trebuchet MS, Verdana; öppna: EB Garamond, IBM Plex Mono/Sans/Serif, Inter, Lato, Noto Sans, Noto Serif, Open Sans, Roboto) — genererar `font`/`header_font`-beskrivningarna i schemat, verifieras exakt i basimage-bygget (`docker/guaranteed-fonts.txt`, bevakad av workflow-filtren) och testas per familj via `KLARTEX_REQUIRE_FONTS`. Baspinnen flyttad till `klartex-base:20260831-12`. (#83)
- **Externa fonter per anrop.** `font` och `header_font` tar en filform — `{"file": "Inter-Regular.ttf", "bold": …, "italic": …, "bold_italic": …}` — som emitterar `\setmainfont{…}[Path=./, …]`; utelämnad face faller tillbaka på regular utan syntes. Filnamn valideras escape-invariant, en preflight kontrollerar att varje refererad face finns i asset-roten (fel före xelatex-kravet, mappat till strukturerad 400 i `klartex serve`), och fontfiler reser som vanliga base64-`assets`. (#83)
- **Helsidesmallen är tillbaka.** En `.tex.jinja` som äger båda slotarna: `page_template_source` på `render()` och `POST /render`, `--page-template` på CLI:t, plus autodetektering av `<stem>.tex.jinja`/`page_template.tex.jinja` bredvid datafilen (kräver riktig fil; slot-flaggor undertrycker den; `Using page template: <path>` på stderr). Dokumentnivå-inställningarna (`font`, `header_font`, `diff_style`, `margins`) fortsätter gälla bredvid källan, och kombination med per-slot-källa avvisas i en central kontrollpunkt (`ValueError` → CLI-fel/`400 input_error`). (#85)

### Fixes
- **Letterhead-sidhuvudet kolliderar inte längre.** Kolumnerna breddade till 0,30 + 0,25 `\textwidth` med 0,03-mellanrum, `\raggedright` och avstavning av i båda — långa adresser blöder inte in i kontaktkolumnen, inga utsträckta ordmellanrum, inga avstavade orgnamn. (#84)
- **Serverisolering för filform-fonter.** Ett anrop med filform-font utan övriga assets etablerar nu per-request-asset-roten, så en fil i serverprocessens cwd aldrig kan bäddas in oombedd. (#83)
- **Trailing newline avvisas i dimensions- och fontfilnamnssträngar** — `$`-ankaret ersatt med absolut slut (`fullmatch` + portabelt schemamönster), så `"2cm\n"` varken passerar validering eller läcker in i LaTeX. (#65, #83)

## 0.17.0 — 2026-08-30

### Breaking changes
- **Sidmallsytan är helt omgjord — inga alias, inga platta fält, ingen helsideskälla.** `page_template` är enbart ett objekt: `formal`/`clean`/`none` och `name`-nyckeln är borttagna (en utelämnad slot får ytans default — blockmotorn tomt sidhuvud + `pagenumber`-fot, recepten `letterhead` + `pagenumber` med dokumenttiteln). Slot-innehåll ligger under `fields` och ett slot-objekt kräver `variant`; `letterhead`-objektformen kräver `fields.org_name`, och `logo`-filnamn valideras mot ett mönster utan LaTeX-specialtecken. Sidfoten är två varianter: `pagenumber` (inställning `title` — dokumenttiteln före sidnumret) och `columns` (flerkolumnsfoten, `fields` med företags-, kontakt- och betalningsuppgifter). Helsideskällan är borta: `page_template_source` (API), `--page-template` (CLI) och autodetekteringen av `<stem>.tex.jinja`/`page_template.tex.jinja` — egen LaTeX är alltid per slot (`header_source`/`footer_source`, `--header-template`/`--footer-template`). Slot-modellen är typad och definierad på ett ställe i `page_templates.py`; `page_template`-subträdet i alla mallscheman genereras därifrån. Schemabeskrivningarna är nu på engelska (schemat är agentens upptäcktsyta); svenska domäntermer och PDF-strängar står kvar. Ett partiellt `document.page_template` i en recipe.yaml faller tillbaka per slot i stället för att krascha. (#80)

### New features
- **`klartex serve` och `ghcr.io/swedev/klartex-render:X.Y.Z`.** Det interna kompileringslagret bor nu i kärnan: `klartex/server/` (FastAPI, flyttad från klartex.se och anpassad till slot-API:t) exponeras som `klartex serve` bakom nya extran `serve`. Kontrakt (internt v1): `POST /render` med `template`, `data`, valfria `header_source`/`footer_source` och base64-`assets` → PDF; strukturerade fel (`400 input_error`/`validation_error` med block-path, `413`, `500`, `503` med `Retry-After`); `GET /health` med kärnans version; konfiguration enbart via env (`KLARTEX_MAX_CONCURRENT`, `KLARTEX_MAX_BODY_MB`). Varje release publicerar `docker/Dockerfile.render` som `ghcr.io/swedev/klartex-render:<version>` (multi-arch, byggd på den pinnade basimagen, aldrig `latest`) via ett nytt `image`-jobb i release-workflowen. Imagen kör som icke-root och tål `read_only: true` med tmpfs `/tmp` och tmpfs-HOME. (#81)

## 0.16.0 — 2026-08-30

### Breaking changes
- **Inline-markup tolkas nu i alla textbärande block.** `description_list` (`value`), `agenda` (`title`, `discussion`, `decision`, `decisionLabel`, `subItems[]` — på både blockmotorn och protokoll-receptet), `name_roster` (`title`, `name`, `role`, `note`), `title_page` (`party1`, `party2`, `title`) och `signatures` (`header`, `name`, `signatory`, `title`) passerar `| inline`-filtret som övriga block: `**fet**`, `*kursiv*`, `` `kod` ``, typografiska citattecken efter dokumentspråk och ändringsmarkörerna `{+…+}` / `[-…-]`. Producenter som skickar literala markup- eller markörtecken i dessa fält får dem tolkade. Fält som sitter som makroargument (`title_page`, `signatures`, `name_roster` utom `role`) kollapsar radbrytning till mellanslag; `agenda`-fälten och `name_roster.role` bryter rad. Schemabeskrivningarna anger vad som gäller per fält. (#47, #60, #69)
- **Sidmallen är två slots: `header` och `footer`.** `page_template` accepterar nu `{"header": …, "footer": …}` där varje slot var för sig är en fördefinierad variant (header: `letterhead`, `logo` eller tom; footer: `standard`), en egen `.tex.jinja`-källa eller tom — och strukturerade overrides fortsätter gälla för den slot som förblir fördefinierad. `formal` / `clean` / `none` finns kvar som alias för motsvarande slot-kombinationer och renderar identiskt (låst av golden-tester mot förra versionens preamble); befintliga `footer`-objekt är oförändrat giltiga. Nytt: `letterhead` tar strukturerade fält `org_name` (obligatoriskt i objektformen), `address`, `web`, `email`, `phone`, `logo`, så orgdetaljer i headern inte längre kräver en egen mall. API: `render(header_source=…, footer_source=…)`; CLI: `--header-template` / `--footer-template` (ömsesidigt uteslutande med `--page-template`, båda filerna i samma katalog). Beteendeändringar: `font`, `header_font` och `diff_style` gäller nu även tillsammans med en egen källa (var tidigare tyst verkningslösa); kontraktsmakrona `\orgname`, `\orgaddress`, `\orgwebsite`, `\orgemail`, `\orgphone`, `\brandlogo` är `\providecommand`-ade i `klartex-base.cls`, så en egen källa som använder `\newcommand{\orgname}` får "already defined" — använd `\providecommand` + `\renewcommand` som README anger; `PageTemplate.footer` är en `SlotSpec`, och `prepare_*_context` emitterar inte längre `page_template_source` / `external_page_template`. `logo` valideras mot ett mönster som avvisar LaTeX-specialtecken i filnamnet. (#63)

### New features
- **Renderingsmiljön ägs av repot.** `docker/Dockerfile.base` publiceras som `ghcr.io/swedev/klartex-base` av `base-image.yml`, som kör hela testsviten i den nybyggda imagen före push. `publish.yml` kör sviten i den pinnade imagen som release-gate, så en version når PyPI först efter att ha passerat i produktionsmiljön. (#55)
- **Protokoll: `subItems` på `agenda_items[]` är dokumenterat.** Fältet accepterades och renderades redan (decimal underpunkter `3.1.`, `3.2.` efter punktens diskussion och beslut) men fanns inte i schemat. Nu är det del av kontraktet, med i `klartex example protokoll`, och låst av tester. Felformade värden (`"subItems": "text"`, `[123]`) som tidigare passerade som okända nycklar avvisas. (#70)

### Fixes
- **Ett stycke längre än en sida bryts nu över sidgränsen.** `\widowpenalties 2 10000 10000` / `\clubpenalties 2 10000 10000` i `klartex-base.cls` saknade avslutande `0`, och eTeX låter arrayens sista värde gälla alla följande rader — oändligt straff på varje radbrytpunkt i varje stycke, så ett stycke högre än textytan spillde ut förbi nederkanten och klipptes tyst (overfull `\vbox`, innehåll förlorat). Arrayerna avslutas nu med `0`; 2-raders änka/horunge-skyddet är oförändrat. Stycken på ≤4 rader förblir obrytbara, avsiktligt. Låst av ett `pdftotext`-test som verifierar att styckets sista ord når sista sidan. (#49)

## 0.15.0 — 2026-08-28

### New features
- **Ändringsmarkering.** Dokument som visar vad som ändrats mellan två versioner — kanoniskt fall: stadgeändringar — markeras nu inline i `git diff --word-diff`-notation: `{+tillagt+}` renderas grönt och `[-struket-]` rött med genomstrykning. Markörerna gäller i alla fält som passerar `| inline`-filtret, alltså även i tabellceller. Nya `klartex-changes.sty` äger utseendet via de omdefinierbara hookarna `\kxaddedstyle` / `\kxremovedstyle`, och laddas från `klartex-base.cls` så markeringen fungerar på både blockmotorn och recept-vägen. För hela stycken finns `revision: "added" | "removed"` på `text`-blocket. Kanoniskt exempel: `tests/fixtures/block_stadgeandring.json`. (#40)
- **`diff_style` i sidmallsobjektet.** `page_template: {"diff_style": "underline"}` markerar tillagd text med grön understrykning i stället för enbart grön text; struken text är överstruken i båda fallen. Understruket tillägg mot överstruken strykning är konventionen i ändringsdokument, och till skillnad från färg överlever den svartvit utskrift. Default är `"color"`. Understrykningen ritas av `ulem`, som redan laddas — inget nytt beroende. (#40)

### Fixes
- **Kantblanksteg i `{+ tillagt +}` försvinner inte längre.** `\textcolor` kastar ett blanksteg först i sitt argument, så ett mellanslag författaren skrev föll bort ur utdatan utan spår. Blanksteg och tabbar i markörinnehållets kanter emitteras nu utanför makrot. `[-struket-]` behåller sina — ett mellanslag inuti en struken passage är en del av det som strukits, och den som vill ha det utanför strykningen skriver det utanför markören.
- **Installationsinstruktionerna listar alla TeX-paket som krävs.** `apt install texlive-xetex` räcker inte — bland annat `ulem`, `tcolorbox` och `siunitx` saknas, och den som följde instruktionen fick ett LaTeX-fel som inte namngav det saknade paketet. README anger nu samma paketuppsättning som CI installerar, alltså den hela testsviten körs mot. (#48)

## 0.14.0 — 2026-08-27

### New features
- **Svenskt talformat i recept.** Nya Jinja-filter `money`/`num` renderar belopp svenskt som default (`32 400,00` — smala mellanslagsgrupper, decimalkomma) i stället för det tidigare hårdkodade engelska formatet. Dokumentets språk avgör stilen; `number_format` (`sv`/`en`) i faktura-/kvitto-data överstyr. `num` använder `.10g` så stora kvantiteter inte slår över i exponentnotation. (#41)
- **Sidmallsoptioner i alla recept-scheman.** `page_template` accepterar objektform (som i block-motorn) med nya `font` och `header_font` (fontspec-familjenamn; `header_font` faller tillbaka på `font` via `\kxheaderfont` i `klartex-base`) samt `footer`. Footern renderas av nya `klartex-footer.sty` (`\kxfooter`): tre justerade kolumner (Adress | Företag | Betalning), bottenankrade mot fotens baslinje så höga footrar växer uppåt, radbruten postadress (sträng eller array av rader), språkmedvetna etiketter och sidnummer bara när dokumentet är längre än en sida. (#42)
- **Faktura: avsändare, footer och logga.** Fakturan bär ett eget `footer`-fält på toppnivå — den kanoniska platsen för betalningsuppgifter, med företräde framför sidmallens footer; `payment_info`-blocket i brödtexten är en dokumenterad fallback som undertrycks när en footer har betalningsuppgifter (och renderar inget alls utan data). Nya `sender` (Avsändare-block bredvid Mottagare, med referenser under) och `logo`/`logo_height`/`logo_offset` (toppjusterad med FAKTURA-rubriken, offset i andelar av loggans höjd). FAKTURA-kolumnen är vänsterställd och delar mottagarkolumnens vänsterkant. (#41, #42)
- **Kvitto: avsändare, header-logga och footer** — samma behandling som fakturan: valfri `sender`, `logo`/`logo_height`/`logo_offset` i headern och `footer` på toppnivå. Header och referensrader är utbrutna till delade `doc_header`/`invoice_refs`-makron som faktura och kvitto delar, och `invoice_recipient` renderar avsändar-only-layouter (tom högerkolumn) respektive ingenting alls utan data — ingen tom Mottagare-etikett längre.

### Fixes
- **Vänsterställda rubriker sätts ragged-right.** Ett utslutet stycke i rubrikstorlek har för få brytpunkter per rad, så TeX överfyller i stället för att bryta tidigt och sista ordet sticker ut i högermarginalen. `textAlign: "left"` (default) sätter nu `\raggedright`; center/right är oförändrade.

## 0.13.0 — 2026-07-25

### New features
- **Ny recipe-template: `kvitto`.** Betalningsbekräftelse, medvetet lättare än faktura: kvittonummer, datum, enkel artikellista, en explicit totalsumma (`total_amount`, beräknas aldrig från raderna) och betalsätt. Ingen momsspecifikation, inget förfallodatum. Två nya recipe-only-komponenter (`receipt_header`, `receipt_table`); Betalsätt/Betalt av via `description_list` + valfri metadata. Säljaridentitet kommer från sidmallen (`\orgname`). `klartex example kvitto` fungerar via auto-discovery. (#8)
- **Block spacing-overrides: per-instans-fält + dokumentnivåns `block_settings`.** Sju block (`heading`, `text`, `list`, `table`, `callout`, `quote`, `description_list`) accepterar nu `spacing_before`/`spacing_after` (råa LaTeX-dimensioner, t.ex. `"2em"`; `"0em"` tar bort default-spacing). Upplösningsordning: per-instans > `block_settings[type]` > inbyggd default. Rent additivt — befintliga dokument renderas oförändrat. (#29)

### Fixes
- **Sidmallars assets löses nu mot mallens katalog i stället för cwd.** `\includegraphics{logo.pdf}` m.m. i en extern sidmall (`--page-template` eller auto-detekterad) krävde tidigare att asseten kopierades till build-cwd. CLI:t skickar nu mallfilens katalog som `asset_dir`, och `_compile_tex` kör xelatex med `cwd=asset_root` + `-output-directory`, så både bara filnamn (via `TEXINPUTS`) och explicit relativa sökvägar (`./logo.pdf`, `../shared.tex` — som Kpathsea aldrig söker `TEXINPUTS` för) hittas bredvid mallen; cwd är fallback. Beteendeförändringar: en asset som finns både bredvid mallen och i cwd löses nu till mallens kopia; ogiltig `asset_dir` ger `ValueError` i stället för tyst no-op; utan `asset_dir` löses `./`-namn mot processens cwd (tidigare alltid fel, mot en privat tempdir). (#37)
- **`_recipe_base`: `description_list`-armen är nu guardad med `if metadata`** — ett recept utan metadata renderar ingenting i stället för ~4em spacing runt en tom tabell. No-op för protokoll som alltid har metadata. (del av #8)

## 0.12.0 — 2026-07-06

### Breaking changes
- **`signatures`: avtalsingressen är nu opt-in via `contract_intro: true`.** Tidigare renderades "Detta avtal har upprättats i två (2) likalydande exemplar, av vilka parterna tagit var sitt." automatiskt så fort `parties` hade exakt två poster — även i protokoll, berättelser och andra icke-avtal. Nu krävs `contract_intro: true` (schema v0.3, default false). Tvåparts-avtal som förlitade sig på heuristiken behöver lägga till flaggan.
- **Valideringsfel refererar nu `body[i]`-paths i stället för `index i`.** Felmeddelanden som tidigare löd `Invalid 'text' block at index 2` lyder nu `Invalid 'text' block at body[2]`; nästlade block får full path, t.ex. `body[0].content[1]`. Konsumenter som parsar felsträngar behöver uppdateras.

### New features
- **Nästlade block valideras mot sina scheman.** Block i `clause.content[]`, `list.items[].content[]` och `columns.items[][]` validerades tidigare bara på `type`-nivå — ett nästlat block med saknade obligatoriska fält kraschade i Jinja eller renderade tyst tomt. Nu valideras hela trädet rekursivt med path i felmeddelandet. Nästlingsbärarna är utbrutna till en delad hjälpare (`_child_block_lists`) som även escape/restore-passet använder.
- **`parties`: `signatory` renderas.** Fältet fanns i schemat men tappades tyst. Renderas som "Företräds av: …" under adressen; skippas när det är identiskt med partsnamnet (samma konvention som signaturpanelen).
- **`table`: `align` fungerar nu tillsammans med fast `width`.** `{"width": "3cm", "align": "right"}` gav tidigare vänsterställd kolumn; nu emitteras `>{\raggedleft\arraybackslash}p{3cm}`.
- **`title_page` hanterar utelämnade parter.** Med bara `title` renderades tidigare "Och" och tomma partsrader; nu renderas enbart titeln, och en ensam part visas utan "Och".

### Fixes
- **Radbrytningar (`\n`) i tabell- och formulärceller korrumperar inte längre tabellen.** `inline`-filtret gjorde `\n → \\` ovillkorligt; med `\arraybackslash` avslutar `\\` tabellraden, så en cell med radbrytning klippte raden och förskjöt resten av tabellen (i header-celler: kompileringsfel). Celler använder nu `\newline` (paragraph-kolumner) respektive mellanslag (LR-kolumner i formuläretiketter).
- **Faktura utan `currency` skrev "None" i totalsummorna.** `extract_component_data` sätter `None` för saknade data_map-paths, så mallens dict-get-default triggades aldrig. Nu faller tomt värde tillbaka till "SEK".
- **CLI: vänliga felmeddelanden i hela flödet.** Trasig JSON (stdin eller fil), katalog som `-d`-path och oskrivbar `-o`-path ger nu `Error: …` + exit 1 i stället för tracebacks; skrivfelet slog tidigare till efter en lyckad rendering så PDF-bytesen gick förlorade.
- **xelatex-timeout ger `RuntimeError` och höjs 30 → 60 s.** `subprocess.TimeoutExpired` läckte tidigare rått genom `render()`-kontraktet; kall fontcache i en färsk container kunde ensam överskrida 30 s.
- **`formal`-sidmallens footer skriver ingen ledande punkt när dokumentet saknar titel.**
- **All fil-I/O använder `encoding="utf-8"`** oberoende av värdens locale.

## 0.11.2 — 2026-07-06

### Fixes
- **`columns`: top-alignment fungerar nu även när första elementet i en kolumn är en bild (eller annat baseline-på-botten-element).** `\begin{minipage}[t]` alignar första radens *baseline*, inte visuella toppen. När en kolumn börjar med `\includegraphics` ligger den baselinen vid bildens **undre** kant, så en bild-vänster/text-höger-layout placerade textens första rad nere vid bildens nederkant — såg ut som om kolumnerna var center-aligned, men var i själva verket korrekt baseline-aligned mot fel referenspunkt. Lägger till `\null\vspace{-\baselineskip}` i varje minipage så de börjar med en text-baseline överst. Osynligt för text-text- och heading-cases (verifierat).

## 0.11.1 — 2026-05-11

### New features
- **`render(asset_dir=...)`-parameter.** `klartex.render()` accepterar nu en valfri `asset_dir: Path | str | None`. Katalogen läggs in i `TEXINPUTS` mellan den bundlade `cls/`-mappen och anroparens cwd, så `\includegraphics`, `\input`, custom fonts m.m. i en sidmall hittas där utan att anroparen behöver `chdir`. Tänkt huvudanvändning: serverlager (t.ex. `klartex.se`) som slår upp namngivna sidmalls-bundles i en lokal katalog och vill peka klartex på den utan globala sidoeffekter.

## 0.11.0 — 2026-05-11

### Breaking changes
- **HTTP-server borttagen ur kärnpaketet.** `klartex serve`-kommandot, `klartex/main.py` (FastAPI-appen) och `fastapi`/`uvicorn`-beroendena är raderade. Konsumenter som behöver en HTTP-yta får importera `klartex` som library i ett eget webblager (det är vad `klartex.se` gör). Inga andra kända konsumenter — clean break utan deprecation-period.
- **Docker-image borttagen.** `Dockerfile`, `docker-compose.yml` och `.github/workflows/docker.yml` raderade — imagen fanns enbart för att paketera HTTP-servern. `ghcr.io/swedev/klartex:0.10.1` är sista publicerade taggen och kommer inte uppdateras. Använd `pipx install klartex` eller importera som library.

### Fixes
- **`xelatex` körs nu med `-no-shell-escape`.** Stänger `\write18` och shell-exekvering från `.tex`-källan. Relevant när uppströmskonsumenter (t.ex. `klartex.se`) renderar användaruppladdade sidmallar — utan flaggan kunde en manipulerad page template köra godtyckliga shell-kommandon under kompilering.

## 0.10.1 — 2026-05-11

### Fixes
- **Docker build:** replace standalone `tabularx` tlmgr package with `tools` bundle. TeX Live 2026 no longer ships `tabularx` as its own tlmgr package (rolled into the `tools` LaTeX bundle), so the v0.10.0 Docker image failed to build with `tlmgr install: package tabularx not present in repository`. PyPI v0.10.0 is unaffected. GHCR `ghcr.io/swedev/klartex` first becomes available at this version.

## 0.10.0 — 2026-05-11

### Breaking changes
- **`signatureblock` recipe component removed.** Use the `signatures` block instead — same `.sty` underneath, but the block supports N parties, configurable columns, and custom headers. No live recipe used `signatureblock`.
- **`klausuler` recipe component removed.** Use the `agenda` block with `numberingStyle: "decimal"`. The `protokoll` recipe is migrated accordingly; custom recipes using `klausuler` should switch to `agenda` (items already use the same `{title, discussion, decision}` shape).
- **`titelsida` recipe component removed.** Use the `title_page` block. No live recipe used it.
- **Recipe `text` component now parses inline markup.** Strings like `**bold**` or `*italic*` in recipe text data are rendered as formatting instead of literal asterisks. Escape with `\*` for literal output.
- **`prepare_recipe_context` joins list-typed metadata values to strings.** Direct callers that expected `metadata[].value` to sometimes be a list (e.g. `attendees`, `adjusters`) now always receive a comma-joined string.

### New features
- **Multi-arch Docker image published to GHCR on release.** `vX.Y.Z` tags trigger `.github/workflows/docker.yml`; image pushed to `ghcr.io/swedev/klartex` for `linux/amd64` + `linux/arm64` with tags `X.Y.Z`, `X.Y`, and `latest`. Pull: `docker run --rm -p 8000:8000 ghcr.io/swedev/klartex:latest`.
- **CLI auto-detects page templates.** When `--page-template` is omitted, klartex looks for `<data-stem>.tex.jinja` next to the data file, then `./page_template.tex.jinja` in cwd. Explicit `--page-template` still wins.
- **`agenda` block gains `numberingStyle`, `decisionLabel`, and per-item `subItems`.** `numberingStyle: "section"` (default, §-prefix) or `"decimal"` (1., 2., …). Per-item `subItems: string[]` renders decimal sub-numbering (1.1., 1.2., …). `decisionLabel` overrides the default "Beslut:".
- **`heading` block gains `textAlign`.** Values `"left"` (default), `"center"`, `"right"`. Universal heading alignment usable in any block-engine document.
- **Recipe rendering deduplicated via shared macros.** New `_block_macros.tex.jinja` holds the canonical implementations of `agenda`, `heading`, and `description_list`; both `_block_engine.tex.jinja` and `_recipe_base.tex.jinja` import from it. `_recipe_base.tex.jinja` shrinks from 195 → 141 lines.

### Spacing
- **Recipe headings now go through `render_heading`.** Recipe-rendered headings (protokoll, faktura, etc.) gain orphan protection (`\kxneedspace`) and parskip cancellation, matching block-engine heading semantics. Visual output is *not* pixel-identical to v0.9.8 — spacing above headings is slightly looser and orgname/subtitle metadata lines render as separate centered blocks rather than line-broken inside one group. Documents that were pixel-tuned to v0.9.x recipe output may need a re-look.

## 0.9.8 — 2026-05-06

### Breaking changes
- **`clause`: label no longer auto-appends a period.** The renderer used to hard-code a `.` after `block.number`, so `"§ 7"` rendered as `§ 7.` and `"a)"` would have become `a).`. The number string is now passed through verbatim — `"§ 7"` → `§ 7`, `"a)"` → `a)`. To get the dotted form, write `"§ 7."` in the `number` field. Migration: existing documents using `"§ N"` style numbers should be updated to `"§ N."` if the period is wanted in the rendering.

## 0.9.7 — 2026-05-06

### Spacing
- **`signatures`: inter-row vspace 0.5cm → 1cm.** v0.9.6's combined fixes (empty-title pane shorter + row-gap halved) overshot — rows visually too tight. Back to 1cm gap between rows. Header `\vspace{0.5cm}` stays for the tight top rhythm.

## 0.9.6 — 2026-05-06

### Fixes
- **`signatures`: empty `title` no longer reserves a phantom line of vertical space.** The trailing `\\[0.25cm]` in `\kxsignaturepane` ran unconditionally before `\kx@signatory@line`, so even when no signatory text was rendered, a full line's worth of vertical space was still reserved at the bottom of each pane. The line break is now emitted *inside* `\kx@signatory@line`, only when there is actual content (party≠signatory or non-empty title) — empty signatory line now takes zero vertical space.

### Spacing
- **`signatures`: uniform 0.5cm rhythm.** Section header now has `\vspace{0.5cm}` below (was using only `\section*`'s default 12pt, mismatching the row gap). Inter-row vspace 1cm → 0.5cm. `new_page: false` preceding margin 1cm → 0.5cm. The whole block now has consistent 0.5cm vertical breathing space between header, intro, and signature rows.

## 0.9.5 — 2026-05-06

### New features
- **Inline `\n` → LaTeX line break.** Literal newlines in JSON strings (`"line 1\nline 2"`) now render as in-paragraph line breaks. Applies to all inline-filtered text fields (heading, text, clause text, callout, quote, etc.). For separate paragraphs, use separate text blocks.

### Fixes
- **`heading`: orphan-protection generalized.** v0.9.4 only suppressed the competing `\kxneedspace` for clause→clause. The same orphan mechanic also affected heading→clause and heading→heading: the second block's own `\kxneedspace` lured TeX into breaking between them. The top-level body loop now tracks the previous block type; when the previous block was a `heading`, the next clause or heading suppresses its `\kxneedspace`.

### Spacing
- **`callout`: top/bottom margin bumped from 1em to 1.5em** (50%) so callouts breathe properly between adjacent paragraphs.
- **`heading`: tighter line height for multi-line wrap.** Headings now wrap their text in `\setstretch{1.1}` so multi-line titles don't inherit the document's default 1.3 line stretch — fixes the visually loose 2-line wrap.

## 0.9.4 — 2026-05-04

### Fixes
- **`clause`: title orphan finally fixed by suppressing the first sub-clause's `\kxneedspace`.** Earlier patches (v0.9.2 `\nopagebreak[4]`, v0.9.3 bumped needspace value) didn't address the actual root cause: the parent's `\kxneedspace` and the first sub's `\kxneedspace` both emit `\penalty -100`, so when the page is too full TeX picks one of two equally attractive break points — and would pick the inner one, stranding the title. Fix: when iterating `content[]`, the first clause sub now receives `suppress_needspace=true` so it doesn't emit its own `\kxneedspace`. The parent's penalty is then the only attractive break, so the break happens before the title and the section moves to the next page intact. Subsequent sub-clauses still get `\kxneedspace` so they're individually orphan-protected.

## 0.9.3 — 2026-05-04

### Fixes
- **`clause`: titles no longer strand alone at the bottom of a page (full fix).** v0.9.2's `\nopagebreak[4]` only forbade *one* break point between the title and the first sub-item, leaving the `\kxneedspace` penalty inside the first sub-item as a still-attractive break that TeX would happily pick. The pre-title `\kxneedspace` value is now bumped to reserve room for the title **plus** the first sub-item: `level: 2` reserves 8 baselineskip, `level: 3` reserves 6, `level: 4` reserves 4, regel-style stays at 2. With this, when the page is too full for both, the break is taken before the title — the title moves to the next page together with its first sub-item, instead of being orphaned. (An interim attempt to switch `\kxneedspace` to a hard `\pagegoal-\pagetotal` check using `\pagebreak` was reverted; in the recursive clause structure it interacted badly and stranded *single* sub-items on otherwise empty pages.)

## 0.9.2 — 2026-05-04

### Fixes
- **`clause`: title no longer strands alone at the bottom of a page when content[] follows.** `\kxneedspace{4\baselineskip}` runs *before* the title is placed and only checks room for the title itself; once the title fit, the first sub-item's own `\kxneedspace` would then break the page, leaving the title orphaned. The renderer now emits `\nopagebreak[4]` between the title and `content[]` so TeX keeps them together — if there isn't room for both, the page breaks before the whole section.

### Spacing
- **`clause`: more breathing room above the title, scaled by `level`.** Previously the title rode straight on `\parskip` from the previous block, which made `§ 3.` clauses sit too close to the last sub-item of `§ 2.`. Now: `level: 2` adds `1.4em` (matches heading H2), `level: 3` adds `1.0em` (H3), `level: 4` adds `0.4em`. Regel-style clauses (no `level`) stay tight so consecutive regelpunkter still hug each other.

## 0.9.1 — 2026-05-04

### Fixes
- **`clause`: label box now sized via LaTeX `\settowidth` per sibling group.** v0.9.0 used a Python-side char-width heuristic that systematically underestimated `§` (and other wide glyphs) at `\Large`, so labels like `§ 13.` overflowed their box and touched the title with no visible padding. The renderer now emits a `\settowidth` + `\ifdim`-max pre-pass per sibling group (including top-level body) into a scoped `\kxgrouplabelw`, then uses that for the box width and `\hangindent`. Always pixel-accurate, regardless of font size or character widths.

## 0.9.0 — 2026-05-04

### Breaking changes
- **`clause` block fully redesigned** for flexibility. The old shape (`{title, items: [...]}` with auto-numbering 1, 2, 3 and rigid `items[]` regelpunkter) is replaced by:
  ```json
  {
    "type": "clause",
    "number": "§ 7",        // free-form string, manual
    "text": "...",          // optional inline text on the label row
    "level": 2 | 3 | 4,     // optional visual prominence
    "content": [Block, ...] // optional nested blocks (including nested clauses)
  }
  ```
  - **Manual numbering**: author writes `"§ 7"`, `"7.1"`, `"I"`, `"A"`, etc. — verbatim. No automatic counters.
  - **Recursive nesting**: a `clause` block's `content[]` can contain another `clause` (sub-section). Nesting supports text, list, callout, quote, table, latex, form, description_list as well.
  - **Levels are optional and purely visual**: `level: 2` = `\Large` bold (matches heading H2), `level: 3` = `\large` bold (H3), `level: 4` = body bold. **Omit `level`** for regel-style: body-size, regular weight (label and text matched).
  - **Indent is depth-based** (0.5cm per nesting level) and decoupled from label width — sub-content position is independent of how wide the parent label was.
  - **Label width per sibling group**: the renderer measures the longest `number` in each sibling group and uses that for all labels in the group, so columns align even when one sibling is `7.9` and another is `7.10`.
  - Migration: replace `items: ["a", "b", "c"]` with `content: [{type: "clause", number: "1.1", text: "a"}, {type: "clause", number: "1.2", text: "b"}, ...]`. For old nested `{title, items}` items, use a nested `clause` with `text` and `content`.

### Removed
- **`klartex-klausuler.sty`** removed. The old `\clauses`/`\subclauses` enumitem environments and `\clause`/`\clausenum` macros are gone — clause rendering now uses `\hangindent` + `\makebox` + `\leftskip` directly. The `klausuler` recipe component (used by `protokoll`) is migrated to inline rendering with position-based numbering; recipe data shape is unchanged.

### Internal
- `_block_engine.tex.jinja` got a recursive `render_clause(block, lang, indent_cm, label_w)` macro. Top-level body loop pre-computes the group label-width for top-level clause-typed siblings; nested clauses do the same per `content[]`. Heuristic char-width per level (body 0.16cm, `\large` 0.20cm, `\Large` 0.24cm) plus 0.15cm padding.
- `klartex/renderer.py` `_restore_block_types` recurses into `clause.content[]` so nested block-type strings survive escaping.
- `avtal/schema.json` `clause` definition migrated to the new shape.
- 5 fixtures migrated (`block_motion`, `block_spacing_all`, `avtal_block`, `avtal`, `block_engine.example`).
- `TestClauseNumber` (introduced in v0.8.0) replaced with `TestClauseBlock` covering schema validation, group label-width, recursive nesting, and depth-based indent.

## 0.8.0 — 2026-05-04

### New features
- **`clause`: explicit paragraph numbering via optional `number` field.** When set, the clause renders as `§ N. Title` and its sub-items use `N.1, N.2, …` regardless of the block's position in `body[]`. When omitted, behavior is unchanged — auto-numbered as `M. Title` with sub-items `M.1, M.2, …` (no §). Use case: legal contracts (arrendeavtal, hyresavtal) where paragraph numbers are determined by document role, not by `body[]` order. Implemented as a new `\clausenum{N}{title}` macro in `klartex-klausuler.sty` that calls `\setcounter{clausecounter}{N}` so subclauses pick up the explicit number automatically.

## 0.7.1 — 2026-05-04

### Style
- **`form`: blank fields now use dotted lines (`\dotfill`) instead of solid (`\hrulefill`).** Matches the dotted style used in `signatures` blocks for consistent paper-signing aesthetics across a document.

## 0.7.0 — 2026-05-04

### Breaking changes
- **`metadata_table` renamed to `description_list`.** The block has always been a definition list (HTML `<dl>` of label/value pairs), not a table. Field shape (`entries[]` with `{label, value}`) is unchanged — only the type name moves. The `protokoll`, `sie-exportrapport`, `budgetrapport`, `resultatrakning`, and `balansrakning` recipes now emit `description_list` internally; recipe input data is unaffected. Migration: replace `{"type": "metadata_table", ...}` with `{"type": "description_list", ...}` in any block-engine documents.

### New blocks
- **`form`**: label/value rows where missing values render as `\hrulefill` horizontal rules for handwritten signing. No `title` field — compose with a `heading` block before the form when a sub-title is needed. Suitable for arrendeavtal, hyresavtal, and similar paper-signed contracts.
- **`columns`**: side-by-side layout container holding 1–4 column-stacks. Each item in `items[]` is an array of blocks rendered as a single column at equal width. Allowed inner block types: `heading`, `text`, `list`, `callout`, `quote`, `table`, `latex`, `form`, `description_list`. Top-only types and nested `columns` are rejected at validation. Combine with `form` and `description_list` to build party sections, side-by-side details, etc.

### Bug fixes
- **Nested block dispatch.** The renderer now recursively restores unescaped `block.type` strings into nested carriers (`list.items[].content[]` and `columns.items[][]`). Previously type-restoration only walked top-level `body[]`, so a nested `description_list` — or any underscore-named block type — survived as `description\_list` through the Jinja dispatch and was silently dropped from the rendered LaTeX.

## 0.6.1 — 2026-05-04

### Fixes
- **`metadata_table`: long values no longer overflow the right margin.** Both the recipe path (`protokoll`, `faktura`, etc.) and the block engine path now render the value column with `tabularx` `>{\raggedright\arraybackslash}X` so a long Närvarande/attendees row, an unusually long location, etc. wraps to the next line within the page width instead of running off the edge.

## 0.6.0 — 2026-05-04

### Breaking changes
- **`list` block: nested-items shorthand replaced with `content[]`.** A list item that previously expressed a sub-list as `{"text": "...", "items": [...]}` now uses `{"text": "...", "content": [{"type": "list", "items": [...]}]}`. The `content[]` array accepts nested blocks of types `text`, `list`, `callout`, `quote`, `table`, and `latex` — not just sub-lists. Top-only block types (`heading`, `signatures`, `title_page`, `parties`, `agenda`, `metadata_table`, `name_roster`, `clause`, `page_break`, financial blocks) are rejected at validation. This lets a numbered list item carry a continuation paragraph, suggested wording, embedded callout, etc., without introducing `(a)`-style sub-numbering.

### Typography
- **Widow and orphan protection.** `klartex-base.cls` now sets `\widowpenalties 2 10000 10000` and `\clubpenalties 2 10000 10000`, forbidding 1- and 2-line widows (last lines of a paragraph stranded on a new page) and orphans (first lines stranded at the bottom).
- **Heading-orphan protection.** Headings in the block engine call `\kxneedspace{6/4/3 \baselineskip}` (H1/H2/H3) so a heading cannot land alone at the bottom of a page — if the heading plus a few lines of body text doesn't fit, the page breaks before the heading. `\kxneedspace` is implemented inline in `klartex-base.cls` (no `needspace.sty` dependency).

### Internal
- Block-dispatch in `_block_engine.tex.jinja` is now a single `render_block` macro called both from the top-level body loop and recursively from `render_list` for items with `content[]`. The top-level loop continues to own the lazily-opened `clauses` environment around runs of `clause` blocks.

## 0.5.0 — 2026-05-03

### Breaking changes
- **Removed `preamble` block.** It was a pure alias for `text`; use `{"type": "text", ...}` instead. The recipe schema for `avtal` no longer accepts `"preamble"` either.
- **Removed `attendees` block.** The `protokoll` recipe still accepts `attendees` and `adjusters` in its input data and now surfaces them as `Närvarande:` / `Justerare:` rows in the metadata table — no input-data change is required for `protokoll`. Block-engine documents that previously used `{"type": "attendees", ...}` should switch to plain `text` blocks with bold inline labels.

### Spacing
- **Heading rhythm:** trailing `\vspace` now cancels the surrounding `\parskip` locally so H1/H2/H3 produce visibly distinct gaps below them (~1.2 / 0.5 / 0.15 em). Previously the parskip drowned the level differences.
- **`metadata_table`:** 2em above and below.
- **`parties`:** 3em above and below.
- **`table`:** symmetric 1em above and below (was 0/1).
- **`name_roster`, `resultatrakning`, `budgettabell`, `notapparat`:** explicit top/bottom margins so they no longer klistra mot brödtext.
- **`callout`:** `before/after skip` raised to 1em — consecutive callouts no longer touch.

### Quote block
- 2em vertical breathing room above and below.
- Wrapped in curly typographic quotes (`“…”`).
- The opening `“` is set at 36pt and hung into the left margin via a zero-width right-aligned box (classic hanging quote).

### Tests
- New comprehensive fixture `tests/fixtures/block_spacing_all.json` exercising every block type with realistic prose, useful for visual spacing inspection.

## 0.4.0 — 2026-05-02

### Breaking changes
- **Removed `adjuster_signatures` block.** The `protokoll` recipe still surfaces adjusters via the `attendees` label; for dedicated adjuster signature lines, use the `signatures` block.
- **Renamed `klartex-signaturblock` → `klartex-signatureblock`** (both the `.sty` package and the recipe component type). Update `\usepackage{klartex-signaturblock}` and any recipe `type: signaturblock` references.

### New features
- **`signatures` flexibility:** party `name` is now optional (omit to suppress the bold header above a signature pane); new block-level `show_location_date` flag (default `true`) hides the "Ort och datum" line and its dotted entry.

### Improvements
- **`table` block:** thin row lines (0.2pt `\cmidrule` between data rows) and a default `1em` bottom margin so following content breathes.
- **`signatures` block:** tighter pane spacing — reduced gaps above dotted lines (`0.8cm → 0.6cm`), shorter pane internals, and smaller inter-row/intro vspaces.
- **README:** previously-missing v0.3.0 blocks (`list`, `table`, `callout`, `quote`) now listed.

## 0.3.0 — 2026-04-30

### New blocks
- **`list`** — bullet/numbered, nestable (#24)
- **`table`** — simple data table with `tabularx` + `booktabs`, configurable column widths (#26)
- **`callout`** — visually distinct notice box with five variants (info/tip/warning/danger/note), backed by new `klartex-callout.sty` (#27)
- **`quote`** — typographic blockquote with optional em-dash attribution (#28)

### New features
- **Inline markup** in text-bearing fields: `**bold**`, `*italic*`, `` `code` ``, locale-aware smart quotes (sv: ”…”, en: “…”). Implemented as a Jinja `inline` filter; runs post-escape so existing escaping stays intact. (#25)
- **CLI:** `--version` / `-V` flag

### Fixes
- **External page templates** are now treated as self-contained — `--page-template` no longer loses the page-1 header from spurious `\thispagestyle{plain}` overrides applied on top of the user's template
- **Heading typography:** moved `\vspace` from after to before headings with asymmetric magnitudes; headings now visually belong to their following content. Removed redundant `\vspace{1em}` before text blocks (parskip handles it)
- **`metadata_table`** gets a default `\vspace{1em}` after, so it breathes before body content

## 0.2.1 — 2026-04-02

### Fixes
- **API:** Schema validation errors now return 400 instead of 500
- **Page template override:** `--page-template` / `page_template_source` no longer fails when `data.page_template` is missing or unknown
- **CLI:** `klartex example <template>` now works for all recipe templates (example.json files were missing)

## 0.2.0 — 2026-04-02

### New templates
- **resultaträkning** — Income statement with multi-year comparison and note references
- **balansräkning** — Balance sheet with assets/liabilities/equity structure
- **budgetrapport** — Budget vs. actuals report with variance percentages
- **sie-exportrapport** — SIE file export documentation with verification details

### New features
- **Annual meeting package** — 8 ready-made document fixtures (kallelse, verksamhetsberättelse, årsredovisning, revisionsberättelse, budget, valberedning, motion, styrelseyttrande)
- **Agent-friendly CLI** — `oneOf` JSON schema, `klartex blocks` listing, `--example` flag for quick starts
- **Financial components** — Reusable resultaträkning, budgettabell, and notapparat blocks for the block engine
- **Financial macros** — Shared Jinja macros (`_financial_macros.tex.jinja`) to DRY up financial rendering

### Improvements
- Swedish character fixes in protokoll template (Närvarande, Mötesprotokoll, Ordförande)
- Comprehensive test fixtures for all templates and block types (150 tests)

## 0.1.0 — 2026-02-17

Initial release.

- Core rendering engine (JSON + YAML recipe → LaTeX → PDF)
- Composable YAML recipe system with JSON Schema validation
- Templates: protokoll, faktura, avtal (via block engine)
- Universal block engine with clause, signature, attendees, party, and LaTeX blocks
- Configurable page templates and header layouts
- FastAPI HTTP service and Typer CLI
- GitHub Actions CI with xelatex verification
