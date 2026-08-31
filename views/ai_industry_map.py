"""AI 基礎建設產業地圖雛形。"""

from __future__ import annotations

from html import escape
from textwrap import dedent

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# 雛形先依使用者 2026-08-26 截圖中「當日漲幅最高的兩檔」選代表股。
SECTORS = [
    {
        "name": "光通訊／AI伺服器",
        "short": "光通訊／伺服器",
        "role": "傳資料、組裝整座 AI 機櫃",
        "leaders": [
            {"symbol": "3081.TWO", "name": "聯亞"},
            {"symbol": "6669.TW", "name": "緯穎"},
        ],
    },
    {
        "name": "CCL／高速電路板材料",
        "short": "CCL",
        "role": "做出承載晶片與高速線路的電路板底材",
        "leaders": [
            {"symbol": "6213.TW", "name": "聯茂"},
            {"symbol": "8358.TWO", "name": "金居"},
        ],
    },
    {
        "name": "IC設計／ASIC",
        "short": "IC設計",
        "role": "設計 AI、網路與客製化晶片",
        "leaders": [
            {"symbol": "3443.TW", "name": "創意"},
            {"symbol": "2454.TW", "name": "聯發科"},
        ],
    },
    {
        "name": "散熱／廠務",
        "short": "散熱／廠務",
        "role": "用冷板、水管與機房工程把熱帶走",
        "leaders": [
            {"symbol": "3653.TW", "name": "健策"},
            {"symbol": "3017.TW", "name": "奇鋐"},
        ],
    },
]

PERIODS = {"1個月": 21, "3個月": 63, "6個月": 126, "12個月": 252}


@st.cache_data(ttl=21600, show_spinner=False)
def _load_map_history(symbol: str) -> pd.DataFrame:
    """地圖只需收盤價；六小時快取避免切換期間時重抓。"""
    from market_data.fetch import fetch_history

    return fetch_history(symbol, lookback_days=450)


@st.cache_data(ttl=300, show_spinner=False)
def _load_live_prices(symbols: tuple[str, ...]) -> dict[str, float]:
    """代表股一次批次查詢盤中價格，失敗時由呼叫端退回最新收盤價。"""
    from market_data.live_price import fetch_live_prices

    try:
        return fetch_live_prices(list(symbols))
    except Exception:
        return {}


def calculate_period_returns(close: pd.Series) -> dict[str, float | None]:
    """以交易日近似 1／3／6／12 個月，計算分割基準還原後的價格報酬。"""
    valid = pd.to_numeric(close, errors="coerce").dropna()
    if valid.empty:
        return {label: None for label in PERIODS}
    latest = float(valid.iloc[-1])
    result: dict[str, float | None] = {}
    for label, trading_days in PERIODS.items():
        if len(valid) <= trading_days:
            result[label] = None
            continue
        base = float(valid.iloc[-(trading_days + 1)])
        result[label] = (latest / base - 1) * 100 if base else None
    return result


def _fmt_return(value: float | None) -> str:
    return "資料不足" if value is None else f"{value:+.1f}%"


