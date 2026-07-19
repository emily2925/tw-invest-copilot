"""追蹤清單與產業分類。

代號規則沿用市場常見格式：上市股票／ETF 加 .TW、上櫃加 .TWO，
加權指數使用 ^TWII。新增標的時必須填入 category，主頁會依此產生產業篩選器。
"""

WATCHLIST = [
    {"symbol": "00685L.TW", "name": "群益臺灣加權正2", "category": "穩定股"},
    {"symbol": "2330.TW", "name": "台積電", "category": "穩定股"},
    {"symbol": "2327.TW", "name": "國巨", "category": "被動元件"},
    {"symbol": "3026.TW", "name": "禾伸堂", "category": "被動元件"},
    {"symbol": "8261.TWO", "name": "富鼎", "category": "功率元件"},
    {"symbol": "2481.TW", "name": "強茂", "category": "功率元件"},
    {"symbol": "6435.TWO", "name": "大中", "category": "功率元件"},
    {"symbol": "5425.TWO", "name": "台半", "category": "功率元件"},
    {"symbol": "5299.TWO", "name": "杰力", "category": "功率元件"},
    {"symbol": "3711.TW", "name": "日月光投控", "category": "封測"},
    {"symbol": "6257.TW", "name": "矽格", "category": "封測"},
    {"symbol": "6488.TWO", "name": "環球晶", "category": "矽晶圓"},
    {"symbol": "2408.TW", "name": "南亞科", "category": "記憶體"},
    {"symbol": "8046.TW", "name": "南電", "category": "載板"},
    {"symbol": "3189.TW", "name": "景碩", "category": "載板"},
]
