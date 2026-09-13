from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from . import dashboard
from . import filters as filters_mod
from . import state as state_mod
from .notify import send_telegram
from .scrapers import scrape_shop

# Titlar kan innehålla tecken (t.ex. specialtankstreck) som en Windows-terminal
# (cp1252) inte klarar av att skriva ut. Tvinga UTF-8 så körning lokalt inte
# kraschar på annonstexter vi inte kan kontrollera.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


def main() -> None:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        config = json.load(f)

    seen = state_mod.load_seen()
    new_seen = set(seen)
    total_new_matches = 0
    current_matches: list[tuple[dict, str]] = []

    for shop in config["shops"]:
        try:
            items = scrape_shop(shop)
        except Exception as exc:  # en trasig butik ska inte stoppa de andra
            print(f"[FEL] {shop['name']} ({shop['platform']}): {exc}", file=sys.stderr)
            continue

        for item in items:
            is_new = item["id"] not in seen
            new_seen.add(item["id"])

            if filters_mod.matches(item, config["filters"]):
                current_matches.append((item, shop["name"]))
                if is_new:
                    send_telegram(item, shop["name"])
                    total_new_matches += 1

        time.sleep(1)  # var artig mellan butiker

    state_mod.save_seen(new_seen)
    dashboard.render(
        current_matches,
        config["filters"],
        repo=os.environ.get("GITHUB_REPOSITORY", ""),
    )
    print(f"Klart. {total_new_matches} nya träffar som matchade dina filter.")


if __name__ == "__main__":
    main()
