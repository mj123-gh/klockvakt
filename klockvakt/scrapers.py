"""
Skrapare för de olika butiksplattformarna.

Varje funktion tar emot ett "shop"-dict från config.json och returnerar en
lista av produkt-dicts med nycklarna:
    id, title, url, price_eur (float | None), image (str | None)

platform == "custom_diff" är ett stopgap för butiker som ännu inte har en
riktig produkt-parser: den hashar hela sidans text och rapporterar en enda
pseudo-post om sidan har ändrats sen senaste körning. Det talar bara om
"något är nytt här", inte vad.
"""
from __future__ import annotations

import hashlib
import html
import re
import time
from typing import Any

import requests
from bs4 import BeautifulSoup

HEADERS = {
    # Var en artig bot: tydlig UA, ingen maskering.
    "User-Agent": "Klockvakt/1.0 (personligt bruk, kontakt: <din e-post>)"
}
TIMEOUT = 30  # vissa butikers WooCommerce Store API är påfallande långsamt (t.ex. Kalevan Kello)


def _get(url: str) -> requests.Response:
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp


def _get_json(url: str, params: dict[str, Any] | None = None, retries: int = 2) -> requests.Response:
    """
    Som _get, men med några omförsök om servern svarar med tom/trasig JSON.
    Molnservrar (t.ex. GitHub Actions) blir ibland tillfälligt nekade eller
    får ett tomt svar av en butiks brandvägg – ett par sekunders paus och
    ett nytt försök löser oftast det utan att hela körningen missar butiken.
    """
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            resp.json()  # validera att kroppen faktiskt är JSON innan vi litar på den
            return resp
        except (requests.RequestException, ValueError) as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(3)
    assert last_exc is not None
    raise last_exc


def shopify_products(shop: dict[str, Any]) -> list[dict[str, Any]]:
    """Shopify-butiker exponerar alltid en /products.json på collection-URL:en."""
    base = shop["base_url"].rstrip("/")
    path = shop.get("collection_path", "").rstrip("/")
    url = f"{base}{path}/products.json?limit=250"
    data = _get_json(url).json()

    items = []
    for p in data.get("products", []):
        variants = p.get("variants", [])
        price = None
        if variants:
            try:
                price = float(variants[0].get("price"))
            except (TypeError, ValueError):
                price = None
        image = None
        if p.get("images"):
            image = p["images"][0].get("src")
        items.append(
            {
                "id": f"{shop['id']}:{p['id']}",
                "title": p.get("title", ""),
                "url": f"{base}/products/{p.get('handle')}",
                "price_eur": price,
                "image": image,
            }
        )
    return items


