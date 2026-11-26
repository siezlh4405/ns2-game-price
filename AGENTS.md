# AGENTS.md — Switch 2 / Switch Taiwan eShop Price Tracker

Project map and working memory for AI coding assistants. Automatically loaded at the start of every session.

## Project Goal
Zero-cost Taiwan Nintendo eShop (TWD) price & discount tracker for Nintendo Switch 2 and Nintendo Switch games, built with a **Python scraper + Vue 3 (TS + Tailwind) static frontend**, automated via **GitHub Actions + GitHub Pages**.

- Live Repo: `https://github.com/siezlh4405/ns2-game-price`
- Live Site: `https://siezlh4405.github.io/ns2-game-price/`

## Repository Map

```text
ns2-game-price-tw/
├── AGENTS.md                        # This file (project map & conventions)
├── README.md                        # User docs + Known Issues / Roadmap
├── docs/                            # Self-contained HTML learning notes ("做中學筆記本")
│   ├── index.html                   # Index of all lessons (update whenever adding a new lesson)
│   └── 01-github-actions-deploy-and-update.html
├── scraper/                         # Python 3.9+ standard-library-only scraper (no pip deps)
│   ├── main.py                      # Entry point: merge catalog -> fetch TW prices -> update history -> write games.json
│   ├── price_fetcher.py             # Batch queries api.ec.nintendo.com/v1/price?country=TW&lang=zh (50 NSUIDs/batch)
│   ├── history.py                   # Tracks lowest price & compact price change log in data/history.json
│   ├── requirements.txt             # Intentionally empty (stdlib only)
│   └── sources/
│       ├── tw_official.py           # https://www.nintendo.com/tw/api/software (24 featured titles; accurate Switch 2 tags)
│       ├── titledb_hk.py            # raw.githubusercontent.com/blawar/titledb/master/HK.zh.json (~13,765 HK/TW titles; CI-friendly)
│       ├── hk_store.py              # https://store.nintendo.com.hk/games/all-released-games (~1,570 digital titles, 66 pages; local/proxy)
│       └── manual.json              # User-maintained extra NSUIDs
├── data/
│   ├── catalog.json                 # Persistent NSUID catalog cache (prevents data wipe if a source is blocked in CI)
│   └── history.json                 # Historical lowest prices & last 30 price-change points per NSUID
├── frontend/                        # Vue 3 + TypeScript + Tailwind CSS v3 + Vite 5
│   ├── vite.config.ts               # Uses base: './' so GitHub Pages works under any repo name
│   ├── public/data/games.json       # Generated static dataset consumed by frontend (./data/games.json)
│   └── src/
│       ├── App.vue                  # Main dashboard (default tab: on_sale, tabs, search, sort)
│       ├── components/GameCard.vue  # Game card (Switch 2 badge, discount%, countdown, all-time-low, wishlist)
│       ├── composables/useWishlist.ts # localStorage wishlist (key: ns2_tw_wishlist_v1)
│       └── types/game.ts            # Shared TypeScript interfaces
└── .github/workflows/
    ├── update-data.yml              # Cron 09:00 & 21:00 UTC+8 + manual; runs scraper, commits data/* + games.json, calls deploy.yml
    └── deploy.yml                   # Reusable workflow; builds Vue app & deploys frontend/dist to GitHub Pages
```

## Runtime & Tooling Constraints
- **Local Machine**: Windows, Python `3.9.6`, Node `v18.20.7`, npm `10.8.2`.
  - Keep Python code compatible with **Python 3.9+** (`from __future__ import annotations`, stdlib only).
  - Keep frontend dependencies compatible with **Node 18+** (Vite 5, Tailwind CSS v3 — do not upgrade to Vite 6+/7+ without checking Node version).
- **GitHub Actions**: Ubuntu latest, Python `3.12`, Node `22`, core actions on `@v7` (`actions/checkout@v7`, `actions/setup-python@v7`, `actions/setup-node@v7`) to avoid Node 20 runner deprecation warnings.

## Key APIs & Known Gotchas
1. **CORS**: All Nintendo endpoints (`api.ec.nintendo.com`, `nintendo.com/tw/api/software`, `store.nintendo.com.hk`) lack `Access-Control-Allow-Origin`. Frontend MUST read static `./data/games.json`, never fetch Nintendo directly from the browser.
2. **HK Store Blocked on CI IPs**: `store.nintendo.com.hk` blocks GitHub Actions' US datacenter IPs (returns 0 items in CI, works fine from Taiwan local IP).
   - **Mitigation**: `scraper/main.py` merges with `data/catalog.json` first and catches source errors so CI never wipes the catalog. `api.ec.nintendo.com/v1/price?country=TW` works reliably from CI.
3. **HK & TW NSUID Sharing (and Non-Sharing with JP/US/EU/KR/AU)**: Taiwan and Hong Kong share the exact same Nintendo Asia NSUID pool (100% overlap; ~4,546 of 14,019 catalog entries return valid TWD prices on `country=TW`). By contrast, JP/US/EU/KR/AU use completely separate regional NSUID pools (verified 0% hit rate on `country=TW`).
4. **Price API Rate Limit**: `api.ec.nintendo.com/v1/price` returns HTTP 403 if queried too aggressively with concurrency (~125 fast batches). `price_fetcher.py` uses sequential 0.4s pacing with 403/429 cooldown retries, and `main.py` caches `twNotFoundAt` in `data/catalog.json` (7-day TTL) so daily runs only query ~4,700 NSUIDs (~94 batches).
5. **Old Gist Endpoints Dead**: `ec.nintendo.com/api/{TW|HK}/zh/search/sales` returns 404; `nintendo.com/tw/data/json/switch_software.json` stopped updating in Oct 2024.
6. **Reusable Workflow Checkout**: `deploy.yml` MUST keep `with: ref: main` on `actions/checkout@v7`, otherwise when called by `update-data.yml` it checks out the pre-commit SHA instead of the newly committed `games.json`.

## Common Commands

```powershell
# Quick local scrape (10 pages of HK store)
python scraper/main.py --max-hk-pages 10

# Full local scrape (all ~66 pages of HK store + TW official -> updates catalog.json, history.json, games.json)
python scraper/main.py --workers 6

# Price-only refresh using cached catalog.json
python scraper/main.py --skip-hk

# Frontend dev & build
cd frontend
npm run dev
npm run build
```

## Active Roadmap / Known Issues (from README.md)
- **Cloudflare Worker proxy for `store.nintendo.com.hk` top 3–5 pages in CI**: Even with `titledb_hk.py` covering ~13,765 HK/TW titles in CI, ~235 newest Switch 2 / deluxe bundle titles appear first or exclusively on `store.nintendo.com.hk`. Adding a free Cloudflare Worker relay lets CI scrape the newest 3–5 pages daily for 100% zero-local automation.
- **Self-hosted WebP thumbnail cache (fallback if `wsrv.nl` is blocked)**: `GameCard.vue` currently proxies images via `wsrv.nl` (with direct fallback) to bypass corporate firewall blocks on `nintendo.*`. If corporate networks also block `wsrv.nl`, pre-generate ~320px WebP thumbnails (~12 KB each, ~55 MB total) and deploy them on the same `github.io` origin.
- Optional price-drop notifications (Discord / Telegram / Email) triggered from `update-data.yml`.
