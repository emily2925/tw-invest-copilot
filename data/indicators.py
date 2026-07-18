"""技術指標計算：均線、布林通道、前高偵測。"""
import pandas as pd

MA_WINDOWS = [5, 10, 20, 60]


def add_moving_averages(df: pd.DataFrame, windows: list[int] = MA_WINDOWS) -> pd.DataFrame:
    """在 df 上加上 MA{window} 欄位，回傳新的 DataFrame（不修改原本的）。"""
    df = df.copy()
    for w in windows:
        df[f"MA{w}"] = df["Close"].rolling(window=w).mean()
    return df


def latest_ma_values(df: pd.DataFrame, windows: list[int] = MA_WINDOWS) -> dict:
    """取最新一筆的均線數值。"""
    df = add_moving_averages(df, windows)
    latest = df.iloc[-1]
    return {f"MA{w}": (None if pd.isna(latest[f"MA{w}"]) else float(latest[f"MA{w}"])) for w in windows}


if __name__ == "__main__":
    from config.watchlist import WATCHLIST
    from data.fetch import fetch_history, latest_price

    for item in WATCHLIST:
        symbol, name = item["symbol"], item["name"]
        df = fetch_history(symbol, period="6mo")
        price = latest_price(df)
        mas = latest_ma_values(df)
        ma_str = "  ".join(f"{k}={v:.2f}" if v is not None else f"{k}=N/A" for k, v in mas.items())
        print(f"{name}（{symbol}）現價 {price:.2f}｜{ma_str}")
