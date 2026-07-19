"""股價歷史資料抓取。

原本用 yfinance，但發現對台股「上櫃」股票（例如環球晶 6488）的歷史收盤價
在 20-60 天這個範圍內跟 Fubon/Yahoo奇摩股市 兩個獨立來源對不起來（差距約 0.5-1%），
換成 FinMind（台灣在地的開源金融資料 API，上市櫃資料都涵蓋，經驗證跟權威來源完全吻合）。
"""
import os
from datetime import date, timedelta

import pandas as pd
from dotenv import load_dotenv
from FinMind.data import DataLoader

load_dotenv()

_loader = DataLoader()
_token = os.environ.get("FINMIND_API_TOKEN")
if _token:
    _loader.login_by_token(api_token=_token)


def symbol_to_finmind_id(symbol: str) -> str:
    """把 yfinance 風格代號轉成 FinMind 的 stock_id。"""
    if symbol == "^TWII":
        return "TAIEX"
    if symbol.endswith(".TWO"):
        return symbol[: -len(".TWO")]
    if symbol.endswith(".TW"):
        return symbol[: -len(".TW")]
    raise ValueError(f"不認得的代號格式: {symbol}")


def fetch_history(symbol: str, lookback_days: int = 400) -> pd.DataFrame:
    """抓單一標的的歷史 OHLC（原始成交價）。lookback_days 抓夠均線/前高偵測要用的天數。"""
    stock_id = symbol_to_finmind_id(symbol)
    start = (date.today() - timedelta(days=lookback_days)).isoformat()
    end = date.today().isoformat()

    raw = _loader.taiwan_stock_daily(stock_id=stock_id, start_date=start, end_date=end)
    if raw.empty:
        raise RuntimeError(f"抓不到 {symbol}（FinMind stock_id={stock_id}）的歷史資料")

    df = raw.rename(
        columns={"open": "Open", "max": "High", "min": "Low", "close": "Close", "Trading_Volume": "Volume"}
    )
    df["Date"] = pd.to_datetime(df["date"])
    df = df.set_index("Date").sort_index()
    return df[["Open", "High", "Low", "Close", "Volume"]]


def latest_price(df: pd.DataFrame) -> float:
    """從歷史資料取最新一筆收盤價，當作目前價格的近似值（fallback 用）。"""
    return float(df["Close"].iloc[-1])


def get_current_price(symbol: str, df: pd.DataFrame) -> float:
    """目前價格：優先用 TWSE MIS 準即時報價，查不到才 fallback 回歷史收盤價。"""
    from data.live_price import fetch_live_prices

    try:
        live = fetch_live_prices([symbol]).get(symbol)
        if live is not None:
            return live
    except Exception:
        pass
    return latest_price(df)


if __name__ == "__main__":
    from config.watchlist import WATCHLIST

    for item in WATCHLIST:
        symbol, name = item["symbol"], item["name"]
        df = fetch_history(symbol)
        price = get_current_price(symbol, df)
        print(f"{name}（{symbol}）目前價格: {price}")
