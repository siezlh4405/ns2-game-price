# Switch 2 / Switch 台灣 eShop 特價追蹤

自動追蹤台灣 Nintendo eShop（新台幣 TWD）Switch 2 與 Switch 遊戲價格、特價折扣與歷史最低價，並透過 GitHub Actions + GitHub Pages 零成本部署。

## 架構

- **`scraper/`（Python 3.9+ 標準庫，免裝額外套件）**
  - `sources/tw_official.py`：抓台灣官網 `/tw/api/software`（含 Switch 2 標記）
  - `sources/titledb_hk.py`：抓社群 `blawar/titledb`（`HK.zh.json`，13,700+ 款港台區本體與組合包，GitHub Actions 不會被擋 IP）
  - `sources/hk_store.py`：抓香港官方數位商店 `store.nintendo.com.hk`（1,500+ 款繁中數位版遊戲，本機可補齊最新 Switch 2／豪華版）
  - `sources/manual.json`：可手動補充額外 NSUID
  - `price_fetcher.py`：每 50 款一批查詢 `api.ec.nintendo.com/v1/price?country=TW&lang=zh`（含節流與 403/429 冷卻重試）
  - `history.py`：維護 `data/history.json` 記錄歷史價格與史低
- **`frontend/`（Vue 3 + TypeScript + Tailwind CSS + Vite）**
  - 讀取靜態 `public/data/games.json`（4,500+ 款台灣有價遊戲）
  - 支援特價中 / Switch 2 / Switch / 願望清單篩選、關鍵字搜尋、多種排序與分批載入
  - 封面圖預設透過免費 `wsrv.nl` 轉 WebP 縮圖（繞過公司網路擋任天堂網域），失敗時自動退回原網址
- **`.github/workflows/`**
  - `update-data.yml`：每天台灣時間 09:17、21:17 自動執行爬蟲（`--skip-hk`）、更新歷史價格並觸發部署
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

- [x] **擴充台灣 eShop 全量目錄（CI 不被擋）**：已整合 `blawar/titledb`（`HK.zh.json`），使台灣有價遊戲從 1,098 款擴充至 **4,546 款**；且實測確認日／美／歐／韓／澳區 NSUID 與 `country=TW` 共通率為 0%，僅港台共用同一套亞洲區 NSUID。
- [ ] **用免費 Cloudflare Worker 補齊 `store.nintendo.com.hk` 最新新作（達成 100% 零本機全自動）**：`store.nintendo.com.hk` 在 GitHub Actions 美國機房 IP 會被擋，目前 CI 以 `--skip-hk` 略過（靠 `titledb_hk` + `tw_official` + `catalog.json` 兜底）；但最新 Switch 2 遊戲與部分第三方數位豪華版仍以香港官方商店上架最快。後續可架設免費 Cloudflare Worker（每日 10 萬次免費額度）當轉發代理，讓 CI 每天只抓前 3～5 頁最新上架商品即可完全免本機操作。
- [ ] **封面圖同網域 WebP 縮圖快取（備案）**：目前前端已改走免費 `wsrv.nl` 代理（含失敗退回原網址）以繞過公司防火牆封鎖 `nintendo.*` 網域；若實測公司網路連 `wsrv.nl` 也封鎖，可改由爬蟲／CI 將封面壓成小尺寸 WebP 縮圖（~12 KB/張，約 50–60 MB）部署在同一個 `github.io` 網域，確保只要打得開網站就 100% 看得到圖。
- [x] **史低標籤判斷優化**：已調整為需累積至少 2 次價格紀錄（`len(records) >= 2`）才顯示「🔥 史低」，避免首次抓到特價就全部標成史低。
- [ ] **降價通知（選配）**：未來可在 GitHub Actions 偵測到願望清單或新史低時推送至 Discord / Telegram / Email。
