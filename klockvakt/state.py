from __future__ import annotations

import json
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent.parent / "state" / "seen.json"


def load_seen() -> set[str]:
    if not STATE_PATH.exists():
        return set()
    with STATE_PATH.open("r", encoding="utf-8") as f:
        return set(json.load(f))


def save_seen(seen: set[str]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STATE_PATH.open("w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, ensure_ascii=False, indent=2)
