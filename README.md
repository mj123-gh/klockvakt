# Klockvakt

Bevakar utvalda finska begagnatklockhandlare och skickar en Telegram-notis
när ett nytt objekt dyker upp som matchar dina kriterier (märke, pris,
nyckelord).

## Status just nu

Alla 27 handlare från [Kellofoorumis lista](https://kellofoorumi.fi/uutiset/kaytettyjen-kellojen-kauppiaat-suomessa/)
har gåtts igenom och verifierats direkt mot deras servrar. 21 butiker är
konfigurerade och testkörda (`python -m klockvakt.main`, flera körningar för
att bekräfta att dedup fungerar), inga krascher.

| Plattform | Antal | Hur det funkar |
|---|---|---|
| `shopify` | 2 | Läser butikens `/products.json` – stabilt, ingen CSS inblandad |
| `woocommerce_api` | 8 | Läser WooCommerce **Store API** (`/wp-json/wc/store/v1/products`) – strukturerad JSON istället för att gissa CSS-klasser |
| `takuukello` | 1 | Egen skrapare – statisk HTML (Breakdance page builder) |
| `supabase` | 1 | Egen skrapare (Rolle Kellot) – frågar samma publika Supabase-API som sidan själv använder |
| `squarespace` | 1 | Egen skrapare (Prime Time Kellot) – Squarespaces `?format=json`-API |
| `custom_diff` | 8 | Stopgap – larmar bara "sidan ändrades", inte vad |

### Butiker som INTE är medtagna

| Butik | Orsak |
|---|---|
| Kellokonttori, Kelloneuvos, Helsingin Kello ja Kulta | Har redan egen "hakuvahti"/e-postbevakning inbyggd på sajten – prenumerera direkt hos dem istället, då slipper du underhålla en skrapare |
| Timepiece Finland, Second Time | Säljer bara via Instagram – går inte att bevaka programmatiskt utan inloggning, och bryter mot Instagrams användarvillkor |
| **Kelloholvi** | Sidans "butik" är i praktiken en inbäddad Instagram-flödes-widget (Smash Balloon-pluginet, hittades i sidans källkod) – de riktiga WooCommerce-produkterna finns men är satta till dold katalogsynlighet. Samma princip som Instagram-only-butikerna ovan: går inte att bevaka programmatiskt på ett sätt som känns rimligt |
| Oulun Arvokello | Har lagt ner sin kello-verksamhet (sidan bekräftar det explicit) |

### Custom-plattformar utan egen parser (kvar som `custom_diff`)

Kronometri, Kellotupa, Aika & Aarre, Sörkan Kello, Gello, Aikarauta, ChronoX,
Kulta-Center – inget uppenbart strukturerat API hittades vid genomgången
(Weebly/Wix/Webador/Webflow utan publikt API). Går att undersöka djupare
efter samma metod som gav resultat för Rolle Kellot/Prime Time Kellot:
kolla sidans källkod och nätverksflik i webbläsarens DevTools efter
JSON-anrop, sitemap.xml för produktlänkar, eller `?format=json` för
Squarespace-sajter.

## Så funkar det

- `config.json` – lista över butiker (`platform`: `shopify` /
  `woocommerce_api` / `woocommerce` / `takuukello` / `supabase` /
  `squarespace` / `custom_diff`) samt dina filterkriterier.
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

1. Skicka med bild i Telegram-meddelandet (`image`-fältet samlas redan in
   men används inte av `notify.py` ännu).
2. Prisfall-notis på redan sedda klockor, inte bara helt nya objekt.
3. Lägg till felnotifiering till dig själv (t.ex. ett separat
   Telegram-meddelande) om en skrapare börjar ge 0 träffar flera körningar
   i rad – tecken på att sajten bytt struktur.
4. Håll ett öga på Kalevan Kellos svarstider – deras WooCommerce Store API
   är påfallande långsamt (~20 s per sida med 100 objekt) och kan ibland
   timeouta; det är redan hanterat (en trasig/långsam butik stoppar inte de
   andra), men om det blir ett återkommande problem kan sidstorleken sänkas
   från 100 till t.ex. 50.
5. Undersök resterande `custom_diff`-butiker efter samma metod som gav
   resultat för Rolle Kellot/Prime Time Kellot (se ovan).

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
