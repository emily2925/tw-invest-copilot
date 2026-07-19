"""FinMind 個股基本面資料抓取。"""
from datetime import date, timedelta

import pandas as pd

from market_data.fetch import _loader, symbol_to_finmind_id


def fetch_monthly_revenue(symbol: str, lookback_months: int = 30) -> pd.DataFrame:
    """抓個股月營收，保留實際營收年月與資料建立時間。"""
    stock_id = symbol_to_finmind_id(symbol)
    start = (date.today() - timedelta(days=lookback_months * 31)).isoformat()
    end = date.today().isoformat()
    raw = _loader.taiwan_stock_month_revenue(stock_id=stock_id, start_date=start, end_date=end)
    if raw.empty:
        raise RuntimeError(f"抓不到 {symbol}（FinMind stock_id={stock_id}）的月營收資料")

    df = raw.copy()
    df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce")
    df["revenue_year"] = pd.to_numeric(df["revenue_year"], errors="coerce")
    df["revenue_month"] = pd.to_numeric(df["revenue_month"], errors="coerce")
    df["announcement_date"] = pd.to_datetime(df["create_time"], errors="coerce")
    df["record_date"] = pd.to_datetime(df["date"], errors="coerce")
    return df[
        ["stock_id", "revenue", "revenue_year", "revenue_month", "announcement_date", "record_date"]
    ]