def woocommerce_api_products(shop: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Läser WooCommerce Store API (/wp-json/wc/store/v1/products), som de
    flesta moderna WooCommerce-butiker exponerar publikt oavsett tema –
    mycket stabilare än att gissa CSS-selektorer eftersom det är strukturerad
    JSON. Verifierat manuellt mot 8 av butikerna i config.json.

    Valfri "category" i config.json (kategorins slug, t.ex. "arvokellot")
    begränsar till en kategori – bra för butiker som säljer annat än kellor
    också (t.ex. Holmasto som mest säljer mynt och smycken).
    """
    base = shop["base_url"].rstrip("/")
    category = shop.get("category")
    items: list[dict[str, Any]] = []
    page = 1
    max_pages = 20  # skyddsnät mot oändlig loop om API:t beter sig oväntat

    while page <= max_pages:
        params: dict[str, Any] = {"per_page": 100, "page": page}
        if category:
            params["category"] = category
        resp = _get_json(f"{base}/wp-json/wc/store/v1/products", params=params)
        batch = resp.json()
        if not batch:
            break

        for p in batch:
            # Vissa butiker (t.ex. Longitudi) har sålda/slutsålda objekt kvar
            # i API:t med pris 0 – hoppa över dem, de är inte till salu.
            if p.get("is_in_stock") is False:
                continue
            prices = p.get("prices") or {}
            raw_price = prices.get("price")
            minor_unit = prices.get("currency_minor_unit", 2)
            price = None
            # "0" betyder oftast "fråga efter pris" snarare än gratis.
            if raw_price not in (None, "", "0"):
                try:
                    price = float(raw_price) / (10**minor_unit)
                except (TypeError, ValueError):
                    price = None
            image = None
            if p.get("images"):
                image = p["images"][0].get("src")
            items.append(
                {
                    "id": f"{shop['id']}:{p['id']}",
                    "title": html.unescape(p.get("name", "")),
                    "url": p.get("permalink", ""),
                    "price_eur": price,
                    "image": image,
                }
            )

        total_pages = int(resp.headers.get("X-WP-TotalPages", page))
        if page >= total_pages:
            break
        page += 1

    return items


def woocommerce_products(shop: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Generisk WooCommerce-skrapare. Standardteman använder klasserna nedan,
    men temat varierar per butik – kontrollera selektorerna mot sidans
    faktiska HTML (högerklicka -> Granska) om inget hittas, och justera i
    config.json (product_link_selector / price_selector).
    """
    listing_url = shop["listing_url"]
    link_sel = shop.get("product_link_selector", "a.woocommerce-LoopProduct-link")
    price_sel = shop.get("price_selector", ".price")
    next_sel = shop.get("next_page_selector", "a.next.page-numbers")

    items: list[dict[str, Any]] = []
    url = listing_url
    pages_fetched = 0
    max_pages = 3  # var artig, skrapa inte oändligt djupt varje körning

    while url and pages_fetched < max_pages:
        soup = BeautifulSoup(_get(url).text, "html.parser")
        products = soup.select("li.product, div.product")
        for prod in products:
            link_el = prod.select_one(link_sel) or prod.select_one("a")
            if not link_el or not link_el.get("href"):
                continue
            product_url = link_el["href"]
            title = html.unescape(link_el.get("title") or link_el.get_text(strip=True))
            price_el = prod.select_one(price_sel)
            price = _parse_price(price_el.get_text(" ", strip=True)) if price_el else None
            img_el = prod.select_one("img")
            image = img_el.get("src") if img_el else None
            items.append(
                {
                    "id": f"{shop['id']}:{product_url}",
                    "title": title,
                    "url": product_url,
                    "price_eur": price,
                    "image": image,
                }
            )

        next_el = soup.select_one(next_sel)
        url = next_el["href"] if next_el and next_el.get("href") else None
        pages_fetched += 1

    return items


def custom_diff(shop: dict[str, Any]) -> list[dict[str, Any]]:
    """Stopgap: larma bara att sidan ändrats, utan att veta exakt vad."""
    page_text = _get(shop["listing_url"]).text
    digest = hashlib.sha256(page_text.encode("utf-8")).hexdigest()
    return [
        {
            "id": f"{shop['id']}:page-hash:{digest}",
            "title": f"Sidan har ändrats hos {shop['name']} – kolla manuellt",
            "url": shop["listing_url"],
            "price_eur": None,
            "image": None,
        }
    ]


def _parse_price(text: str) -> float | None:
    # Plockar ut t.ex. "1 234,50 €" eller "1234.50" ur en textsträng.
    match = re.search(r"[\d]{1,3}(?:[ \u00a0.]?\d{3})*(?:[.,]\d{2})?", text)
    if not match:
        return None
    raw = match.group(0).replace(" ", "").replace("\u00a0", "")
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".")
    else:
        raw = raw.replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


SCRAPERS = {
    "shopify": shopify_products,
    "woocommerce_api": woocommerce_api_products,
    "woocommerce": woocommerce_products,
    "custom_diff": custom_diff,
}


def scrape_shop(shop: dict[str, Any]) -> list[dict[str, Any]]:
    fn = SCRAPERS.get(shop["platform"])
    if not fn:
        raise ValueError(f"Okänd plattform: {shop['platform']} för {shop['id']}")
    return fn(shop)
