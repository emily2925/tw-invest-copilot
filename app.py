"""台股投資 AI 工具 — Streamlit dashboard（v1 骨架）。

Hour 5：只顯示追蹤清單的走勢圖 + 均線疊圖，警示/agent 在後面的 checkpoint 才加。
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.watchlist import WATCHLIST
from data.fetch import fetch_history, get_current_price
from data.indicators import add_moving_averages, MA_WINDOWS

st.set_page_config(page_title="台股投資 AI 工具", layout="wide")
st.title("台股投資 AI 工具")


@st.cache_data(ttl=300)
def load_history(symbol: str):
    return fetch_history(symbol)


# MA 線刻意避開紅/綠（留給K線漲跌用），走藍紫灰色系，短天期較亮、長天期較沉，方便辨識
MA_COLORS = {5: "#2a78d6", 10: "#7f77dd", 20: "#eda100", 60: "#5f5e5a"}

for item in WATCHLIST:
    symbol, name = item["symbol"], item["name"]

    df = load_history(symbol)
    price = get_current_price(symbol, df)
    df = add_moving_averages(df, MA_WINDOWS)
    latest = df.iloc[-1]

    st.subheader(f"{name}（{symbol}）")
    st.metric("目前價格", f"{price:.2f}")

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
            increasing_line_color="#d64545",
            increasing_fillcolor="#d64545",
            decreasing_line_color="#2f9e44",
            decreasing_fillcolor="#2f9e44",
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
        height=420,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="white",
        paper_bgcolor="white",
        hovermode="x unified",
        xaxis=dict(gridcolor="#f0efec", showgrid=False),
        yaxis=dict(gridcolor="#f0efec"),
    )
    st.plotly_chart(fig, use_container_width=True)
