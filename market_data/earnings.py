"""實際 EPS 的決定性整理與成長率計算。"""
import pandas as pd


def prepare_eps_summary(raw: pd.DataFrame) -> dict:
    """整理最近單季、近四季 EPS 與同季 YoY。

    FinMind TaiwanStockFinancialStatements 的 EPS 列為單季值，TTM 因此加總最近四季。
    本函式只處理已公告實際值，不混入任何市場預估。
    """
    if "EPS" not in raw.columns:
        raise ValueError("EPS 資料缺少 EPS 欄位")
    df = raw[["EPS"]].copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df["EPS"] = pd.to_numeric(df["EPS"], errors="coerce")
    df = df.dropna().sort_index()
    df = df[~df.index.duplicated(keep="last")]
    if len(df) < 4:
        raise ValueError(f"EPS 資料只有 {len(df)} 季，至少需要 4 季才能計算 TTM")

    latest_date = df.index[-1]
    latest_eps = float(df["EPS"].iloc[-1])
    ttm_eps = float(df["EPS"].tail(4).sum())
    same_quarter_last_year = latest_date - pd.DateOffset(years=1)
    previous_eps = df["EPS"].get(same_quarter_last_year)
    quarterly_yoy = None
    if previous_eps is not None and pd.notna(previous_eps) and previous_eps != 0:
        quarterly_yoy = float((latest_eps / float(previous_eps) - 1) * 100)

    return {
        "data": df,
        "latest_date": latest_date,
        "latest_eps": latest_eps,
        "ttm_eps": ttm_eps,
        "quarterly_yoy_pct": quarterly_yoy,
        "quarters": len(df),
    }
