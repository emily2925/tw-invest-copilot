"""FinMind 股票分割／反分割／面額變更資料抓取。"""
from datetime import date, timedelta

import pandas as pd

from market_data.fetch import _loader, symbol_to_finmind_id


SHARE_BASIS_CHANGE_TYPES = {"分割", "反分割", "面額變更"}


def fetch_share_basis_changes(symbol: str, lookback_years: int = 5) -> pd.DataFrame:
    """抓會改變每股基準的公司行動，並算出歷史 EPS 應乘的調整係數。

    FinMind 的 TaiwanStockSplitPrice 沒有直接提供拆分股數比例，但生效前價格與
    生效後參考價的比率，正是每股數字需追溯套用的基準係數。例如國巨 546 →
    136.5，歷史 EPS 應乘 136.5 / 546 = 0.25。
    """
    stock_id = symbol_to_finmind_id(symbol)
    start = (date.today() - timedelta(days=lookback_years * 366)).isoformat()
    end = date.today().isoformat()
    raw = _loader.taiwan_stock_split_price(start_date=start, end_date=end)
    columns = ["date", "stock_id", "type", "before_price", "after_price", "basis_factor"]
    if raw.empty:
        return pd.DataFrame(columns=columns)

    changes = raw[
        raw["stock_id"].astype(str).eq(stock_id)
        & raw["type"].astype(str).isin(SHARE_BASIS_CHANGE_TYPES)
    ].copy()
    if changes.empty:
        return pd.DataFrame(columns=columns)

    changes["date"] = pd.to_datetime(changes["date"], errors="coerce").dt.tz_localize(None)
    changes["before_price"] = pd.to_numeric(changes["before_price"], errors="coerce")
    changes["after_price"] = pd.to_numeric(changes["after_price"], errors="coerce")
    changes = changes.dropna(subset=["date", "before_price", "after_price"])
    changes = changes[(changes["before_price"] > 0) & (changes["after_price"] > 0)]
    changes["basis_factor"] = changes["after_price"] / changes["before_price"]
    return changes[columns].sort_values("date").reset_index(drop=True)
