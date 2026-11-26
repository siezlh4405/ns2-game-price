from __future__ import annotations

import json
import urllib.request
from typing import Any

TITLEDB_HK_URL = "https://raw.githubusercontent.com/blawar/titledb/master/HK.zh.json"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def _format_release_date(raw: Any) -> str:
    if raw is None:
        return ""
    s = str(raw).strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    return s


def _detect_platform(title: str) -> str:
    lower = title.lower()
    if "switch 2 edition" in lower:
        return "switch2_edition"
    if "switch 2" in lower or "ns2" in lower:
        return "switch2"
    return "switch"


def fetch_titledb_hk() -> list[dict[str, Any]]:
    """Fetch HK/TW region NSUID catalog from blawar/titledb (HK.zh.json).

    Taiwan and Hong Kong eShops share the same Nintendo Asia NSUID namespace.
    This source is hosted on GitHub Raw, so it works reliably from GitHub Actions CI
    without being blocked by store.nintendo.com.hk's regional IP filtering.
    """
    req = urllib.request.Request(
        TITLEDB_HK_URL,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    games: list[dict[str, Any]] = []
    for entry in payload.values():
        if not isinstance(entry, dict):
            continue

        # Skip demos and non-game DLC/add-ons (keep 7001 base games and 7007 bundles)
        if entry.get("isDemo"):
            continue

        nsuid_raw = entry.get("nsuId")
        if nsuid_raw is None:
            continue
        nsuid = str(nsuid_raw).strip()
        if not nsuid.isdigit() or not nsuid.startswith(("7001", "7007")):
            continue

        title = (entry.get("name") or "").strip()
        if not title:
            continue

        image_url = (
            entry.get("bannerUrl")
            or entry.get("iconUrl")
            or entry.get("frontBoxArt")
            or ""
        )

        games.append(
            {
                "nsuid": nsuid,
                "title": title,
                "platform": _detect_platform(title),
                "publisher": (entry.get("publisher") or "").strip(),
                "releaseDate": _format_release_date(entry.get("releaseDate")),
                "imageUrl": image_url,
                "storeUrl": f"https://store.nintendo.com.hk/{nsuid}",
                "sources": ["titledb_hk"],
            }
        )

    return games
