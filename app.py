"""台股投資 AI 工具 — Streamlit dashboard（v1 骨架）。

Hour 5：只顯示追蹤清單的走勢圖 + 均線疊圖，警示/agent 在後面的 checkpoint 才加。
風格參考使用者提供的深色終端機風 dashboard：深色底、等寬字、橘色重點色、卡片分區。
"""
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.watchlist import WATCHLIST
from data.fetch import fetch_history, get_current_price
from data.indicators import add_moving_averages, MA_WINDOWS

ACCENT = "#e8935a"
BG = "#0d0d0d"
CARD_BG = "#161616"
GRID = "#2a2a2a"
TEXT_MUTED = "#8a8880"

st.set_page_config(page_title="台股投資 AI 工具", layout="wide")

st.markdown(
    f"""
    <div style="display:flex; justify-content:space-between; align-items:baseline;
                border-bottom:1px solid {GRID}; padding-bottom:12px; margin-bottom:20px;">
      <div>
        <span style="color:{ACCENT}; font-size:22px;">台股投資 AI 工具</span>
        <div style="color:{TEXT_MUTED}; font-size:13px;">tw-invest-copilot · v1</div>
      </div>
      <div style="color:{TEXT_MUTED}; font-size:13px;">
        last update: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=300)
def load_history(symbol: str):
    return fetch_history(symbol)


# MA 線刻意避開紅/綠（留給K線漲跌用），深色底上要夠亮才看得清楚
MA_COLORS = {5: "#5b9bd5", 10: "#a89ef0", 20: "#f0b429", 60: "#c4c1b8"}

for item in WATCHLIST:
    symbol, name = item["symbol"], item["name"]

    df = load_history(symbol)
    price = get_current_price(symbol, df)
    df = add_moving_averages(df, MA_WINDOWS)
    latest = df.iloc[-1]

    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(
                f"<span style='color:{ACCENT}; font-size:16px;'>{name}</span> "
                f"<span style='color:{TEXT_MUTED}; font-size:13px;'>{symbol}</span>",
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                f"<div style='text-align:right; font-size:20px;'>{price:.2f}</div>",
                unsafe_allow_html=True,
            )

        fig = go.Figure()
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                name="K線",
                showlegend=False,
                # 台股慣例：紅漲、綠跌（跟 Plotly 預設的美式紅跌綠漲相反）
                increasing_line_color="#ef5350",
                increasing_fillcolor="#ef5350",
                decreasing_line_color="#4caf50",
                decreasing_fillcolor="#4caf50",
            )
        )
        for w in MA_WINDOWS:
            ma_value = latest[f"MA{w}"]
            label = f"MA{w} {ma_value:.1f}" if pd.notna(ma_value) else f"MA{w} N/A"
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df[f"MA{w}"],
                    name=label,
                    line=dict(color=MA_COLORS[w], width=1.5),
                )
            )
        fig.update_layout(
            height=380,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_rangeslider_visible=False,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                font=dict(color=TEXT_MUTED, size=11),
            ),
            plot_bgcolor=CARD_BG,
            paper_bgcolor=CARD_BG,
            font=dict(color=TEXT_MUTED, family="monospace"),
            hovermode="x unified",
            xaxis=dict(showgrid=False, color=TEXT_MUTED),
            yaxis=dict(gridcolor=GRID, color=TEXT_MUTED),
        )
        st.plotly_chart(fig, use_container_width=True)
