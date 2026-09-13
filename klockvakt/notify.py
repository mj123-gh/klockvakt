from __future__ import annotations

import os
import sys
from typing import Any

import requests

TELEGRAM_MESSAGE_API = "https://api.telegram.org/bot{token}/sendMessage"
TELEGRAM_PHOTO_API = "https://api.telegram.org/bot{token}/sendPhoto"


def send_telegram(item: dict[str, Any], shop_name: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        # Ingen bot konfigurerad än – skriv till loggen istället så du ser
        # att matchningen fungerar innan du kopplar in Telegram.
        print(f"[NY TRÄFF] {shop_name}: {item['title']} – {item.get('price_eur')} € – {item['url']}")
        return

    price = f"{item['price_eur']} €" if item.get("price_eur") is not None else "pris okänt"
    text = f"🕰️ {shop_name}: {item['title']}\n{price}\n{item['url']}"
    image = item.get("image")

    if image:
        try:
            resp = requests.post(
                TELEGRAM_PHOTO_API.format(token=token),
                json={"chat_id": chat_id, "photo": image, "caption": text},
                timeout=15,
            )
            if resp.ok and resp.json().get("ok"):
                return
            print(
                f"[VARNING] sendPhoto misslyckades för {shop_name} ({image}): "
                f"{resp.status_code} {resp.text[:200]} – skickar textmeddelande istället.",
                file=sys.stderr,
            )
        except requests.RequestException as exc:
            print(
                f"[VARNING] sendPhoto misslyckades för {shop_name}: {exc} – "
                "skickar textmeddelande istället.",
                file=sys.stderr,
            )

    # Ingen bild, eller sendPhoto misslyckades (t.ex. otillgänglig/blockerad
    # bild-URL) – Telegram måste själv kunna hämta bilden, vilket ibland
    # strular även om vår egen skrapning av URL:en gick bra.
    resp = requests.post(
        TELEGRAM_MESSAGE_API.format(token=token),
        json={"chat_id": chat_id, "text": text},
        timeout=15,
    )
    resp.raise_for_status()
