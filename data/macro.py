"""總經/警示指標：台幣匯率、費城半導體指數、外資期貨空單趨勢。

匯率跟費半是全球通用標的，yfinance 對這類非台股 OTC 的資料沒有出現過品質問題
（先前發現的落差只針對台股上櫃個股），所以這裡繼續用 yfinance，不用額外換 FinMind。

外資空單趨勢：使用者要的是「外資台指期未平倉淨額」（跟財經M平方 MacroMicro 那張圖
同一個概念，資料源就是 TAIFEX），不是市場整體融資融券——那是完全不同的東西，之前
用融券餘額當代理指標是不夠精準的權宜之計，這裡改成抓真正的外資期貨未平倉資料。
"""
from datetime import date, timedelta

import pandas as pd
import requests
import yfinance as yf
from bs4 import BeautifulSoup

TAIFEX_FUT_CONTRACTS_URL = "https://www.taifex.com.tw/cht/3/futContractsDate"


def fetch_twd_usd(period: str = "3mo") -> pd.DataFrame:
    df = yf.Ticker("TWD=X").history(period=period, auto_adjust=False)
    if df.empty:
        raise RuntimeError("抓不到台幣匯率資料")
    return df[["Close"]]


def fetch_sox(period: str = "3mo") -> pd.DataFrame:
    df = yf.Ticker("^SOX").history(period=period, auto_adjust=False)
    if df.empty:
        raise RuntimeError("抓不到費城半導體指數資料")
    return df[["Close"]]


def _fetch_foreign_tx_net_oi(query_date: date) -> float | None:
    """抓單一天的「外資台股期貨(TXF)未平倉多空淨額(口數)」。查無資料回傳 None。"""
    payload = {
        "queryType": "2",
        "goDay": "",
        "doQuery": "1",
        "dateaddcnt": "",
        "commodityId": "TXF",
        "queryDate": query_date.strftime("%Y/%m/%d"),
    }
    resp = requests.post(
        TAIFEX_FUT_CONTRACTS_URL, data=payload, headers={"User-Agent": "Mozilla/5.0"}, timeout=10
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    table = soup.find("table", class_="table_f")
    if table is None:
        return None
    for row in table.find("tbody").find_all("tr"):
        cells = [c.get_text(strip=True) for c in row.find_all("td")]
        if cells and cells[0] == "外資":
            # 欄位順序：外資, 多方口數,多方金額, 空方口數,空方金額, 多空淨額口數,多空淨額金額 (交易),
            #           多方口數,多方金額, 空方口數,空方金額, 多空淨額口數,多空淨額金額 (未平倉)
            # 未平倉多空淨額口數 = index 11
            raw = cells[11].replace(",", "")
            return float(raw)
    return None


def fetch_foreign_futures_position(lookback_trading_days: int = 20) -> pd.DataFrame:
    """外資台指期貨未平倉多空淨額，近 lookback_trading_days 個交易日。

    TAIFEX 這份資料一天一次查詢沒有區間查詢功能，所以要逐日往回查，
    交易日不多（近1個月約20天）還可接受，呼叫端記得加長效期的 cache。
    """
    records = []
    d = date.today()
    attempts = 0
    max_attempts = lookback_trading_days * 2 + 15  # 多留一些餘裕跳過假日/查無資料的日子

    while len(records) < lookback_trading_days and attempts < max_attempts:
        attempts += 1
        if d.weekday() < 5:  # 只跳過六日，未處理國定假日（已知限制）
            try:
                value = _fetch_foreign_tx_net_oi(d)
                if value is not None:
                    records.append((d, value))
            except Exception:
                pass
        d -= timedelta(days=1)

    if not records:
        raise RuntimeError("抓不到外資期貨未平倉資料")

    records.reverse()
    df = pd.DataFrame(records, columns=["date", "Close"]).set_index("date")
    return df


def value_and_change(df: pd.DataFrame) -> dict:
    """從一段 Close 序列算出目前值 + 變化率（跟序列第一筆比）。"""
    current = float(df["Close"].iloc[-1])
    first = float(df["Close"].iloc[0])
    change_pct = (current - first) / first * 100 if first else 0.0
    return {"current": current, "change_pct": change_pct}


if __name__ == "__main__":
    print("=== 台幣匯率（3個月）===")
    twd = fetch_twd_usd()
    print(value_and_change(twd))

    print("=== 費城半導體指數（3個月）===")
    sox = fetch_sox()
    print(value_and_change(sox))

    print("=== 外資台指期未平倉淨額（近20個交易日）===")
    fut = fetch_foreign_futures_position(lookback_trading_days=20)
    print(fut)
    print(value_and_change(fut))
