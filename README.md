# Klockvakt

Bevakar utvalda finska begagnatklockhandlare och skickar en Telegram-notis
när ett nytt objekt dyker upp som matchar dina kriterier (märke, pris,
nyckelord).

## Status just nu

Alla 27 handlare från [Kellofoorumis lista](https://kellofoorumi.fi/uutiset/kaytettyjen-kellojen-kauppiaat-suomessa/)
har gåtts igenom och verifierats direkt mot deras servrar. 21 butiker är
konfigurerade och testkörda (`python -m klockvakt.main`, två körningar för
att bekräfta att dedup fungerar) – 166 träffar första körningen, 0 andra
körningen, inga krascher.

| Plattform | Antal | Hur det funkar |
|---|---|---|
| `shopify` | 2 | Läser butikens `/products.json` – stabilt, ingen CSS inblandad |
| `woocommerce_api` | 8 | Läser WooCommerce **Store API** (`/wp-json/wc/store/v1/products`) – strukturerad JSON istället för att gissa CSS-klasser. Mycket stabilare än ren HTML-scraping eftersom temat kan bytas utan att skraparen går sönder |
| `custom_diff` | 11 | Stopgap – larmar bara "sidan ändrades", inte vad. Se avsnittet nedan om vilka som är värda att bygga ut |

### Butiker som INTE är medtagna

| Butik | Orsak |
|---|---|
| Kellokonttori, Kelloneuvos, Helsingin Kello ja Kulta | Har redan egen "hakuvahti"/e-postbevakning inbyggd på sajten – prenumerera direkt hos dem istället, då slipper du underhålla en skrapare |
| Timepiece Finland, Second Time | Säljer bara via Instagram – går inte att bevaka programmatiskt utan inloggning, och bryter mot Instagrams användarvillkor |
| Oulun Arvokello | Har lagt ner sin kello-verksamhet (sidan bekräftar det explicit) |

### `custom_diff`-butiker värda att bygga ut vidare

De flesta av dessa kräver mer jobb än en enkel CSS-fix eftersom de inte
exponerar någon strukturerad data:

- **Kelloholvi** – kör WooCommerce-tema, men produkterna är satta till
  `catalog_visibility: hidden` så Store API:t visar bara 1 av ~90 objekt,
  och sidan renderar listan via JS. Kräver en headless browser (t.ex.
  Playwright) för en riktig lösning.
- **Takuukello** – helt custom-byggd med Breakdance page builder, ingen
  produkt-API hittad. Går att bygga en riktig parser mot
  `article.bde-loop-item` / `a.bde-container-link` om det är värt besväret.
- **Rolle Kellot** – Next.js-app med Supabase-backend. Öppna DevTools →
  Network på `rollekellot.fi/kellot` för att hitta deras faktiska
  data-anrop (troligen ett Supabase REST-anrop med publik anon-key) – då
  går det säkert att bygga en riktig JSON-baserad parser.
- **Prime Time Kellot** – Squarespace, som ofta har ett dolt
  `?format=json` på handelssidor. Rätt sid-URL för butiken är inte
  bekräftad än.
- Kronometri, Kellotupa, Aika & Aarre, Sörkan Kello, Gello, Aikarauta,
  ChronoX, Kulta-Center – custom-plattformar (Weebly/Wix/Webador/Webflow)
  utan uppenbar strukturerad data. `custom_diff` fungerar men larmar bara
  "något ändrades".

## Så funkar det

- `config.json` – lista över butiker (`platform`: `shopify` /
  `woocommerce_api` / `woocommerce` / `custom_diff`) samt dina
  filterkriterier.
- `klockvakt/scrapers.py` – en funktion per plattformstyp.
- `klockvakt/filters.py` – matchar mot märke/pris/nyckelord.
- `klockvakt/state.py` – kommer ihåg vilka annonser som redan är sedda
  (`state/seen.json`), så du bara får notis för *nya* objekt.
- `klockvakt/notify.py` – skickar Telegram-meddelande (skriver till
  terminalen om ingen bot är konfigurerad än, så du kan testa utan Telegram
  först).
- `.github/workflows/klockvakt.yml` – kör allt var 3:e timme via GitHub
  Actions, helt utan att du behöver hålla en egen dator igång.

## Testat lokalt

Hela pipelinen (21 butiker) har körts två gånger i rad i den här miljön:
första körningen gav 166 träffar som matchade filtren i `config.json`
(Rolex/Omega/Tudor under 6000 €), andra körningen gav 0 nya träffar – dedup
via `state/seen.json` fungerar. Inga krascher.

## Kom igång lokalt (testa innan du deployar)

```bash
pip install -r requirements.txt
python -m klockvakt.main
```

Första körningen räknar allt som "nytt" (state är tom), så förvänta dig en
skur av notiser/loggrader – det är förväntat. Kör en gång till direkt efter
för att se att inget dubbelrapporteras.

## Koppla in Telegram

1. Prata med [@BotFather](https://t.me/BotFather) på Telegram, skapa en bot,
   spara token.
2. Skicka ett valfritt meddelande till din nya bot, hämta sedan ditt
   `chat_id` via `https://api.telegram.org/bot<TOKEN>/getUpdates`.
3. Sätt `TELEGRAM_BOT_TOKEN` och `TELEGRAM_CHAT_ID` som miljövariabler
   lokalt, eller som **GitHub Secrets** i repot (Settings → Secrets and
   variables → Actions) för molnkörningen.

## Deploya med GitHub Actions

1. Skapa ett nytt (gärna privat) GitHub-repo och pusha den här mappen.
2. Lägg till secrets enligt ovan.
3. Workflow-filen kör automatiskt var 3:e timme, och sparar sitt state
   (`state/seen.json`) tillbaka till repot mellan körningar.
4. Testa manuellt via fliken **Actions → Klockvakt → Run workflow** innan du
   litar på schemat.

## Nästa steg

1. Bygg riktiga parsers för de `custom_diff`-butiker som är mest
   intressanta för dig (se prioriteringen ovan – Kelloholvi, Takuukello,
   Rolle Kellot och Prime Time Kellot har alla en trolig väg till
   strukturerad data).
2. Lägg till felnotifiering till dig själv (t.ex. ett separat
   Telegram-meddelande) om en skrapare börjar ge 0 träffar flera körningar
   i rad – tecken på att sajten bytt struktur.
3. Håll ett öga på Kalevan Kellos svarstider – deras WooCommerce Store API
   är påfallande långsamt (~20 s per sida med 100 objekt) och kan ibland
   timeouta; det är redan hanterat (en trasig/långsam butik stoppar inte de
   andra), men om det blir ett återkommande problem kan sidstorleken sänkas
   från 100 till t.ex. 50.

## Kända begränsningar

- `custom_diff` ger dig bara "något ändrades", inte vilket objekt – bygg ut
  den per butik i den takt du hinner (se prioritering ovan).
- WooCommerce-selektorerna i den äldre CSS-baserade `woocommerce`-skrapan
  (kvar i koden som fallback) är generiska gissningar. Alla butiker som
  faktiskt konfigurerats i `config.json` använder istället `woocommerce_api`
  mot Store API:t, som är verifierat och stabilare.
- Ingen hantering av att objekt *tas bort* (sålda kellor) – state-filen
  växer bara. Fungerar fint, men om du vill hålla den ren kan du lägga till
  en TTL/rensning.
- Vissa butikers Store API returnerar även sålda/slutsålda objekt (upptäckt
  hos Longitudi) – dessa filtreras bort via fältet `is_in_stock`, men om
  ytterligare butiker beter sig annorlunda kan liknande justeringar behövas.
