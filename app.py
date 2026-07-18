"""台股投資 AI 工具 — Streamlit dashboard（v1 骨架）。

Hour 5：只顯示追蹤清單的走勢圖 + 均線疊圖，警示/agent 在後面的 checkpoint 才加。
"""
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


MA_COLORS = {5: "#eb6834", 10: "#eda100", 20: "#4a3aa7", 60: "#1baf7a"}

for item in WATCHLIST:
    symbol, name = item["symbol"], item["name"]

    df = load_history(symbol)
    price = get_current_price(symbol, df)
    df = add_moving_averages(df, MA_WINDOWS)

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
        )
    )
    for w in MA_WINDOWS:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[f"MA{w}"],
                name=f"MA{w}",
                line=dict(color=MA_COLORS[w], width=1.5),
            )
        )
    fig.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)
