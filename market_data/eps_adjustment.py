"""把歷史 EPS 統一到最新股數基準，避免股票分割扭曲成長率。"""
import pandas as pd

from market_data.earnings import prepare_eps_summary


def adjust_eps_for_share_basis_changes(raw: pd.DataFrame, changes: pd.DataFrame) -> pd.DataFrame:
    """依公司行動追溯調整事件日前的 EPS。

    每次分割都只影響事件日前的財報季度；若期間內發生多次分割，舊季度會依序累乘。
    這與 IAS 33 對股票分割／反分割須追溯調整所有表達期間 EPS 的原則一致。
    """
    adjusted = raw.copy()
    if "EPS" not in adjusted.columns:
        raise ValueError("EPS 資料缺少 EPS 欄位")
    adjusted.index = pd.to_datetime(adjusted.index).tz_localize(None)
    adjusted["EPS"] = pd.to_numeric(adjusted["EPS"], errors="coerce")
    if changes is None or changes.empty:
        return adjusted

    required = {"date", "basis_factor"}
    missing = required.difference(changes.columns)
    if missing:
        raise ValueError(f"公司行動資料缺少欄位：{', '.join(sorted(missing))}")

    for change in changes.sort_values("date").itertuples(index=False):
        action_date = pd.Timestamp(change.date).tz_localize(None)
        factor = float(change.basis_factor)
        if factor <= 0:
            raise ValueError("公司行動的 EPS 基準調整係數必須大於 0")
        adjusted.loc[adjusted.index < action_date, "EPS"] *= factor
    return adjusted


def prepare_split_adjusted_eps_summary(raw: pd.DataFrame, changes: pd.DataFrame) -> dict:
    """先統一每股基準，再計算單季 EPS、TTM 與同季 YoY。"""
    adjusted = adjust_eps_for_share_basis_changes(raw, changes)
    result = prepare_eps_summary(adjusted)
    result["basis_adjustments"] = [] if changes is None else changes.to_dict("records")
    return result
