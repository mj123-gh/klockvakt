from __future__ import annotations

import json
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent.parent / "state" / "seen.json"

# Tidsstämpel för poster som fanns i state innan vi började spara när varje
# objekt först upptäcktes - sorteras naturligt som "äldst" (dashboarden
# visar nyaste överst).
UNKNOWN_FIRST_SEEN = "1970-01-01T00:00:00+00:00"


def load_seen() -> dict[str, str]:
    """
    Returnerar {id: first_seen_iso}. En äldre state-fil (en ren lista med
    id:n, från innan tidsstämplar infördes) migreras automatiskt till det
    nya formatet vid inläsning.
    """
    if not STATE_PATH.exists():
        return {}
    # utf-8-sig tolererar en BOM i filens början (t.ex. om filen råkat sparas
    # med Anteckningar eller PowerShells Set-Content, som lägger till en) men
    # fungerar precis lika bra på filer utan BOM.
    with STATE_PATH.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)
    if isinstance(data, list):
        return {item_id: UNKNOWN_FIRST_SEEN for item_id in data}
    return data


def save_seen(seen: dict[str, str]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STATE_PATH.open("w", encoding="utf-8") as f:
        json.dump(dict(sorted(seen.items())), f, ensure_ascii=False, indent=2)
