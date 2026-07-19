"""月營收等基本面資料的決定性計算。"""
import pandas as pd


def is_company_fundamentals_applicable(symbol: str) -> bool:
    """指數與 00 開頭 ETF 不套用個別公司的月營收／EPS 模型。"""
    code = symbol.split(".")[0]
    return not symbol.startswith("^") and not code.startswith("00")


def prepare_revenue_trend(raw: pd.DataFrame, display_months: int = 12) -> dict:
    """依實際營收年月排序，計算 MoM、YoY，並回傳最近 display_months 個月。"""
    df = raw.copy()
    required = {"revenue", "revenue_year", "revenue_month"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"月營收資料缺少欄位：{', '.join(sorted(missing))}")

    df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce")
    df["revenue_year"] = pd.to_numeric(df["revenue_year"], errors="coerce")
    df["revenue_month"] = pd.to_numeric(df["revenue_month"], errors="coerce")
    df = df.dropna(subset=["revenue", "revenue_year", "revenue_month"])
    df["period"] = pd.to_datetime(
        {
            "year": df["revenue_year"].astype(int),
            "month": df["revenue_month"].astype(int),
            "day": 1,
        }
    )
    df = df.sort_values("period").drop_duplicates("period", keep="last").set_index("period")
    if len(df) < 2:
        raise ValueError("月營收資料不足，至少需要 2 個月")

    df["revenue_100m"] = df["revenue"] / 100_000_000
    df["mom_pct"] = df["revenue"].pct_change() * 100
    df["yoy_pct"] = df["revenue"].pct_change(12) * 100
    latest = df.iloc[-1]
    announcement_date = latest.get("announcement_date")
    if pd.isna(announcement_date):
        announcement_date = latest.get("record_date")

    return {
        "data": df.tail(display_months),
        "latest_period": df.index[-1],
        "latest_revenue": float(latest["revenue"]),
        "latest_revenue_100m": float(latest["revenue_100m"]),
        "mom_pct": None if pd.isna(latest["mom_pct"]) else float(latest["mom_pct"]),
        "yoy_pct": None if pd.isna(latest["yoy_pct"]) else float(latest["yoy_pct"]),
        "announcement_date": announcement_date,
        "observations": len(df),
    }
