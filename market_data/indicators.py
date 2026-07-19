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


def add_bollinger_bands(df: pd.DataFrame, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    """布林通道：window 日均線 ± num_std 倍標準差。"""
    df = df.copy()
    mid = df["Close"].rolling(window=window).mean()
    std = df["Close"].rolling(window=window).std()
    df["BB_mid"] = mid
    df["BB_upper"] = mid + num_std * std
    df["BB_lower"] = mid - num_std * std
    return df


def find_swing_highs(df: pd.DataFrame, window: int = 10) -> list[tuple]:
    """找歷史上的區域高點（前後 window 天都沒有更高的收盤價，才算 swing high）。

    用 Close 而非 High，避免單日插針誤判；只在 window 天前後都有資料的範圍內找，
    最近 window 天內的高點還沒被「前後夾擊」驗證過，不列入（避免抓到還在噴的假高點）。
    """
    closes = df["Close"]
    swings = []
    for i in range(window, len(df) - window):
        segment = closes.iloc[i - window : i + window + 1]
        if closes.iloc[i] == segment.max():
            swings.append((df.index[i], float(closes.iloc[i])))
    return swings


def front_high_signal(df: pd.DataFrame, current_price: float, window: int = 10) -> dict | None:
    """前高支撐買點訊號：

    1. 找歷史 swing high（區域高點）
    2. 篩選「後續真的有收盤價站上去過」的 swing high（代表市場認證過這個價位）
    3. 在這些「已驗證」的高點中，找目前價格跌破的那些，回傳最近一個（最相關）

    回傳 None 代表目前沒有觸發訊號。
    """
    closes = df["Close"]
    swings = find_swing_highs(df, window=window)

    confirmed = []
    for swing_date, swing_price in swings:
        after = closes[closes.index > swing_date]
        if (after > swing_price).any():
            confirmed.append((swing_date, swing_price))

    # 只保留目前價格已經跌破的那些（= 買點候選），取最近一個
    triggered = [(d, p) for d, p in confirmed if current_price < p]
    if not triggered:
        return None

    swing_date, swing_price = triggered[-1]
    return {
        "swing_date": str(swing_date.date()) if hasattr(swing_date, "date") else str(swing_date),
        "front_high": swing_price,
        "current_price": current_price,
        "message": f"跌破前高 {swing_price:.1f} 了，可能是買點",
    }


if __name__ == "__main__":
    from config.watchlist import WATCHLIST
    from market_data.fetch import fetch_history, get_current_price

    for item in WATCHLIST:
        symbol, name = item["symbol"], item["name"]
        df = fetch_history(symbol)
        price = get_current_price(symbol, df)
        mas = latest_ma_values(df)
        ma_str = "  ".join(f"{k}={v:.2f}" if v is not None else f"{k}=N/A" for k, v in mas.items())
        print(f"{name}（{symbol}）現價 {price:.2f}｜{ma_str}")

        bb = add_bollinger_bands(df).iloc[-1]
        print(
            f"  布林通道: 下軌 {bb['BB_lower']:.2f}｜中線 {bb['BB_mid']:.2f}｜上軌 {bb['BB_upper']:.2f}"
        )

        signal = front_high_signal(df, price)
        print(f"  前高訊號: {signal['message'] if signal else '無（目前價格尚未跌破任何已驗證前高）'}")
        print()
