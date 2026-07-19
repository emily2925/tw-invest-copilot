"""FinMind 季度 EPS 資料抓取。"""
from datetime import date, timedelta

import pandas as pd

from market_data.fetch import _loader, symbol_to_finmind_id


def fetch_quarterly_eps(symbol: str, lookback_years: int = 4) -> pd.DataFrame:
    """抓綜合損益表中的單季基本每股盈餘（EPS）。"""
    stock_id = symbol_to_finmind_id(symbol)
    start = (date.today() - timedelta(days=lookback_years * 366)).isoformat()
    end = date.today().isoformat()
    raw = _loader.taiwan_stock_financial_statement(
        stock_id=stock_id, start_date=start, end_date=end
    )
    eps = raw[raw["type"].eq("EPS")].copy()
    if eps.empty:
        raise RuntimeError(f"抓不到 {symbol}（FinMind stock_id={stock_id}）的 EPS 資料")

    eps["Date"] = pd.to_datetime(eps["date"], errors="coerce")
    eps["EPS"] = pd.to_numeric(eps["value"], errors="coerce")
    eps = eps.dropna(subset=["Date", "EPS"]).sort_values("Date").drop_duplicates("Date", keep="last")
    return eps.set_index("Date")[["EPS", "origin_name"]]
