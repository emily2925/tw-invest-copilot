"""追蹤清單與產業分類。

代號規則沿用市場常見格式：上市股票／ETF 加 .TW、上櫃加 .TWO，
加權指數使用 ^TWII。新增標的時必須填入 category，主頁會依此產生產業篩選器。
"""

WATCHLIST = [
    {"symbol": "^TWII", "name": "加權指數", "category": "大盤指數"},
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
    {"symbol": "3037.TW", "name": "欣興", "category": "載板"},
    {"symbol": "2368.TW", "name": "金像電", "category": "載板"},
    {"symbol": "6213.TW", "name": "聯茂", "category": "CCL"},
    {"symbol": "8358.TWO", "name": "金居", "category": "CCL"},
    {"symbol": "2383.TW", "name": "台光電", "category": "CCL"},
    {"symbol": "3081.TWO", "name": "聯亞", "category": "光通"},
    {"symbol": "6669.TW", "name": "緯穎", "category": "光通"},
    {"symbol": "3363.TW", "name": "上詮", "category": "光通"},
    {"symbol": "6442.TW", "name": "光聖", "category": "光通"},
    {"symbol": "3163.TWO", "name": "波若威", "category": "光通"},
    {"symbol": "3653.TW", "name": "健策", "category": "散熱"},
    {"symbol": "3017.TW", "name": "奇鋐", "category": "散熱"},
    {"symbol": "1727.TW", "name": "中華化", "category": "散熱"},
    {"symbol": "3324.TW", "name": "雙鴻", "category": "散熱"},
    {"symbol": "2308.TW", "name": "台達電", "category": "散熱"},
    {"symbol": "3443.TW", "name": "創意", "category": "IC設計"},
    {"symbol": "2454.TW", "name": "聯發科", "category": "IC設計"},
    {"symbol": "3661.TW", "name": "世芯-KY", "category": "IC設計"},
    {"symbol": "2379.TW", "name": "瑞昱", "category": "IC設計"},
]
