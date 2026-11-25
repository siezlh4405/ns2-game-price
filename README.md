# Switch 2 / Switch 台灣 eShop 特價追蹤

自動追蹤台灣 Nintendo eShop（新台幣 TWD）Switch 2 與 Switch 遊戲價格、特價折扣與歷史最低價，並透過 GitHub Actions + GitHub Pages 零成本部署。

## 架構

- **`scraper/`（Python 3.9+ 標準庫，免裝額外套件）**
  - `sources/tw_official.py`：抓台灣官網 `/tw/api/software`（含 Switch 2 標記）
  - `sources/hk_store.py`：抓香港官方數位商店 `store.nintendo.com.hk`（1,500+ 款繁中數位版遊戲）
  - `sources/manual.json`：可手動補充額外 NSUID
  - `price_fetcher.py`：每 50 款一批查詢 `api.ec.nintendo.com/v1/price?country=TW&lang=zh`
  - `history.py`：維護 `data/history.json` 記錄歷史價格與史低
- **`frontend/`（Vue 3 + TypeScript + Tailwind CSS + Vite）**
  - 讀取靜態 `public/data/games.json`
  - 支援特價中 / Switch 2 / Switch / 願望清單篩選、關鍵字搜尋與多種排序
- **`.github/workflows/`**
  - `update-data.yml`：每天台灣時間 09:00、21:00 自動執行爬蟲、更新歷史價格並觸發部署
  - `deploy.yml`：建置 Vue 前端並部署至 GitHub Pages

## 本機執行

```bash
# 1. 抓資料（測試時可加 --max-hk-pages 5 加快速度；不加則抓全部）
python scraper/main.py --max-hk-pages 10

# 2. 啟動前端開發伺服器
cd frontend
npm install
npm run dev
```

## 部署到 GitHub Pages

1. 將此專案推送到 GitHub 的 `main` 分支。
2. 到 Repo 的 **Settings → Pages → Build and deployment → Source**，選擇 **GitHub Actions**。
3. 到 **Actions** 分頁手動點一次 **Update Taiwan eShop Prices → Run workflow**，即會抓取全量資料並部署完成。

## 已知限制與待優化清單（Known Issues / Roadmap）

- [ ] **香港商店 (`store.nintendo.com.hk`) 在 GitHub Actions 雲端 IP 會被擋**：目前雲端排程抓香港清單會回傳 0 筆，先以本機同步 + `data/catalog.json` 快取兜底（台灣價格 API `api.ec.nintendo.com/v1/price` 在雲端仍可正常每日更新所有快取遊戲的即時價格）。後續可改用不擋雲端 IP 的清單來源（如日／美／歐區官方 JSON/XML、社群公開 NSUID 清單）或透過代理／Cloudflare Worker 抓取。
- [ ] **其他區域上架但台灣可買的遊戲**：部分獨立遊戲或跨區共用 NSUID 遊戲未列於香港商店，後續可整合日區／美區／歐區清單並透過 `country=TW` 過濾補齊。
- [ ] **史低標籤判斷優化**：剛建站初期因只有第一筆快照，所有特價遊戲都會顯示「史低」，後續可改為累積至少 2 次價格變動或追蹤達一定天數後才標示。
- [ ] **降價通知（選配）**：未來可在 GitHub Actions 偵測到願望清單或新史低時推送至 Discord / Telegram / Email。
