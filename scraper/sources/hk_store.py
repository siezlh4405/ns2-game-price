from __future__ import annotations

import html as html_lib
import math
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

HK_BASE_URL = "https://store.nintendo.com.hk/games/all-released-games"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

ITEM_BLOCK_RE = re.compile(
    r'<li class="item product product-item">(.*?)</li>', re.DOTALL
)
LINK_TITLE_RE = re.compile(
    r'<a class="product-item-link"[^>]*href="https://store\.nintendo\.com\.hk/(\d{14})"[^>]*>(.*?)</a>',
    re.DOTALL,
)
IMAGE_RE = re.compile(
    r'<img[^>]*class="product-image-photo"[^>]*src="([^"]+)"', re.DOTALL
)
RELEASE_RE = re.compile(
    r'<div class="category-product-item-released">\s*<span>[^<]*</span>\s*([^<]+)</div>',
    re.DOTALL,
)
PLATFORM_LABEL_RE = re.compile(
    r'<p class="label_platform"[^>]*>(.*?)</p>', re.DOTALL
)
TOOLBAR_NUM_RE = re.compile(r'<span class="toolbar-number">(\d+)</span>')


def _parse_release_date(raw: str) -> str:
    text = raw.strip()
    m = re.match(r"^(\d{2})\.(\d{1,2})\.(\d{1,2})$", text)
    if m:
        yy, mm, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))
        year = 2000 + yy
        return f"{year:04d}-{mm:02d}-{dd:02d}"
    return text


def _detect_platform(title: str, label_html: str) -> str:
    combined = f"{title} {label_html}".lower()
    if "switch 2 edition" in combined:
        return "switch2_edition"
    if "switch 2" in combined or "ns2" in combined:
        return "switch2"
    return "switch"


def _fetch_page_html(page: int) -> str:
    url = f"{HK_BASE_URL}?p={page}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def _parse_page_items(page_html: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for block in ITEM_BLOCK_RE.findall(page_html):
        link_m = LINK_TITLE_RE.search(block)
        if not link_m:
            continue

        nsuid = link_m.group(1)
        title = html_lib.unescape(re.sub(r"\s+", " ", link_m.group(2)).strip())
        img_m = IMAGE_RE.search(block)
        rel_m = RELEASE_RE.search(block)
        plat_m = PLATFORM_LABEL_RE.search(block)

        image_url = html_lib.unescape(img_m.group(1)) if img_m else ""
        release_date = _parse_release_date(rel_m.group(1)) if rel_m else ""
        label_html = plat_m.group(1) if plat_m else ""

        items.append(
            {
                "nsuid": nsuid,
                "title": title,
                "platform": _detect_platform(title, label_html),
                "publisher": "",
                "releaseDate": release_date,
                "imageUrl": image_url,
                "storeUrl": f"https://store.nintendo.com.hk/{nsuid}",
                "sources": ["hk_store"],
            }
        )
    return items


def fetch_hk_store(
    max_pages: int = 0, workers: int = 4, delay_sec: float = 0.1
) -> list[dict[str, Any]]:
    """Fetch digital game list from Nintendo HK official web store.

    Args:
        max_pages: 0 means fetch all pages; > 0 limits pages for quick local runs.
        workers: Number of concurrent page fetchers.
        delay_sec: Polite pause per worker request.
    """
    first_html = _fetch_page_html(1)
    all_games = _parse_page_items(first_html)

    toolbar_nums = [int(x) for x in TOOLBAR_NUM_RE.findall(first_html)]
    total_pages = 1
    if len(toolbar_nums) >= 3 and toolbar_nums[1] > 0:
        per_page = toolbar_nums[1]
        total_items = toolbar_nums[2]
        total_pages = math.ceil(total_items / per_page)

    if max_pages > 0:
        total_pages = min(total_pages, max_pages)

    print(f"[hk_store] Page 1 parsed ({len(all_games)} items). Target pages: {total_pages}")

    if total_pages <= 1:
        return all_games

    def fetch_and_parse(page_num: int) -> list[dict[str, Any]]:
        if delay_sec > 0:
            time.sleep(delay_sec)
        for attempt in range(3):
            try:
                page_html = _fetch_page_html(page_num)
                return _parse_page_items(page_html)
            except Exception as exc:
                if attempt == 2:
                    print(f"[hk_store] Failed page {page_num}: {exc}")
                    return []
                time.sleep(1.0 * (attempt + 1))
        return []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(fetch_and_parse, p): p for p in range(2, total_pages + 1)
        }
        completed = 1
        for future in as_completed(futures):
            completed += 1
            page_items = future.result()
            all_games.extend(page_items)
            if completed % 10 == 0 or completed == total_pages:
                print(
                    f"[hk_store] Progress: {completed}/{total_pages} pages "
                    f"({len(all_games)} items)"
                )

    return all_games
