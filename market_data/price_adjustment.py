"""股票分割後的歷史 OHLCV 還原計算。"""
import pandas as pd


PRICE_COLUMNS = ("Open", "High", "Low", "Close")


def adjust_ohlcv_for_share_basis_changes(raw: pd.DataFrame, changes: pd.DataFrame) -> pd.DataFrame:
    """把事件日前價格統一成目前每股／每單位基準。

    分割後每單位價格下降，因此事件日前 OHLC 乘上 after_price / before_price；
    同一筆交易量代表的新單位數則反向除以該係數。成交金額不會因此改變。
    """
    adjusted = raw.copy()
    adjusted.index = pd.to_datetime(adjusted.index).tz_localize(None)
    missing = set(PRICE_COLUMNS).difference(adjusted.columns)
    if missing:
        raise ValueError(f"OHLC 資料缺少欄位：{', '.join(sorted(missing))}")
    if changes is None or changes.empty:
        adjusted.attrs["share_basis_adjustments"] = []
        return adjusted

    required = {"date", "basis_factor"}
    missing_changes = required.difference(changes.columns)
    if missing_changes:
        raise ValueError(f"公司行動資料缺少欄位：{', '.join(sorted(missing_changes))}")

    for change in changes.sort_values("date").itertuples(index=False):
        action_date = pd.Timestamp(change.date).tz_localize(None)
        factor = float(change.basis_factor)
        if factor <= 0:
            raise ValueError("公司行動的價格基準調整係數必須大於 0")
        mask = adjusted.index < action_date
        adjusted.loc[mask, list(PRICE_COLUMNS)] *= factor
        if "Volume" in adjusted.columns:
            adjusted.loc[mask, "Volume"] /= factor

    adjusted.attrs["share_basis_adjustments"] = changes.to_dict("records")
    return adjusted
