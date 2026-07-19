"""FinMind 股票分割／反分割／面額變更資料抓取。"""
from datetime import date, timedelta
from functools import lru_cache

import pandas as pd

from market_data.fetch import _loader, symbol_to_finmind_id


SHARE_BASIS_CHANGE_TYPES = {"分割", "反分割", "面額變更"}


@lru_cache(maxsize=1)
def _fetch_all_share_basis_changes() -> pd.DataFrame:
    """公司行動筆數很少，一個程序只抓一次全市場資料供所有標的共用。"""
    raw = _loader.taiwan_stock_split_price(start_date="2010-01-01", end_date=date.today().isoformat())
    if raw.empty:
        return raw
    result = raw.copy()
    result["date"] = pd.to_datetime(result["date"], errors="coerce").dt.tz_localize(None)
    result["before_price"] = pd.to_numeric(result["before_price"], errors="coerce")
    result["after_price"] = pd.to_numeric(result["after_price"], errors="coerce")
    result = result[
        result["type"].astype(str).isin(SHARE_BASIS_CHANGE_TYPES)
        & result["date"].notna()
        & result["before_price"].gt(0)
        & result["after_price"].gt(0)
    ].copy()
    result["basis_factor"] = result["after_price"] / result["before_price"]
    return result


def fetch_share_basis_changes(symbol: str, lookback_years: int = 5) -> pd.DataFrame:
    """抓會改變每股基準的公司行動，並算出歷史 EPS 應乘的調整係數。

    FinMind 的 TaiwanStockSplitPrice 沒有直接提供拆分股數比例，但生效前價格與
    生效後參考價的比率，正是每股數字需追溯套用的基準係數。例如國巨 546 →
    136.5，歷史 EPS 應乘 136.5 / 546 = 0.25。
    """
    stock_id = symbol_to_finmind_id(symbol)
    start = pd.Timestamp(date.today() - timedelta(days=lookback_years * 366))
    raw = _fetch_all_share_basis_changes()
    columns = ["date", "stock_id", "type", "before_price", "after_price", "basis_factor"]
    if raw.empty:
        return pd.DataFrame(columns=columns)

    changes = raw[
        raw["stock_id"].astype(str).eq(stock_id)
        & raw["date"].ge(start)
    ].copy()
    if changes.empty:
        return pd.DataFrame(columns=columns)

    return changes[columns].sort_values("date").reset_index(drop=True)