def _industry_diagram(card_bg: str, grid: str, text: str, muted: str, accent: str) -> str:
    """用簡化 SVG 呈現四個產業實際做出的零件，以及它們在 AI 伺服器裡的位置。"""
    return dedent(f"""
    <div style="background:{card_bg}; border:1px solid {grid}; border-radius:10px;
                padding:12px 10px 8px; height:430px; box-sizing:border-box;">
      <div style="color:{text}; font-size:15px; margin:0 0 4px 4px;">零件實際放在哪裡？</div>
      <div style="color:{muted}; font-size:11px; margin:0 0 8px 4px;">簡化的 AI 伺服器，不按真實比例</div>
      <svg viewBox="0 0 430 340" width="100%" height="345" role="img"
           aria-label="AI 伺服器的 GPU、電路板、光模組、液冷與晶片設計示意圖">
        <rect x="18" y="25" width="118" height="280" rx="9" fill="none" stroke="{grid}" stroke-width="3"/>
        <text x="77" y="17" text-anchor="middle" fill="{muted}" font-size="12">AI 伺服器機櫃</text>
        <rect x="31" y="48" width="92" height="55" rx="5" fill="{grid}" opacity=".65"/>
        <rect x="31" y="113" width="92" height="55" rx="5" fill="{grid}" opacity=".65"/>
        <rect x="31" y="178" width="92" height="55" rx="5" fill="{grid}" opacity=".65"/>
        <rect x="31" y="243" width="92" height="42" rx="5" fill="{accent}" opacity=".25" stroke="{accent}"/>
        <circle cx="43" cy="264" r="4" fill="{accent}"/><circle cx="55" cy="264" r="4" fill="{accent}"/>

        <path d="M136 140 C160 140, 160 124, 181 124" fill="none" stroke="{muted}" stroke-dasharray="4 4"/>
        <rect x="181" y="82" width="225" height="154" rx="8" fill="#315e49" stroke="#6aa889" stroke-width="2"/>
        <text x="293" y="256" text-anchor="middle" fill="{text}" font-size="13">CCL 加工後 → PCB 綠色電路板</text>

        <rect x="247" y="126" width="82" height="70" rx="7" fill="#20242a" stroke="{accent}" stroke-width="2"/>
        <text x="288" y="157" text-anchor="middle" fill="{text}" font-size="16" font-weight="600">GPU</text>
        <text x="288" y="176" text-anchor="middle" fill="{muted}" font-size="10">AI 運算晶片</text>
        <rect x="352" y="106" width="31" height="25" rx="3" fill="#20242a" stroke="{muted}"/>
        <rect x="352" y="143" width="31" height="25" rx="3" fill="#20242a" stroke="{muted}"/>
        <text x="368" y="95" text-anchor="middle" fill="{text}" font-size="11">其他 IC</text>

        <rect x="181" y="134" width="48" height="37" rx="3" fill="#2f76a3" stroke="#83c8f3" stroke-width="2"/>
        <path d="M181 145 H158 M181 160 H158" stroke="#83c8f3" stroke-width="4"/>
        <text x="204" y="121" text-anchor="middle" fill="{text}" font-size="11">光模組</text>

        <rect x="253" y="116" width="70" height="13" rx="4" fill="#c98646" stroke="#ffd29f"/>
        <path d="M270 116 C270 91, 337 96, 337 62" fill="none" stroke="#59b7dc" stroke-width="7"/>
        <path d="M306 116 C306 99, 359 105, 359 62" fill="none" stroke="#df765f" stroke-width="7"/>
        <text x="346" y="48" text-anchor="middle" fill="{text}" font-size="11">液冷水管＋冷板</text>

        <path d="M329 179 H395" stroke="{muted}" stroke-dasharray="4 3"/>
        <text x="397" y="185" text-anchor="end" fill="{text}" font-size="11">IC 設計公司</text>
        <text x="397" y="200" text-anchor="end" fill="{muted}" font-size="10">畫出晶片藍圖</text>

        <circle cx="37" cy="326" r="5" fill="#2f76a3"/><text x="48" y="330" fill="{muted}" font-size="10">光通訊</text>
        <circle cx="118" cy="326" r="5" fill="#315e49"/><text x="129" y="330" fill="{muted}" font-size="10">CCL／PCB</text>
        <circle cx="218" cy="326" r="5" fill="#20242a" stroke="{accent}"/><text x="229" y="330" fill="{muted}" font-size="10">IC 設計</text>
        <circle cx="309" cy="326" r="5" fill="#c98646"/><text x="320" y="330" fill="{muted}" font-size="10">散熱液冷</text>
      </svg>
    </div>
    """).strip().replace("\n\n", "\n")


