from __future__ import annotations

import json
import time
import urllib.error
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


def _fetch_batch(
    batch: list[str],
    batch_num: int,
    total_batches: int,
    country: str,
    lang: str,
) -> dict[str, dict[str, Any]]:
    params = urllib.parse.urlencode(
        {"country": country, "lang": lang, "ids": ",".join(batch)}
    )
    url = f"{PRICE_API_URL}?{params}"

    payload: dict[str, Any] | None = None
    max_attempts = 4
    for attempt in range(max_attempts):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 429) and attempt < max_attempts - 1:
                wait_sec = 20 * (attempt + 1)
                print(
                    f"[price_fetcher] Batch {batch_num}/{total_batches} hit HTTP {exc.code}; "
                    f"cooling down {wait_sec}s..."
                )
                time.sleep(wait_sec)
            elif attempt == max_attempts - 1:
                print(f"[price_fetcher] Batch {batch_num}/{total_batches} failed: {exc}")
            else:
                time.sleep(2.0 * (attempt + 1))
        except Exception as exc:
            if attempt == max_attempts - 1:
                print(f"[price_fetcher] Batch {batch_num}/{total_batches} failed: {exc}")
            else:
                time.sleep(2.0 * (attempt + 1))

    batch_result: dict[str, dict[str, Any]] = {}
    if not payload:
        return batch_result

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

        batch_result[title_id] = {
            "salesStatus": sales_status,
            "currency": reg_obj.get("currency") or "TWD",
            "regularPrice": regular_price,
            "discountPrice": discount_price,
            "discountPercent": discount_percent,
            "discountStart": disc_obj.get("start_datetime"),
            "discountEnd": disc_obj.get("end_datetime"),
        }

    return batch_result


def fetch_tw_prices(
    nsuids: list[str],
    country: str = "TW",
    lang: str = "zh",
    batch_size: int = 50,
    delay_sec: float = 0.4,
    workers: int = 1,
) -> dict[str, dict[str, Any]]:
    """Batch-query Nintendo eShop price API with polite pacing to avoid 403 rate limits."""
    _ = workers  # Kept for backwards-compatible signature; sequential avoids Akamai 403.
    result: dict[str, dict[str, Any]] = {}
    unique_ids = list(dict.fromkeys(nsuids))
    batches = [
        unique_ids[idx : idx + batch_size]
        for idx in range(0, len(unique_ids), batch_size)
    ]
    total_batches = len(batches)
    if total_batches == 0:
        return result

    for idx, batch in enumerate(batches):
        batch_num = idx + 1
        result.update(_fetch_batch(batch, batch_num, total_batches, country, lang))
        if batch_num % 25 == 0 or batch_num == total_batches:
            print(f"[price_fetcher] Progress: {batch_num}/{total_batches} batches")
        if delay_sec > 0 and batch_num < total_batches:
            time.sleep(delay_sec)

    return result
