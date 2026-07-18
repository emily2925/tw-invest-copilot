"""股價歷史資料抓取（yfinance）。

已知限制：yfinance 對台股的報價通常有 15-20 分鐘延遲，不是逐秒即時。
這是為了快速做出 v1 的折衷，之後有需要再換成 TWSE MIS 即時行情 API。
"""
import pandas as pd
import yfinance as yf


def fetch_history(symbol: str, period: str = "1y") -> pd.DataFrame:
    """抓單一標的的歷史 OHLC。period 例如 '1y'、'6mo'、'3mo'。"""
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period)
    if df.empty:
        raise RuntimeError(f"抓不到 {symbol} 的歷史資料")
    return df


def latest_price(df: pd.DataFrame) -> float:
    """從歷史資料取最新一筆收盤價，當作目前價格的近似值。"""
    return float(df["Close"].iloc[-1])


if __name__ == "__main__":
    from config.watchlist import WATCHLIST

    for item in WATCHLIST:
        symbol, name = item["symbol"], item["name"]
        df = fetch_history(symbol, period="3mo")
        price = latest_price(df)
        print(f"{name}（{symbol}）目前價格: {price}")