def render_ai_industry_map(
    *, accent: str, bg: str, card_bg: str, grid: str, text_muted: str, text_light: str
) -> None:
    """畫出四族群的報酬樹狀圖與 AI 伺服器零件示意圖。"""
    st.markdown(
        f"<div style='color:{accent}; font-size:20px; margin-bottom:3px;'>AI 基礎建設產業地圖</div>"
        f"<div style='color:{text_muted}; font-size:12px; margin-bottom:14px;'>"
        "第一版雛形 · 先用每族群兩檔代表股觀察資金輪動</div>",
        unsafe_allow_html=True,
    )

    selected_period = st.segmented_control(
        "熱力圖期間",
        options=list(PERIODS),
        default="3個月",
        key="industry_map_period",
    )

    all_leaders = [leader for sector in SECTORS for leader in sector["leaders"]]
    histories: dict[str, pd.DataFrame] = {}
    with st.spinner("第一次載入 8 檔代表股，之後切換期間會直接使用快取…"):
        for leader in all_leaders:
            try:
                histories[leader["symbol"]] = _load_map_history(leader["symbol"])
            except Exception:
                histories[leader["symbol"]] = pd.DataFrame()

    symbols = tuple(leader["symbol"] for leader in all_leaders)
    live_prices = _load_live_prices(symbols)

    map_rows = []
    latest_dates = []
    for sector in SECTORS:
        leader_details = []
        selected_values = []
        for leader in sector["leaders"]:
            history = histories[leader["symbol"]]
            if history.empty:
                returns = {label: None for label in PERIODS}
                close = None
                data_date = None
            else:
                returns = calculate_period_returns(history["Close"])
                close = float(history["Close"].iloc[-1])
                data_date = pd.Timestamp(history.index[-1])
                latest_dates.append(data_date)
            current = live_prices.get(leader["symbol"], close)
            selected_value = returns[selected_period]
            if selected_value is not None:
                selected_values.append(selected_value)
            leader_details.append({**leader, "current": current, "returns": returns})

        average = sum(selected_values) / len(selected_values) if selected_values else 0.0
        map_rows.append({**sector, "average": average, "leader_details": leader_details})

    labels = [row["name"] for row in map_rows]
    colors = [row["average"] for row in map_rows]
    hovertexts = []
    for row in map_rows:
        lines = [
            f"<b>{escape(row['name'])}</b>",
            escape(row["role"]),
            f"代表股平均（{selected_period}）：{row['average']:+.1f}%",
            "<br><b>代表公司</b>",
        ]
        for leader in row["leader_details"]:
            price_text = "N/A" if leader["current"] is None else f"{leader['current']:,.2f}"
            lines.append(f"{escape(leader['name'])}　{price_text}")
            lines.append(
                "｜".join(f"{period} {_fmt_return(leader['returns'][period])}" for period in PERIODS)
            )
        hovertexts.append("<br>".join(lines))

    max_abs = max(max(abs(value) for value in colors), 5.0)
    fig = go.Figure(
        go.Treemap(
            labels=labels,
            parents=["AI 基礎建設"] * len(labels),
            values=[1] * len(labels),
            branchvalues="total",
            customdata=colors,
            text=[f"代表股平均 {value:+.1f}%" for value in colors],
            marker=dict(
                colors=colors,
                cmin=-max_abs,
                cmax=max_abs,
                cmid=0,
                colorscale=[[0, "#257a4b"], [0.5, grid], [1, "#c43f45"]],
                line=dict(color=bg, width=4),
                colorbar=dict(title=f"{selected_period} %", tickfont=dict(color=text_muted)),
            ),
            texttemplate="<b>%{label}</b><br>%{text}",
            textfont=dict(color=text_light, size=16),
            hovertext=hovertexts,
            hovertemplate="%{hovertext}<extra></extra>",
            pathbar=dict(visible=False),
            root_color=card_bg,
        )
    )
    fig.update_layout(
        height=430,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="monospace", color=text_light),
    )

    visual_grid = st.container(key="industry_map_visuals")
    map_col, diagram_col = visual_grid.columns([1.55, 1])
    with map_col:
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    with diagram_col:
        st.markdown(
            _industry_diagram(card_bg, grid, text_light, text_muted, accent),
            unsafe_allow_html=True,
        )

    latest_label = max(latest_dates).strftime("%Y-%m-%d") if latest_dates else "暫無資料"
    st.caption(
        f"股價報酬資料截至 {latest_label}。色塊目前是兩檔代表股的等權平均；"
        "游標停在色塊可看目前股價及 1／3／6／12 個月漲跌。"
    )
    st.info(
        "這是刻意縮小的雛形：先確認產業地圖、顏色與零件示意是否直覺；"
        "確認方向後，再把照片中的其餘公司納入完整產業平均。"
    )
