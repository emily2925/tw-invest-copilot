"""個股估值資料處理：本益比河流圖的適用性與決定性計算。"""
import pandas as pd

PE_PERCENTILES = (20, 40, 60, 80)


def is_pe_river_applicable(symbol: str) -> bool:
    """加權指數與 00 開頭 ETF 不套用個股 EPS／PE 模型。"""
    code = symbol.split(".")[0]
    return not symbol.startswith("^") and not code.startswith("00")


def build_pe_river(
    price_df: pd.DataFrame,
    pe_df: pd.DataFrame,
    min_observations: int = 252,
    min_positive_pe_coverage: float = 0.8,
) -> dict:
    """以個股自身歷史 PE 分位數建立估值河流。

    每日近四季 EPS 由 Close / PER 反推，再乘上全期間 PE 分位數形成估值帶。
    僅保留正本益比；資料量或正 PE 覆蓋率不足時拒絕產圖，避免誤導。
    """
    prices = price_df[["Close"]].copy()
    prices.index = pd.to_datetime(prices.index).tz_localize(None)
    prices["Close"] = pd.to_numeric(prices["Close"], errors="coerce")

    per = pe_df[["PER"]].copy()
    per.index = pd.to_datetime(per.index).tz_localize(None)
    per["PER"] = pd.to_numeric(per["PER"], errors="coerce")

    joined = prices.join(per, how="left")
    price_observations = int(joined["Close"].notna().sum())
    valid = joined[(joined["Close"] > 0) & (joined["PER"] > 0)].dropna().copy()
    coverage = len(valid) / price_observations if price_observations else 0.0

    if len(valid) < min_observations:
        raise ValueError(f"正本益比資料只有 {len(valid)} 筆，至少需要 {min_observations} 筆")
    if coverage < min_positive_pe_coverage:
        raise ValueError(
            f"正本益比覆蓋率 {coverage:.0%}，低於門檻 {min_positive_pe_coverage:.0%}，不適合畫河流圖"
        )

    valid["EPS_TTM"] = valid["Close"] / valid["PER"]
    percentiles = {p: float(valid["PER"].quantile(p / 100)) for p in PE_PERCENTILES}
    for percentile, multiple in percentiles.items():
        valid[f"PE_P{percentile}"] = valid["EPS_TTM"] * multiple

    return {
        "data": valid,
        "percentiles": percentiles,
        "current_pe": float(valid["PER"].iloc[-1]),
        "current_percentile": float((valid["PER"] <= valid["PER"].iloc[-1]).mean() * 100),
        "latest_date": valid.index[-1],
        "coverage": coverage,
        "observations": len(valid),
        "basis_adjustments": price_df.attrs.get("share_basis_adjustments", []),
    }
