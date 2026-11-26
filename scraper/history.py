from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_history(history_path: Path) -> dict[str, dict[str, Any]]:
    if not history_path.exists():
        return {}
    try:
        data = json.loads(history_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data.get("games", data)
    except Exception as exc:
        print(f"[history] Warning: could not parse {history_path}: {exc}")
    return {}


def update_history(
    history: dict[str, dict[str, Any]],
    nsuid: str,
    current_price: int | None,
    regular_price: int | None,
    today_str: str,
) -> tuple[int | None, bool, list[dict[str, Any]]]:
    """Update price history for a game and return (allTimeLow, isAllTimeLow, records)."""
    if current_price is None:
        existing = history.get(nsuid, {})
        return existing.get("lowestPrice"), False, existing.get("records", [])

    entry = history.get(nsuid)
    if not entry:
        entry = {
            "lowestPrice": current_price,
            "lowestDate": today_str,
            "regularPrice": regular_price,
            "records": [{"date": today_str, "price": current_price}],
        }
        history[nsuid] = entry
    else:
        if regular_price is not None:
            entry["regularPrice"] = regular_price
        prev_lowest = entry.get("lowestPrice")
        if prev_lowest is None or current_price < prev_lowest:
            entry["lowestPrice"] = current_price
            entry["lowestDate"] = today_str

        records = entry.setdefault("records", [])
        if not records or records[-1].get("price") != current_price:
            records.append({"date": today_str, "price": current_price})
            # Keep last 30 price-change points per game to keep repo file compact
            if len(records) > 30:
                entry["records"] = records[-30:]

    lowest_price = entry.get("lowestPrice")
    records = entry.get("records", [])
    is_on_sale = regular_price is not None and current_price < regular_price
    # Require at least 2 recorded price points so initial discovery doesn't mark every sale as all-time low
    is_all_time_low = bool(
        is_on_sale
        and len(records) >= 2
        and lowest_price is not None
        and current_price <= lowest_price
    )
    return lowest_price, is_all_time_low, records


def save_history(
    history_path: Path, history: dict[str, dict[str, Any]], updated_at: str
) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updatedAt": updated_at,
        "count": len(history),
        "games": history,
    }
    history_path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
