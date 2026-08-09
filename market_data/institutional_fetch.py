"""FinMind 個股籌碼面資料抓取（三大法人買賣超、融資融券、外資持股比率）。

籌碼面都是盤後 D-1 資料（證交所／櫃買收盤後才公告），沒有免費盤中版本——
見 AGENTS.md 的資料分層原則。三個資料集都經實測在 FinMind 免費會員層可取得。
"""
from datetime import date, timedelta

import pandas as pd

from market_data.fetch import _loader, symbol_to_finmind_id


def fetch_institutional_investors(symbol: str, lookback_days: int = 40) -> pd.DataFrame:
    """抓三大法人每日買賣超（原始格式：每個法人別各一列，buy/sell 單位為股）。"""
    stock_id = symbol_to_finmind_id(symbol)
    start = (date.today() - timedelta(days=lookback_days)).isoformat()
    end = date.today().isoformat()
    raw = _loader.taiwan_stock_institutional_investors(
        stock_id=stock_id, start_date=start, end_date=end
    )
    if raw is None or raw.empty:
        raise RuntimeError(f"抓不到 {symbol}（FinMind stock_id={stock_id}）的三大法人買賣超資料")
    return raw


def fetch_margin_short(symbol: str, lookback_days: int = 40) -> pd.DataFrame:
    """抓融資融券餘額（單位：張）。"""
    stock_id = symbol_to_finmind_id(symbol)
    start = (date.today() - timedelta(days=lookback_days)).isoformat()
    end = date.today().isoformat()
    raw = _loader.taiwan_stock_margin_purchase_short_sale(
        stock_id=stock_id, start_date=start, end_date=end
    )
    if raw is None or raw.empty:
        raise RuntimeError(f"抓不到 {symbol}（FinMind stock_id={stock_id}）的融資融券資料")
    return raw


def fetch_foreign_shareholding(symbol: str, lookback_days: int = 90) -> pd.DataFrame:
    """抓外資持股比率（ForeignInvestmentSharesRatio，單位：%）。"""
    stock_id = symbol_to_finmind_id(symbol)
    start = (date.today() - timedelta(days=lookback_days)).isoformat()
    end = date.today().isoformat()
    raw = _loader.taiwan_stock_shareholding(
        stock_id=stock_id, start_date=start, end_date=end
    )
    if raw is None or raw.empty:
        raise RuntimeError(f"抓不到 {symbol}（FinMind stock_id={stock_id}）的外資持股資料")
    return raw
