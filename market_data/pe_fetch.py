"""FinMind 個股估值資料抓取。與純計算 valuation.py 分離，避免測試時連網。"""
from datetime import date, timedelta

import pandas as pd

from market_data.fetch import _loader, symbol_to_finmind_id


def fetch_pe_history(symbol: str, lookback_days: int = 1900) -> pd.DataFrame:
    """抓個股逐日本益比／股價淨值比／殖利率，資料源為 FinMind TaiwanStockPER。"""
    stock_id = symbol_to_finmind_id(symbol)
    start = (date.today() - timedelta(days=lookback_days)).isoformat()
    end = date.today().isoformat()

    raw = _loader.taiwan_stock_per_pbr(stock_id=stock_id, start_date=start, end_date=end)
    if raw.empty:
        raise RuntimeError(f"抓不到 {symbol}（FinMind stock_id={stock_id}）的本益比資料")

    df = raw.copy()
    df["Date"] = pd.to_datetime(df["date"])
    for column in ("PER", "PBR", "dividend_yield"):
        df[column] = pd.to_numeric(df[column], errors="coerce")
    return df.set_index("Date").sort_index()[["PER", "PBR", "dividend_yield"]]
