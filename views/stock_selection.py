"""首頁多選標的的純資料處理，與 Streamlit 畫面分離以便測試。"""


def selected_symbols_from_rows(items: list[dict], selected_rows: list[int]) -> list[str]:
    """依表格勾選列回傳不重複的股票代號，忽略失效索引。"""
    symbols = []
    for row in selected_rows:
        if not isinstance(row, int) or row < 0 or row >= len(items):
            continue
        symbol = items[row]["symbol"]
        if symbol not in symbols:
            symbols.append(symbol)
    return symbols


def watchlist_items_to_load(
    filtered_watchlist: list[dict],
    full_watchlist: list[dict],
    confirmed_symbols: list[str],
) -> list[dict]:
    """載入目前候選清單，再補上已送出的標的，讓換 filter 前的詳情不會立刻消失。"""
    items = list(filtered_watchlist)
    loaded_symbols = {item["symbol"] for item in items}
    by_symbol = {item["symbol"]: item for item in full_watchlist}
    for symbol in confirmed_symbols:
        if symbol in by_symbol and symbol not in loaded_symbols:
            items.append(by_symbol[symbol])
            loaded_symbols.add(symbol)
    return items
