"""個股籌碼面的決定性計算（三大法人買賣超、融資融券、外資持股比率）。

抓取在 institutional_fetch.py，這裡只做純計算（pivot、淨額、連續買賣超天數、趨勢），
方便單元測試不必連網。買賣超一律換算成「張」（1 張 = 1000 股）符合台股散戶習慣。
"""
import pandas as pd

SHARES_PER_LOT = 1000


def is_institutional_applicable(symbol: str) -> bool:
    """指數（^ 開頭）沒有個股籌碼；個股與 ETF 都有三大法人／融資融券資料。"""
    return not symbol.startswith("^")


def _streak(net_values: list[float]) -> dict:
    """從最新一筆往回算連續同方向（買超>0／賣超<0）的天數。"""
    if not net_values:
        return {"days": 0, "direction": None}
    last = net_values[-1]
    if last == 0:
        return {"days": 0, "direction": None}
    direction = "buy" if last > 0 else "sell"
    days = 0
    for v in reversed(net_values):
        if (v > 0 and direction == "buy") or (v < 0 and direction == "sell"):
            days += 1
        else:
            break
    return {"days": days, "direction": direction}


def prepare_institutional_net(raw: pd.DataFrame, display_days: int = 20) -> dict:
    """把三大法人原始資料（每法人別一列）pivot 成每日外資／投信／自營淨買賣超（張）。"""
    required = {"date", "name", "buy", "sell"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"三大法人資料缺少欄位：{', '.join(sorted(missing))}")

    df = raw.copy()
    df["buy"] = pd.to_numeric(df["buy"], errors="coerce").fillna(0)
    df["sell"] = pd.to_numeric(df["sell"], errors="coerce").fillna(0)
    df["net_lots"] = (df["buy"] - df["sell"]) / SHARES_PER_LOT

    def group_of(name: str) -> str | None:
        if name.startswith("Foreign"):
            return "foreign"
        if name == "Investment_Trust":
            return "trust"
        if name.startswith("Dealer"):
            return "dealer"
        return None

    df["group"] = df["name"].map(group_of)
    df = df.dropna(subset=["group"])
    df["period"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["period"])

    pivot = (
        df.pivot_table(index="period", columns="group", values="net_lots", aggfunc="sum")
        .sort_index()
    )
    for col in ("foreign", "trust", "dealer"):
        if col not in pivot.columns:
            pivot[col] = 0.0
    pivot = pivot[["foreign", "trust", "dealer"]].fillna(0.0)
    if pivot.empty:
        raise ValueError("三大法人資料不足")

    foreign_vals = pivot["foreign"].tolist()
    latest = pivot.iloc[-1]
    return {
        "data": pivot.tail(display_days),
        "latest_date": pivot.index[-1],
        "foreign_net": float(latest["foreign"]),
        "trust_net": float(latest["trust"]),
        "dealer_net": float(latest["dealer"]),
        "foreign_streak": _streak(foreign_vals),
        "foreign_cum_5d": float(pivot["foreign"].tail(5).sum()),
        "foreign_cum_20d": float(pivot["foreign"].tail(20).sum()),
        "observations": len(pivot),
    }


def prepare_margin_short(raw: pd.DataFrame, display_days: int = 20) -> dict:
    """融資／融券餘額（張）趨勢，並算最新一日相對前一日的變化。"""
    required = {"date", "MarginPurchaseTodayBalance", "ShortSaleTodayBalance"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"融資融券資料缺少欄位：{', '.join(sorted(missing))}")

    df = raw.copy()
    df["period"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["period"]).sort_values("period").set_index("period")
    df["margin_balance"] = pd.to_numeric(df["MarginPurchaseTodayBalance"], errors="coerce")
    df["short_balance"] = pd.to_numeric(df["ShortSaleTodayBalance"], errors="coerce")
    df = df.dropna(subset=["margin_balance", "short_balance"])
    if df.empty:
        raise ValueError("融資融券資料不足")

    out = df[["margin_balance", "short_balance"]]
    latest = out.iloc[-1]
    margin_chg = short_chg = None
    if len(out) >= 2:
        prev = out.iloc[-2]
        margin_chg = float(latest["margin_balance"] - prev["margin_balance"])
        short_chg = float(latest["short_balance"] - prev["short_balance"])
    return {
        "data": out.tail(display_days),
        "latest_date": out.index[-1],
        "margin_balance": float(latest["margin_balance"]),
        "short_balance": float(latest["short_balance"]),
        "margin_change": margin_chg,
        "short_change": short_chg,
        "observations": len(out),
    }


def prepare_foreign_shareholding(raw: pd.DataFrame, display_days: int = 60) -> dict:
    """外資持股比率（%）趨勢，並算視窗內的變化幅度。"""
    if "date" not in raw.columns or "ForeignInvestmentSharesRatio" not in raw.columns:
        raise ValueError("外資持股資料缺少 date 或 ForeignInvestmentSharesRatio 欄位")

    df = raw.copy()
    df["period"] = pd.to_datetime(df["date"], errors="coerce")
    df["foreign_ratio"] = pd.to_numeric(df["ForeignInvestmentSharesRatio"], errors="coerce")
    df = df.dropna(subset=["period", "foreign_ratio"]).sort_values("period").set_index("period")
    if df.empty:
        raise ValueError("外資持股資料不足")

    out = df[["foreign_ratio"]].tail(display_days)
    change = None
    if len(out) >= 2:
        change = float(out["foreign_ratio"].iloc[-1] - out["foreign_ratio"].iloc[0])
    return {
        "data": out,
        "latest_date": out.index[-1],
        "foreign_ratio": float(out["foreign_ratio"].iloc[-1]),
        "ratio_change": change,
        "observations": len(out),
    }
