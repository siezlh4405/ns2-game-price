from __future__ import annotations

import json
import urllib.request
from typing import Any

TW_SOFTWARE_API = "https://www.nintendo.com/tw/api/software"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def _normalize_platform(hardware_category: str | None) -> str:
    if not hardware_category:
        return "switch"
    lower = hardware_category.lower()
    if "switch 2 edition" in lower:
        return "switch2_edition"
    if "switch 2" in lower:
        return "switch2"
    return "switch"


def fetch_tw_official() -> list[dict[str, Any]]:
    """Fetch featured Switch & Switch 2 titles from Nintendo Taiwan official API."""
    req = urllib.request.Request(
        TW_SOFTWARE_API,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    games: list[dict[str, Any]] = []
    for item in payload.get("items", []):
        nsuid = str(item.get("nsuid") or "").strip()
        if not nsuid.isdigit():
            continue

        image_hero = item.get("imageHero") or {}
        release_raw = item.get("releaseDate") or item.get("releaseDateDownload") or ""
        release_date = release_raw[:10] if len(release_raw) >= 10 else ""

        games.append(
            {
                "nsuid": nsuid,
                "title": (item.get("title") or "").strip(),
                "platform": _normalize_platform(item.get("hardwareCategory")),
                "publisher": (item.get("publisher") or "").strip(),
                "releaseDate": release_date,
                "imageUrl": image_hero.get("url") or "",
                "storeUrl": f"https://store.nintendo.com.hk/{nsuid}",
                "sources": ["tw_official"],
            }
        )

    return games
