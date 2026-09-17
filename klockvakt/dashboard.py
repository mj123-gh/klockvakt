from __future__ import annotations

import html as html_mod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DASHBOARD_PATH = Path(__file__).resolve().parent.parent / "docs" / "index.html"

_PAGE_TEMPLATE = """<!doctype html>
<html lang="sv">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Klockvakt</title>
<style>
  :root {{
    color-scheme: light dark;
    --bg: #f5f4f1;
    --card-bg: #ffffff;
    --text: #1a1a1a;
    --muted: #6b6b6b;
    --border: #e4e2dd;
    --accent: #8a6d3b;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #17181a;
      --card-bg: #232426;
      --text: #ececec;
      --muted: #9a9a9a;
      --border: #34363a;
      --accent: #d4af6a;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 24px 16px 60px;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
  }}
  header {{
    max-width: 1100px;
    margin: 0 auto 24px;
  }}
  h1 {{
    margin: 0 0 4px;
    font-size: 1.6rem;
  }}
  .meta {{
    color: var(--muted);
    font-size: 0.9rem;
  }}
  .filters {{
    color: var(--muted);
    font-size: 0.85rem;
    margin-top: 8px;
  }}
  .grid {{
    max-width: 1100px;
    margin: 0 auto;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
    gap: 16px;
  }}
  .card {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    text-decoration: none;
    color: var(--text);
    transition: transform 0.1s ease;
  }}
  .card:hover {{
    transform: translateY(-2px);
  }}
  .card img {{
    width: 100%;
    aspect-ratio: 1 / 1;
    object-fit: cover;
    background: var(--border);
  }}
  .card .no-image {{
    width: 100%;
    aspect-ratio: 1 / 1;
    background: var(--border);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--muted);
    font-size: 0.85rem;
  }}
  .card-body {{
    padding: 12px 14px 14px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    flex: 1;
  }}
  .card-title {{
    font-weight: 600;
    font-size: 0.95rem;
    line-height: 1.3;
  }}
  .card-shop {{
    color: var(--muted);
    font-size: 0.8rem;
  }}
  .card-price {{
    margin-top: auto;
    padding-top: 6px;
    font-weight: 700;
    color: var(--accent);
  }}
  .empty {{
    max-width: 1100px;
    margin: 60px auto;
    text-align: center;
    color: var(--muted);
  }}
  footer {{
    max-width: 1100px;
    margin: 40px auto 0;
    color: var(--muted);
    font-size: 0.8rem;
    text-align: center;
  }}
  footer a {{ color: inherit; }}
</style>
</head>
<body>
<header>
  <h1>Klockvakt</h1>
  <div class="meta">{count} klockor matchar just nu &middot; uppdaterad {updated}</div>
  <div class="filters">{filters_text}</div>
</header>
{body}
<footer>
  Genererad automatiskt av <a href="https://github.com/{repo}">Klockvakt</a> &middot;
  körs {schedule_text}
</footer>
</body>
</html>
"""

_CARD_TEMPLATE = """<a class="card" href="{url}" target="_blank" rel="noopener">
  {image_html}
  <div class="card-body">
    <div class="card-title">{title}</div>
    <div class="card-shop">{shop}</div>
    <div class="card-price">{price}</div>
  </div>
</a>
"""


def _format_price(price_eur: float | None) -> str:
    if price_eur is None:
        return "Pris okänt"
    return f"{price_eur:,.0f} €".replace(",", " ")


def _format_filters(filters: dict[str, Any]) -> str:
    parts = []
    brands = filters.get("brands") or []
    if brands:
        parts.append("Märken: " + ", ".join(brands))
    min_p = filters.get("min_price_eur")
    max_p = filters.get("max_price_eur")
    if min_p is not None or max_p is not None:
        lo = f"{min_p:,.0f}".replace(",", " ") if min_p is not None else "0"
        hi = f"{max_p:,.0f}".replace(",", " ") if max_p is not None else "obegränsat"
        parts.append(f"Pris: {lo}–{hi} €")
    include = filters.get("keywords_include") or []
    if include:
        parts.append("Måste innehålla: " + ", ".join(include))
    exclude = filters.get("keywords_exclude") or []
    if exclude:
        parts.append("Utesluter: " + ", ".join(exclude))
    return " &middot; ".join(parts) if parts else "Inga filter satta"


def _first_seen_epoch(first_seen: str) -> float:
    try:
        return datetime.fromisoformat(first_seen).timestamp()
    except ValueError:
        return 0.0


def render(
    matches: list[tuple[dict[str, Any], str, str]],
    filters: dict[str, Any],
    repo: str = "",
    schedule_text: str = "enligt schemat i .github/workflows/klockvakt.yml",
) -> None:
    """
    Skriver docs/index.html - en statisk dashboard över alla objekt som
    matchar filtren i config.json i den senaste körningen. "matches" är en
    lista av (item, shop_name, first_seen_iso)-tripplar, nyast överst
    (därefter billigast överst som tie-breaker). Sidan är helt fristående
    (ingen extern JS/CSS), redo att servas direkt av GitHub Pages från
    /docs.
    """
    sorted_matches = sorted(
        matches,
        key=lambda t: (
            -_first_seen_epoch(t[2]),
            t[0].get("price_eur") is None,
            t[0].get("price_eur") or 0,
        ),
    )

    if sorted_matches:
        cards = []
        for item, shop_name, _first_seen in sorted_matches:
            image_url = item.get("image")
            if image_url:
                image_html = f'<img src="{html_mod.escape(image_url)}" alt="" loading="lazy">'
            else:
                image_html = '<div class="no-image">Ingen bild</div>'
            cards.append(
                _CARD_TEMPLATE.format(
                    url=html_mod.escape(item.get("url", "")),
                    image_html=image_html,
                    title=html_mod.escape(item.get("title", "")),
                    shop=html_mod.escape(shop_name),
                    price=html_mod.escape(_format_price(item.get("price_eur"))),
                )
            )
        body = f'<div class="grid">{"".join(cards)}</div>'
    else:
        body = '<div class="empty">Inga klockor matchar dina filter just nu.</div>'

    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    page = _PAGE_TEMPLATE.format(
        count=len(sorted_matches),
        updated=updated,
        filters_text=_format_filters(filters),
        body=body,
        repo=repo or "ditt-repo",
        schedule_text=schedule_text,
    )

    DASHBOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_PATH.write_text(page, encoding="utf-8")
