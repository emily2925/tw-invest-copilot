"""總經/警示指標：台幣匯率、費城半導體指數、外資空單趨勢。

匯率跟費半是全球通用標的，yfinance 對這類非台股 OTC 的資料沒有出現過品質問題
（先前發現的落差只針對台股上櫃個股），所以這裡繼續用 yfinance，不用額外換 FinMind。
外資空單趨勢用 FinMind 的整體市場融券餘額（ShortSale）當代理指標——注意這是
「整體市場融券」，不是「外資專屬」的空單部位，免費資料能拿到的最接近版本。
"""
from datetime import date, timedelta

import pandas as pd
import yfinance as yf
from FinMind.data import DataLoader

_loader = DataLoader()


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


def fetch_foreign_short_trend(lookback_days: int = 60) -> pd.DataFrame:
    """整體市場融券餘額趨勢（外資空單的代理指標），近 lookback_days 天。"""
    start = (date.today() - timedelta(days=lookback_days)).isoformat()
    end = date.today().isoformat()
    raw = _loader.taiwan_stock_margin_purchase_short_sale_total(start_date=start, end_date=end)
    if raw.empty:
        raise RuntimeError("抓不到融券餘額資料")
    short_df = raw[raw["name"] == "ShortSale"].copy()
    short_df["date"] = pd.to_datetime(short_df["date"])
    short_df = short_df.sort_values("date").set_index("date")
    return short_df.rename(columns={"TodayBalance": "Close"})[["Close"]]


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

    print("=== 外資空單趨勢（1個月）===")
    short = fetch_foreign_short_trend(lookback_days=30)
    print(value_and_change(short))
