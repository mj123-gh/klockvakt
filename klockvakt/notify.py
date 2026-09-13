from __future__ import annotations

import os
from typing import Any

import requests

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


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

    resp = requests.post(
        TELEGRAM_API.format(token=token),
        json={"chat_id": chat_id, "text": text},
        timeout=15,
    )
    resp.raise_for_status()
