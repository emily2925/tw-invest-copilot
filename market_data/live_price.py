"""TWSE MIS 準即時報價（取代 yfinance 的「目前價格」，歷史序列仍用 yfinance）。

資料源：https://mis.twse.com.tw/stock/api/getStockInfo.jsp
同一個 endpoint 用 ex_ch 參數（tse_ 前綴=上市, otc_ 前綴=上櫃）同時查多檔，免登入。
加權指數的代碼是特例：t00（不是股票代號）。
"""
import requests

MIS_URL = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"


def symbol_to_mis_code(symbol: str) -> str:
    """把 yfinance 風格代號轉成 MIS API 的 ex_ch 代碼。"""
    if symbol == "^TWII":
        return "tse_t00.tw"
    if symbol.endswith(".TWO"):
        code = symbol[: -len(".TWO")]
        return f"otc_{code}.tw"
    if symbol.endswith(".TW"):
        code = symbol[: -len(".TW")]
        return f"tse_{code}.tw"
    raise ValueError(f"不認得的代號格式: {symbol}")


def fetch_live_prices(symbols: list[str]) -> dict[str, float | None]:
    """回傳 {symbol: 目前價格}，查不到的給 None（呼叫端應 fallback 回歷史收盤價）。"""
    mis_codes = [symbol_to_mis_code(s) for s in symbols]
    code_to_symbol = dict(zip(mis_codes, symbols))

    resp = requests.get(
        MIS_URL,
        params={"ex_ch": "|".join(mis_codes), "json": "1", "delay": "0"},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    result = {s: None for s in symbols}
    for item in data.get("msgArray", []):
        mis_code = f"{item['ex']}_{item['ch']}"
        symbol = code_to_symbol.get(mis_code)
        if symbol is None:
            continue
        z = item.get("z", "-")
        result[symbol] = float(z) if z not in ("-", "", None) else None
    return result


if __name__ == "__main__":
    from config.watchlist import WATCHLIST

    symbols = [item["symbol"] for item in WATCHLIST]
    prices = fetch_live_prices(symbols)
    for item in WATCHLIST:
        symbol, name = item["symbol"], item["name"]
        print(f"{name}（{symbol}）即時價: {prices[symbol]}")
