"""台指夜盤（台股期貨盤後交易時段）資料抓取。

資料源：TAIFEX 每日行情頁面 (https://www.taifex.com.tw/cht/3/futDailyMarketReport)
POST 表單參數：commodity_id=TX（台股期貨）, MarketCode=1（盤後交易時段）, queryDate=YYYY/MM/DD
免費、無需授權，D-1 style（查詢前一夜盤結算後的資料）。
"""
import re
from datetime import date

import requests
from bs4 import BeautifulSoup

TAIFEX_URL = "https://www.taifex.com.tw/cht/3/futDailyMarketReport"


def fetch_tx_night_session(query_date: date) -> dict:
    """抓指定日期的台股期貨（TX）夜盤近月合約行情。"""
    payload = {
        "queryType": "2",
        "marketCode": "1",
        "dateaddcnt": "",
        "commodity_id": "TX",
        "commodity_id2": "",
        "MarketCode": "1",
        "commodity_idt": "TX",
        "queryDate": query_date.strftime("%Y/%m/%d"),
    }
    resp = requests.post(
        TAIFEX_URL,
        data=payload,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=10,
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    table = soup.find("table", class_="table_f")
    if table is None:
        raise RuntimeError("找不到行情表格，TAIFEX 頁面結構可能變了")

    row = table.find("tbody").find("tr")  # 近月合約通常是第一列
    cells = [c.get_text(strip=True) for c in row.find_all("td")]

    # 欄位順序：契約, 到期月份, 開盤價, 最高價, 最低價, 最後成交價, 漲跌價, 漲跌%, 成交量, ...
    change_pct_raw = cells[7].replace("▲", "").replace("▼", "").replace("%", "")

    return {
        "date": payload["queryDate"],
        "contract": cells[0],
        "expiry": cells[1],
        "open": float(cells[2]),
        "high": float(cells[3]),
        "low": float(cells[4]),
        "close": float(cells[5]),
        "change": cells[6],
        "change_pct": float(change_pct_raw),
    }


def sentiment_tier(change_pct: float) -> str:
    """把漲跌%換算成簡單情緒分級。"""
    if change_pct >= 1.0:
        return "大漲"
    if change_pct >= 0.3:
        return "小漲"
    if change_pct <= -1.0:
        return "大跌"
    if change_pct <= -0.3:
        return "小跌"
    return "持平"


if __name__ == "__main__":
    # Demo：查最近一個交易日的夜盤資料
    from datetime import timedelta

    d = date.today()
    while True:
        try:
            data = fetch_tx_night_session(d)
            break
        except Exception as e:
            print(f"[{d}] 查無資料或錯誤：{e}，往前一天再試")
            d -= timedelta(days=1)

    print("=== 台指期夜盤（近月合約）===")
    for k, v in data.items():
        print(f"{k}: {v}")
    print(f"隔夜情緒分級: {sentiment_tier(data['change_pct'])}")
