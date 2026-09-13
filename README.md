# Klockvakt

Bevakar utvalda finska begagnatklockhandlare och skickar en Telegram-notis
när ett nytt objekt dyker upp som matchar dina kriterier (märke, pris,
nyckelord). Publicerar även en enkel webb-dashboard med alla aktuella
matchningar via GitHub Pages.

## Status just nu

Alla 27 handlare från [Kellofoorumis lista](https://kellofoorumi.fi/uutiset/kaytettyjen-kellojen-kauppiaat-suomessa/)
har gåtts igenom och verifierats direkt mot deras servrar. **Alla 21
medtagna butiker har en riktig parser** – ingen använder längre
"sidan ändrades"-stopgapet. Testkört (`python -m klockvakt.main`, flera
körningar för att bekräfta att dedup fungerar), inga krascher.

| Plattform | Antal | Hur det funkar |
|---|---|---|
| `shopify` | 2 | Läser butikens `/products.json` |
| `woocommerce_api` | 8 | WooCommerce **Store API** (`/wp-json/wc/store/v1/products`) |
| `magento` | 1 (Kulta-Center) | Magentos GA-spårningsattribut (`data-id`/`data-name`/`data-price`) inbäddade på varje produktlänk, med automatisk paginering |
| `wix` | 1 (Kellotupa) | `/store-products-sitemap.xml` + schema.org Product-JSON (`application/ld+json`) på varje produktsida |
| `webflow` | 3 (Sörkan Kello, Gello, ChronoX) | Statisk HTML från Webflows CMS Collection Lists (`w-dyn-item`), ofta med Finsweet CMS Filter-attribut för pris |
| `webador` | 2 (Aikarauta, Aika & Aarre) | JSON inbäddad direkt i `data-webshop-product`-attributet på varje produktkort |
| `kronometri` | 1 | Egen skrapare (Weebly) – läser titel+pris som textrader eftersom HTML-taggarna varierar mellan kort |
| `takuukello` | 1 | Egen skrapare – statisk HTML (Breakdance page builder) |
| `supabase` | 1 (Rolle Kellot) | Frågar samma publika Supabase-API som sidan själv använder |
| `squarespace` | 1 (Prime Time Kellot) | Squarespaces `?format=json`-API |
| `custom_diff` | 0 | Kvar i koden som fallback om en framtida butik saknar strukturerad data |

### Butiker som INTE är medtagna

| Butik | Orsak |
|---|---|
| Kellokonttori, Kelloneuvos, Helsingin Kello ja Kulta | Har redan egen "hakuvahti"/e-postbevakning inbyggd på sajten – prenumerera direkt hos dem istället, då slipper du underhålla en skrapare |
| Timepiece Finland, Second Time | Säljer bara via Instagram – går inte att bevaka programmatiskt utan inloggning, och bryter mot Instagrams användarvillkor |
| Kelloholvi | Sidans "butik" är i praktiken en inbäddad Instagram-flödes-widget (Smash Balloon-pluginet, hittades i sidans källkod) – de riktiga WooCommerce-produkterna finns men är satta till dold katalogsynlighet. Samma princip som Instagram-only-butikerna ovan |
| Oulun Arvokello | Har lagt ner sin kello-verksamhet (sidan bekräftar det explicit) |

### Så hittades API:erna

Samma metod för alla: läs sidans källkod (leta efter plattformsspår som
`wp-json`, `wix-warmup-data`, `data-*`-attribut, `application/ld+json`),
kolla `/sitemap.xml` för produktlänkar, och testa `?format=json` eller
liknande dolda ändpunkter. Inget lösenordsskydd kringgicks någonstans –
allt som används är exakt samma publika data som butikens egen hemsida
redan laddar hem till besökarens webbläsare.

## Så funkar det

- `config.json` – lista över butiker (`platform`: `shopify` /
  `woocommerce_api` / `woocommerce` / `magento` / `wix` / `webflow` /
  `webador` / `kronometri` / `takuukello` / `supabase` / `squarespace` /
  `custom_diff`) samt dina filterkriterier.
- `klockvakt/scrapers.py` – en funktion per plattformstyp.
- `klockvakt/filters.py` – matchar mot märke/pris/nyckelord.
- `klockvakt/state.py` – kommer ihåg vilka annonser som redan är sedda
  (`state/seen.json`), så du bara får notis för *nya* objekt.
- `klockvakt/notify.py` – skickar Telegram-meddelande (skriver till
  terminalen om ingen bot är konfigurerad än, så du kan testa utan Telegram
  först).
- `klockvakt/dashboard.py` – skriver `docs/index.html`, en fristående
  webbsida med alla objekt som matchar dina filter i den senaste körningen
  (sorterade efter pris). Servas gratis via GitHub Pages, se nedan.
- `.github/workflows/klockvakt.yml` – kör allt en gång per dygn via GitHub
  Actions, helt utan att du behöver hålla en egen dator igång.

## Testat lokalt

Hela pipelinen (21 butiker, alla med riktiga parsers) har körts två gånger
i rad i den här miljön: första körningen gav 124 träffar som matchade
filtren i `config.json`, andra körningen gav 0 nya träffar – dedup via
`state/seen.json` fungerar. Inga krascher.

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

1. Skapa ett nytt GitHub-repo och pusha den här mappen.
2. Lägg till secrets enligt ovan.
3. Workflow-filen kör automatiskt en gång per dygn (kl 17:00 finsk tid), och
   sparar sitt state (`state/seen.json`) och dashboard (`docs/index.html`)
   tillbaka till repot mellan körningar.
4. Testa manuellt via fliken **Actions → Klockvakt → Run workflow** innan du
   litar på schemat.

## Dashboard via GitHub Pages

`docs/index.html` genereras automatiskt vid varje körning och visar alla
klockor som matchar dina filter just nu – ingen extern server behövs,
GitHub Pages servar filen gratis direkt från repot.

**Obs:** GitHub Pages på gratisplanen kräver att repot är **publikt**.
Inget hemligt ligger i själva filerna (Telegram-uppgifterna är GitHub
Secrets, och Supabase-nyckeln i `config.json` är en avsiktligt publik
anon-nyckel), men det är ett medvetet val att göra.

1. Gör repot publikt: **Settings → General → Danger Zone → Change
   visibility → Make public**.
2. Aktivera Pages: **Settings → Pages → Build and deployment → Source:
   "Deploy from a branch"** → Branch: `main`, mapp: `/docs` → **Save**.
3. Efter någon minut är sidan live på
   `https://<ditt-användarnamn>.github.io/<repo-namn>/`.

Vill du hellre hålla repot privat: dashboard-filen skapas ändå lokalt vid
varje körning (`docs/index.html`) – öppna den direkt i webbläsaren, eller
kör GitHub Pages via ett betalt GitHub Pro-konto istället.

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
5. Kellotupa (`wix`) gör ett anrop per produkt (ingen samlings-API finns) –
   fint för 33 produkter men skulle behöva justeras om katalogen växer
   mycket (t.ex. cacha vilka produkt-URL:er som redan är kända oförändrade).

## Kända begränsningar

- `custom_diff` (kvar i koden) ger dig bara "något ändrades", inte vilket
  objekt – används inte av någon butik just nu men finns som fallback.
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
- De nya butiksspecifika skraparna (Kronometri, Webflow-butikerna,
  Webador-butikerna) bygger på HTML-strukturer som butikerna kan ändra utan
  förvarning eftersom de inte är ett publicerat API – om en av dem plötsligt
  ger 0 träffar är första steget att kolla om sidans HTML har ändrats.
