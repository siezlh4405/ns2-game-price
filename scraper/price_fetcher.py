from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from typing import Any

PRICE_API_URL = "https://api.ec.nintendo.com/v1/price"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def _to_int_price(raw_value: Any) -> int | None:
    if raw_value is None:
        return None
    try:
        return int(round(float(raw_value)))
    except (ValueError, TypeError):
        return None


def fetch_tw_prices(
    nsuids: list[str],
    country: str = "TW",
    lang: str = "zh",
    batch_size: int = 50,
    delay_sec: float = 0.15,
) -> dict[str, dict[str, Any]]:
    """Batch-query Nintendo eShop price API and return a map of nsuid -> price info."""
    result: dict[str, dict[str, Any]] = {}
    unique_ids = list(dict.fromkeys(nsuids))
    total_batches = (len(unique_ids) + batch_size - 1) // batch_size

    for idx in range(0, len(unique_ids), batch_size):
        batch = unique_ids[idx : idx + batch_size]
        batch_num = idx // batch_size + 1
        params = urllib.parse.urlencode(
            {"country": country, "lang": lang, "ids": ",".join(batch)}
        )
        url = f"{PRICE_API_URL}?{params}"

        payload: dict[str, Any] | None = None
        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=20) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                break
            except Exception as exc:
                if attempt == 2:
                    print(f"[price_fetcher] Batch {batch_num}/{total_batches} failed: {exc}")
                else:
                    time.sleep(1.0 * (attempt + 1))

        if not payload:
            continue

        for entry in payload.get("prices", []):
            title_id = str(entry.get("title_id") or "")
            if not title_id:
                continue

            sales_status = entry.get("sales_status") or "unknown"
            reg_obj = entry.get("regular_price") or {}
            disc_obj = entry.get("discount_price") or {}

            regular_price = _to_int_price(reg_obj.get("raw_value"))
            discount_price = _to_int_price(disc_obj.get("raw_value"))

            discount_percent = 0
            if (
                regular_price
                and discount_price is not None
                and regular_price > 0
                and discount_price < regular_price
            ):
                discount_percent = round(
                    (regular_price - discount_price) / regular_price * 100
                )

            result[title_id] = {
                "salesStatus": sales_status,
                "currency": reg_obj.get("currency") or "TWD",
                "regularPrice": regular_price,
                "discountPrice": discount_price,
                "discountPercent": discount_percent,
                "discountStart": disc_obj.get("start_datetime"),
                "discountEnd": disc_obj.get("end_datetime"),
            }

        if batch_num % 10 == 0 or batch_num == total_batches:
            print(f"[price_fetcher] Progress: {batch_num}/{total_batches} batches")

        if delay_sec > 0 and batch_num < total_batches:
            time.sleep(delay_sec)

    return result
