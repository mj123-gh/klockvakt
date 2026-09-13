from __future__ import annotations

from typing import Any


def matches(item: dict[str, Any], filters: dict[str, Any]) -> bool:
    title = (item.get("title") or "").lower()
    price = item.get("price_eur")

    brands = [b.lower() for b in filters.get("brands", [])]
    if brands and not any(b in title for b in brands):
        return False

    include = [k.lower() for k in filters.get("keywords_include", [])]
    if include and not any(k in title for k in include):
        return False

    exclude = [k.lower() for k in filters.get("keywords_exclude", [])]
    if exclude and any(k in title for k in exclude):
        return False

    min_price = filters.get("min_price_eur")
    if min_price is not None and price is not None and price < min_price:
        return False

    max_price = filters.get("max_price_eur")
    if max_price is not None and price is not None and price > max_price:
        return False

    return True
