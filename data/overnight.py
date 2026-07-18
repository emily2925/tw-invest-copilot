"""台指夜盤（台股期貨盤後交易時段）資料抓取。

資料源：TAIFEX 每日行情頁面 (https://www.taifex.com.tw/cht/3/futDailyMarketReport)
POST 表單參數：commodity_id=TX（台股期貨）, MarketCode=1（盤後交易時段）, queryDate=YYYY/MM/DD

關鍵細節（TAIFEX 的日期歸屬慣例）：盤後交易時段從 T 日 15:00 開跑到 T+1 日 05:00，
但這整段資料是用「下一個交易日」的日期去查，不是用 T 當天的日期。
例如週五(7/17)晚上的夜盤，要查詢日期 = 下一個交易日 = 下週一(7/20)。
也就是說：要看「最近一次完整結束的夜盤」，只要往前找到下一個交易日（略過六日）直接查那天的日期即可，
不需要往回找。

已知限制（v1 先不處理，之後再補）：只略過週六日，沒有處理台灣的國定假日休市。
"""
from datetime import date, timedelta

import requests
from bs4 import BeautifulSoup

TAIFEX_URL = "https://www.taifex.com.tw/cht/3/futDailyMarketReport"


def next_trading_day(d: date) -> date:
    """回傳 d 當天或之後，最近的一個交易日（只略過六日，未處理國定假日）。"""
    while d.weekday() >= 5:  # 5=Sat, 6=Sun
        d += timedelta(days=1)
    return d


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

    # 表格會列出 TX 好幾個到期月份的合約（近月、次月...），
    # 明確挑「到期月份」數字最小（最近到期）的那一列，不要依賴表格排列順序。
    candidates = []
    for row in table.find("tbody").find_all("tr"):
        cells = [c.get_text(strip=True) for c in row.find_all("td")]
        if not cells or cells[0] != "TX":
            continue
        candidates.append(cells)

    if not candidates:
        raise RuntimeError(f"查無 TX 合約資料（查詢日期 {payload['queryDate']}）")

    cells = min(candidates, key=lambda c: c[1])  # cells[1] = 到期月份，如 "202608"

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


def get_overnight_sentiment() -> dict:
    """統一入口：回傳「最近一次已結束的夜盤」資料 + 情緒分級，給 dashboard 直接用。"""
    query_day = next_trading_day(date.today())
    data = fetch_tx_night_session(query_day)
    data["sentiment"] = sentiment_tier(data["change_pct"])
    return data


def fetch_overnight_trend(lookback_trading_days: int = 20):
    """近 lookback_trading_days 個交易日的夜盤收盤價序列，給趨勢圖用。

    TAIFEX 這份資料一天一次查詢，沒有區間查詢功能，逐日往回查。
    """
    import pandas as pd

    records = []
    d = next_trading_day(date.today())
    attempts = 0
    max_attempts = lookback_trading_days * 2 + 15

    while len(records) < lookback_trading_days and attempts < max_attempts:
        attempts += 1
        if d.weekday() < 5:
            try:
                data = fetch_tx_night_session(d)
                records.append((d, data["close"]))
            except Exception:
                pass
        d -= timedelta(days=1)

    if not records:
        raise RuntimeError("抓不到夜盤歷史資料")

    records.reverse()
    return pd.DataFrame(records, columns=["date", "Close"]).set_index("date")


if __name__ == "__main__":
    result = get_overnight_sentiment()
    print("=== 台指期夜盤（近月合約）===")
    for k, v in result.items():
        print(f"{k}: {v}")
