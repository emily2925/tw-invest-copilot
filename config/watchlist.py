"""追蹤清單。先寫死幾檔範例，之後可以直接編輯這個 list，或改成可在 UI 上編輯。

yfinance 代號規則：上市股票/ETF 加 .TW，上櫃加 .TWO，指數用 ^ 開頭。
"""

WATCHLIST = [
    {"symbol": "^TWII", "name": "加權指數"},
    {"symbol": "0050.TW", "name": "元大台灣50"},
    {"symbol": "2330.TW", "name": "台積電"},
    {"symbol": "6488.TWO", "name": "環球晶"},  # 上櫃股票用 .TWO，不是 .TW
]
