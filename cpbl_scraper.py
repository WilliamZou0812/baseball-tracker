"""
CPBL 中職資料爬蟲
爬取對象：en.cpbl.com.tw（英文官網）
輸出：cpbl_data.json（放在與 index.html 相同目錄）

安裝依賴：
  pip install requests beautifulsoup4 lxml

執行方式：
  python cpbl_scraper.py

GitHub Actions 自動排程（每天早上 8:00 台灣時間執行）請見 README.md
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, timedelta
import sys

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}

BASE = "https://en.cpbl.com.tw"

TEAM_ZH = {
    "Uni-President 7-ELEVEn Lions": "統一7-ELEVEn獅",
    "Chinatrust Brothers":          "中信兄弟",
    "Rakuten Monkeys":              "樂天桃猿",
    "Fubon Guardians":              "富邦悍將",
    "TSG Hawks":                    "台鋼雄鷹",
    "Wei Chuan Dragons":            "味全龍",
    # 備用名稱
    "Lions":      "統一獅",
    "Brothers":   "中信兄弟",
    "Monkeys":    "樂天桃猿",
    "Guardians":  "富邦悍將",
    "Hawks":      "台鋼雄鷹",
    "Dragons":    "味全龍",
}

def zh_name(en):
    for k, v in TEAM_ZH.items():
        if k.lower() in en.lower():
            return v
    return en


# ─────────────────────────────────────────
# 1. 排名
# ─────────────────────────────────────────
def scrape_standings():
    print("[standings] 爬取中...")
    url = f"{BASE}/standings/season"
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        res.raise_for_status()
    except Exception as e:
        print(f"  ✗ 失敗：{e}")
        return []

    soup = BeautifulSoup(res.text, "lxml")
    standings = []

    # 找包含 standings 的表格
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cols = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
            if not cols or len(cols) < 5:
                continue
            # 跳過 header 行
            if cols[0] in ("", "Rank", "#", "Team"):
                continue
            # 嘗試解析：Rank / Team / W / L / PCT / GB
            try:
                rank = int(re.sub(r'\D', '', cols[0])) if re.search(r'\d', cols[0]) else len(standings) + 1
                # 找隊名欄位（第一個不是數字的欄位）
                team_col = next((c for c in cols if re.search(r'[A-Za-z]', c)), "")
                nums = [c for c in cols if re.match(r'^[\d.]+$', c.replace("-", "0"))]
                if len(nums) < 4:
                    continue
                w = int(nums[0])
                l = int(nums[1])
                pct_raw = float(nums[2]) if '.' in nums[2] else None
                pct = f".{int(round((pct_raw or w/(w+l+0.001))*1000)):03d}" if w+l > 0 else ".000"
                gb = nums[3] if nums[3] != "0" else "-"
                standings.append({
                    "rank": rank,
                    "team": zh_name(team_col),
                    "teamEn": team_col,
                    "w": w, "l": l,
                    "pct": pct,
                    "gb": gb
                })
            except (ValueError, IndexError):
                continue

    # fallback：如果爬到空的，試 alternate selector
    if not standings:
        print("  → 試備用 selector...")
        for tag in soup.find_all(class_=re.compile(r'standing|rank|team', re.I)):
            text = tag.get_text(" ", strip=True)
            if re.search(r'\d+\s+\d+', text):
                print(f"  候選區塊：{text[:80]}")

    print(f"  ✓ 取得 {len(standings)} 筆排名")
    return standings


# ─────────────────────────────────────────
# 2. 近期賽程（前後 7 天）
# ─────────────────────────────────────────
def scrape_schedule():
    print("[schedule] 爬取中...")
    url = f"{BASE}/schedule"
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        res.raise_for_status()
    except Exception as e:
        print(f"  ✗ 失敗：{e}")
        return []

    soup = BeautifulSoup(res.text, "lxml")
    schedule = []
    today = datetime.now()
    window_start = today - timedelta(days=7)
    window_end   = today + timedelta(days=7)

    # 嘗試找賽程表
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        current_date = None
        for row in rows:
            cols = [td.get_text(" ", strip=True) for td in row.find_all(["td", "th"])]
            if not cols:
                continue

            # 嘗試找日期欄
            date_match = re.search(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', " ".join(cols))
            if not date_match:
                date_match = re.search(r'(\d{1,2})[/-](\d{1,2})', " ".join(cols))
                if date_match:
                    m, d = date_match.group(1), date_match.group(2)
                    current_date = f"{today.year}/{int(m):02d}/{int(d):02d}"
            else:
                y, m, d = date_match.groups()
                current_date = f"{y}/{int(m):02d}/{int(d):02d}"

            if not current_date:
                continue

            # 找主客隊
            teams = [c for c in cols if re.search(r'[A-Za-z]{3}', c) and len(c) < 40]
            if len(teams) < 2:
                continue

            # 找比分
            score_match = re.search(r'(\d+)\s*[:\-]\s*(\d+)', " ".join(cols))
            time_match  = re.search(r'\d{1,2}:\d{2}', " ".join(cols))

            try:
                game_dt = datetime.strptime(current_date, "%Y/%m/%d")
            except ValueError:
                continue

            if not (window_start <= game_dt <= window_end):
                continue

            if score_match:
                score = f"{score_match.group(1)}-{score_match.group(2)}"
                status = "final"
            elif time_match:
                score = time_match.group(0)
                status = "upcoming" if game_dt >= today.replace(hour=0, minute=0) else "final"
            else:
                continue

            schedule.append({
                "date":   current_date[5:],   # MM/DD
                "away":   zh_name(teams[0]),
                "home":   zh_name(teams[1]),
                "score":  score,
                "status": status,
            })

    # 去重
    seen = set()
    unique_schedule = []
    for g in schedule:
        key = f"{g['date']}-{g['away']}-{g['home']}"
        if key not in seen:
            seen.add(key)
            unique_schedule.append(g)

    print(f"  ✓ 取得 {len(unique_schedule)} 筆賽程")
    return unique_schedule[:20]  # 最多20筆


# ─────────────────────────────────────────
# 3. 組合輸出
# ─────────────────────────────────────────
def main():
    print("=" * 50)
    print(f"CPBL 爬蟲啟動 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    standings = scrape_standings()
    schedule  = scrape_schedule()

    # 如果排名或賽程是空的，補假資料當 fallback（讓頁面不會空白）
    if not standings:
        print("\n⚠ 排名爬取失敗，使用 fallback 示範資料")
        standings = [
            {"rank":1,"team":"統一7-ELEVEn獅","w":0,"l":0,"pct":".000","gb":"-"},
            {"rank":2,"team":"中信兄弟",       "w":0,"l":0,"pct":".000","gb":"-"},
            {"rank":3,"team":"樂天桃猿",       "w":0,"l":0,"pct":".000","gb":"-"},
            {"rank":4,"team":"富邦悍將",       "w":0,"l":0,"pct":".000","gb":"-"},
            {"rank":5,"team":"台鋼雄鷹",       "w":0,"l":0,"pct":".000","gb":"-"},
            {"rank":6,"team":"味全龍",         "w":0,"l":0,"pct":".000","gb":"-"},
        ]

    if not schedule:
        print("⚠ 賽程爬取失敗，section 將顯示空")

    output = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "season": datetime.now().year,
        "standings": standings,
        "schedule": schedule,
    }

    with open("cpbl_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 完成！輸出至 cpbl_data.json")
    print(f"   排名：{len(standings)} 隊 ／ 賽程：{len(schedule)} 場")
    print("=" * 50)


if __name__ == "__main__":
    main()
