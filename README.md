# 中華棒球追蹤站 — 部署說明

## 檔案結構

```
your-repo/
├── index.html              ← taiwan-baseball-tracker.html 改名
├── cpbl_data.json          ← Python 爬蟲輸出（自動產生）
├── cpbl_scraper.py         ← 中職爬蟲
├── cloudflare-worker.js    ← API Key 代理
└── .github/
    └── workflows/
        └── update_cpbl.yml ← 自動排程（選用）
```

---

## Step 1：GitHub Pages 部署

1. 建立 public repo（例如 `baseball-tracker`）
2. 把 `taiwan-baseball-tracker.html` 改名為 `index.html` 上傳
3. Settings → Pages → Source 選 `main` branch → Save
4. 網址：`https://你的帳號.github.io/baseball-tracker/`

---

## Step 2：Cloudflare Worker（API Key 保護）

1. 登入 [dash.cloudflare.com](https://dash.cloudflare.com)
2. Workers & Pages → Create Worker
3. 貼上 `cloudflare-worker.js` 的內容
4. **Settings → Variables → Environment Variables** 新增：
   ```
   ANTHROPIC_API_KEY = sk-ant-xxxxxxxxxx
   ```
5. Deploy，取得 Worker URL，例如：
   ```
   https://baseball-proxy.yourname.workers.dev
   ```
6. 打開 `index.html`，找到 CONFIG 區塊，填入：
   ```javascript
   PROXY_URL: "https://baseball-proxy.yourname.workers.dev",
   ```

---

## Step 3：中職爬蟲

### 手動執行

```bash
pip install requests beautifulsoup4 lxml
python cpbl_scraper.py
```

執行後會產生 `cpbl_data.json`，把它上傳到 repo 根目錄即可。

---

## Step 4：GitHub Actions 自動排程（選用）

建立 `.github/workflows/update_cpbl.yml`：

```yaml
name: Update CPBL Data

on:
  schedule:
    - cron: '0 0 * * *'   # 每天 UTC 00:00 = 台灣時間 08:00
  workflow_dispatch:        # 也可以手動觸發

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install requests beautifulsoup4 lxml

      - name: Run scraper
        run: python cpbl_scraper.py

      - name: Commit and push
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add cpbl_data.json
          git diff --staged --quiet || git commit -m "chore: update CPBL data $(date '+%Y-%m-%d %H:%M')"
          git push
```

設定好後，每天早上 8 點台灣時間會自動爬取並更新 `cpbl_data.json`。

---

## 快取說明

| 類型       | TTL     | 說明                       |
|------------|---------|----------------------------|
| 旅外成績   | 24 小時  | localStorage，重整不消失    |
| 球員新聞   | 2 小時   | localStorage，可手動刷新    |
| 中職資料   | 4 小時   | 優先讀 cpbl_data.json       |

---

## 資料來源

- MLB Stats API：`statsapi.mlb.com`（免費官方 API）
- 中職排名/賽程：`en.cpbl.com.tw`（Python 爬蟲）
- 旅外成績/新聞：Claude AI + Web Search
- 球員履歷：台灣棒球維基館 `twbsball.dils.tku.edu.tw`
