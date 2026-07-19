"""總經/警示指標：台幣匯率、費城半導體指數、外資期貨空單趨勢。

匯率跟費半是全球通用標的，yfinance 對這類非台股 OTC 的資料沒有出現過品質問題
（先前發現的落差只針對台股上櫃個股），所以這裡繼續用 yfinance，不用額外換 FinMind。

外資空單趨勢：使用者要的是「外資台指期未平倉淨額」（跟財經M平方 MacroMicro 那張圖
同一個概念，資料源就是 TAIFEX），不是市場整體融資融券——那是完全不同的東西，之前
用融券餘額當代理指標是不夠精準的權宜之計，這裡改成抓真正的外資期貨未平倉資料。
"""
import pandas as pd
import yfinance as yf

from market_data.foreign_futures import fetch_foreign_futures_position


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
