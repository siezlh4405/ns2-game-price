from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from history import load_history, save_history, update_history
from price_fetcher import fetch_tw_prices
from sources.hk_store import fetch_hk_store
from sources.tw_official import fetch_tw_official

ROOT_DIR = Path(__file__).resolve().parent.parent
MANUAL_PATH = Path(__file__).resolve().parent / "sources" / "manual.json"
CATALOG_PATH = ROOT_DIR / "data" / "catalog.json"
HISTORY_PATH = ROOT_DIR / "data" / "history.json"
OUTPUT_PATH = ROOT_DIR / "frontend" / "public" / "data" / "games.json"

PLATFORM_PRIORITY = {
    "switch2": 3,
    "switch2_edition": 2,
    "switch": 1,
}


def load_cached_catalog() -> list[dict[str, Any]]:
    if not CATALOG_PATH.exists():
        return []
    try:
        payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        items = payload.get("games", payload) if isinstance(payload, dict) else payload
        if isinstance(items, list):
            return items
    except Exception as exc:
        print(f"[catalog] Warning: failed to read {CATALOG_PATH}: {exc}")
    return []


def save_cached_catalog(catalog: dict[str, dict[str, Any]], updated_at: str) -> None:
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    games_sorted = sorted(catalog.values(), key=lambda g: g["nsuid"])
    payload = {
        "updatedAt": updated_at,
        "count": len(games_sorted),
        "games": games_sorted,
    }
    CATALOG_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def load_manual_games() -> list[dict[str, Any]]:
    if not MANUAL_PATH.exists():
        return []
    try:
        items = json.loads(MANUAL_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[manual] Failed to load manual.json: {exc}")
        return []

    games: list[dict[str, Any]] = []
    for item in items:
        nsuid = str(item.get("nsuid") or "").strip()
        if not nsuid.isdigit():
            continue
        games.append(
            {
                "nsuid": nsuid,
                "title": (item.get("title") or nsuid).strip(),
                "platform": item.get("platform") or "switch",
                "publisher": item.get("publisher") or "",
                "releaseDate": item.get("releaseDate") or "",
                "imageUrl": item.get("imageUrl") or "",
                "storeUrl": item.get("storeUrl")
                or f"https://store.nintendo.com.hk/{nsuid}",
                "sources": ["manual"],
            }
        )
    return games


def merge_catalog(lists: list[list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for game_list in lists:
        for game in game_list:
            nsuid = game["nsuid"]
            if nsuid not in merged:
                merged[nsuid] = {
                    **game,
                    "sources": list(game.get("sources", [])),
                }
                continue

            existing = merged[nsuid]
            # Prefer higher-specificity platform (switch2 > switch2_edition > switch)
            if PLATFORM_PRIORITY.get(game.get("platform", "switch"), 0) > PLATFORM_PRIORITY.get(
                existing.get("platform", "switch"), 0
            ):
                existing["platform"] = game["platform"]

            # Fill missing metadata
            for field in ("title", "publisher", "releaseDate", "imageUrl", "storeUrl"):
                if not existing.get(field) and game.get(field):
                    existing[field] = game[field]

            # Prefer tw_official title / image when available
            if "tw_official" in game.get("sources", []):
                if game.get("title"):
                    existing["title"] = game["title"]
                if game.get("imageUrl"):
                    existing["imageUrl"] = game["imageUrl"]
                if game.get("publisher"):
                    existing["publisher"] = game["publisher"]

            for src in game.get("sources", []):
                if src not in existing["sources"]:
                    existing["sources"].append(src)

    return merged


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch Taiwan Switch & Switch 2 eShop prices and discounts."
    )
    parser.add_argument(
        "--max-hk-pages",
        type=int,
        default=0,
        help="Limit HK store pages for quick local testing (0 = fetch all pages).",
    )
    parser.add_argument(
        "--skip-hk",
        action="store_true",
        help="Skip scraping HK store and rely on cached catalog.json + tw_official.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Concurrent workers for HK store scraping.",
    )
    args = parser.parse_args()

    now_utc = datetime.now(timezone.utc)
    updated_at = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    today_str = now_utc.strftime("%Y-%m-%d")

    cached_games = load_cached_catalog()
    print(f"[main] 0. Loaded {len(cached_games)} cached titles from data/catalog.json")

    print("[main] 1. Fetching Nintendo Taiwan official software list...")
    tw_games: list[dict[str, Any]] = []
    try:
        tw_games = fetch_tw_official()
        print(f"[main]    -> {len(tw_games)} titles from tw_official")
    except Exception as exc:
        print(f"[main]    -> tw_official failed (using cache): {exc}")

    hk_games: list[dict[str, Any]] = []
    if args.skip_hk:
        print("[main] 2. Skipping HK store (--skip-hk)")
    else:
        print("[main] 2. Fetching Nintendo HK digital store list...")
        try:
            hk_games = fetch_hk_store(
                max_pages=args.max_hk_pages, workers=args.workers
            )
            print(f"[main]    -> {len(hk_games)} titles from hk_store")
        except Exception as exc:
            print(f"[main]    -> hk_store failed (using cache): {exc}")

    manual_games = load_manual_games()
    print(f"[main]    -> {len(manual_games)} titles from manual.json")

    catalog = merge_catalog([cached_games, tw_games, hk_games, manual_games])
    print(f"[main] 3. Merged unique NSUIDs: {len(catalog)}")

    if catalog:
        save_cached_catalog(catalog, updated_at)

    print("[main] 4. Querying Taiwan eShop prices (country=TW)...")
    prices = fetch_tw_prices(list(catalog.keys()), country="TW", lang="zh")

    history = load_history(HISTORY_PATH)

    output_games: list[dict[str, Any]] = []
    on_sale_count = 0
    switch2_count = 0
    all_time_low_count = 0

    for nsuid, game in catalog.items():
        price_info = prices.get(nsuid)
        if not price_info:
            continue
        if price_info["salesStatus"] == "not_found":
            continue
        if price_info["regularPrice"] is None:
            continue

        regular_price = price_info["regularPrice"]
        discount_price = price_info["discountPrice"]
        current_price = discount_price if discount_price is not None else regular_price
        is_on_sale = discount_price is not None and discount_price < regular_price

        all_time_low, is_all_time_low, _ = update_history(
            history, nsuid, current_price, regular_price, today_str
        )

        if is_on_sale:
            on_sale_count += 1
        if game["platform"] in ("switch2", "switch2_edition"):
            switch2_count += 1
        if is_all_time_low:
            all_time_low_count += 1

        output_games.append(
            {
                "nsuid": nsuid,
                "title": game["title"],
                "platform": game["platform"],
                "publisher": game["publisher"],
                "releaseDate": game["releaseDate"],
                "imageUrl": game["imageUrl"],
                "storeUrl": game["storeUrl"],
                "salesStatus": price_info["salesStatus"],
                "currency": price_info["currency"],
                "regularPrice": regular_price,
                "discountPrice": discount_price,
                "currentPrice": current_price,
                "discountPercent": price_info["discountPercent"],
                "discountStart": price_info["discountStart"],
                "discountEnd": price_info["discountEnd"],
                "isOnSale": is_on_sale,
                "allTimeLow": all_time_low,
                "isAllTimeLow": is_all_time_low,
                "sources": game["sources"],
            }
        )

    # Sort: on-sale first (highest discount%), then lowest currentPrice
    output_games.sort(
        key=lambda g: (
            0 if g["isOnSale"] else 1,
            -g["discountPercent"],
            g["currentPrice"],
            g["title"],
        )
    )

    save_history(HISTORY_PATH, history, updated_at)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updatedAt": updated_at,
        "country": "TW",
        "currency": "TWD",
        "stats": {
            "total": len(output_games),
            "onSale": on_sale_count,
            "switch2": switch2_count,
            "allTimeLow": all_time_low_count,
        },
        "games": output_games,
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    print(
        f"[main] Done! Saved {len(output_games)} TW games "
        f"({on_sale_count} on sale, {switch2_count} Switch 2) -> {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
