"""台股投資 AI 工具 — Streamlit dashboard（v1 骨架）。

Hour 5：只顯示追蹤清單的走勢圖 + 均線疊圖，警示/agent 在後面的 checkpoint 才加。
風格參考使用者提供的深色終端機風 dashboard：深色底、等寬字、橘色重點色、卡片分區。
"""
import os
import sys
from datetime import datetime

# 保險起見明確把專案根目錄加進 sys.path——不加的話，Streamlit 重新執行腳本時
# 有時候找不到同層的 config/、data/ 這些本地 package（曾經在瀏覽器實測時遇到
# ModuleNotFoundError: No module named 'data.fetch'，本機單獨跑 python3 -m 不會重現）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.watchlist import WATCHLIST
from data.fetch import fetch_history, get_current_price
from data.indicators import add_bollinger_bands, add_moving_averages, front_high_signal, MA_WINDOWS
from data.macro import fetch_foreign_short_trend, fetch_sox, fetch_twd_usd, value_and_change
from data.overnight import get_overnight_sentiment

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


@st.cache_data(ttl=1800)
def load_overnight_sentiment():
    return get_overnight_sentiment()


@st.cache_data(ttl=1800)
def load_macro_series(kind: str, lookback_days: int):
    if kind == "twd":
        return fetch_twd_usd(period="3mo")
    if kind == "sox":
        return fetch_sox(period="3mo")
    if kind == "short":
        return fetch_foreign_short_trend(lookback_days=lookback_days)
    raise ValueError(kind)


def render_sparkline(df, up: bool):
    """小折線圖：不要座標軸/格線/圖例，只給一條乾淨的趨勢線。"""
    # 台股慣例：紅漲綠跌，跟主圖一致
    line_color, fill_color = ("#ef5350", "rgba(239,83,80,0.08)") if up else ("#4caf50", "rgba(76,175,80,0.08)")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=list(range(len(df))), y=df["Close"], mode="lines",
            line=dict(color=line_color, width=1.5), fill="tozeroy", fillcolor=fill_color,
        )
    )
    fig.update_layout(
        height=60,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        plot_bgcolor=CARD_BG,
        paper_bgcolor=CARD_BG,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig


st.markdown(
    f"<div style='color:{ACCENT}; font-size:16px; margin-bottom:8px;'>警示指標</div>",
    unsafe_allow_html=True,
)

alert_cols = st.columns(4)

# 台指夜盤：只看最近一次（昨夜），不用畫趨勢圖
with alert_cols[0]:
    with st.container(border=True):
        try:
            overnight = load_overnight_sentiment()
            up = overnight["change_pct"] >= 0
            c = "#ef5350" if up else "#4caf50"
            st.markdown(
                f"""
                <div style="color:{TEXT_MUTED}; font-size:12px;">台指夜盤（昨夜）</div>
                <div style="font-size:24px; margin:2px 0;">{overnight['close']:,.0f}</div>
                <div style="color:{c}; font-size:13px;">{overnight['change']} ({overnight['change_pct']:+.2f}%) · {overnight['sentiment']}</div>
                """,
                unsafe_allow_html=True,
            )
        except Exception as e:
            st.markdown(f"<div style='color:{TEXT_MUTED}; font-size:12px;'>台指夜盤：暫時抓不到（{e}）</div>", unsafe_allow_html=True)

# 台幣兌美元匯率：近3個月
with alert_cols[1]:
    with st.container(border=True):
        try:
            twd = load_macro_series("twd", 0)
            vc = value_and_change(twd)
            up = vc["change_pct"] >= 0
            c = "#ef5350" if up else "#4caf50"
            st.markdown(
                f"""
                <div style="color:{TEXT_MUTED}; font-size:12px;">台幣兌美元（近3個月）</div>
                <div style="font-size:24px; margin:2px 0;">{vc['current']:.3f}</div>
                <div style="color:{c}; font-size:13px;">{vc['change_pct']:+.2f}%</div>
                """,
                unsafe_allow_html=True,
            )
            st.plotly_chart(render_sparkline(twd, up), width="stretch", config={"displayModeBar": False})
        except Exception as e:
            st.markdown(f"<div style='color:{TEXT_MUTED}; font-size:12px;'>台幣匯率：暫時抓不到（{e}）</div>", unsafe_allow_html=True)

# 費城半導體指數：近3個月
with alert_cols[2]:
    with st.container(border=True):
        try:
            sox = load_macro_series("sox", 0)
            vc = value_and_change(sox)
            up = vc["change_pct"] >= 0
            c = "#ef5350" if up else "#4caf50"
            st.markdown(
                f"""
                <div style="color:{TEXT_MUTED}; font-size:12px;">費城半導體指數（近3個月）</div>
                <div style="font-size:24px; margin:2px 0;">{vc['current']:,.0f}</div>
                <div style="color:{c}; font-size:13px;">{vc['change_pct']:+.2f}%</div>
                """,
                unsafe_allow_html=True,
            )
            st.plotly_chart(render_sparkline(sox, up), width="stretch", config={"displayModeBar": False})
        except Exception as e:
            st.markdown(f"<div style='color:{TEXT_MUTED}; font-size:12px;'>費半：暫時抓不到（{e}）</div>", unsafe_allow_html=True)

# 外資空單趨勢（整體市場融券餘額代理）：近1個月
with alert_cols[3]:
    with st.container(border=True):
        try:
            short = load_macro_series("short", 30)
            vc = value_and_change(short)
            up = vc["change_pct"] >= 0
            c = "#ef5350" if up else "#4caf50"
            st.markdown(
                f"""
                <div style="color:{TEXT_MUTED}; font-size:12px;">外資空單趨勢＊（近1個月）</div>
                <div style="font-size:24px; margin:2px 0;">{vc['current']:,.0f}</div>
                <div style="color:{c}; font-size:13px;">{vc['change_pct']:+.2f}%</div>
                """,
                unsafe_allow_html=True,
            )
            st.plotly_chart(render_sparkline(short, up), width="stretch", config={"displayModeBar": False})
            st.markdown(
                f"<div style='color:{TEXT_MUTED}; font-size:10px;'>＊整體市場融券餘額代理，非外資專屬空單</div>",
                unsafe_allow_html=True,
            )
        except Exception as e:
            st.markdown(f"<div style='color:{TEXT_MUTED}; font-size:12px;'>外資空單：暫時抓不到（{e}）</div>", unsafe_allow_html=True)


# MA 線刻意避開紅/綠（留給K線漲跌用），深色底上要夠亮才看得清楚
MA_COLORS = {5: "#5b9bd5", 10: "#a89ef0", 20: "#f0b429", 60: "#c4c1b8"}

# 「今日」沒有放進來：我們的歷史資料是日線（一天一根K棒），沒有分鐘級盤中資料，
# 「今日」放進日K圖只會看到1根棒子沒有意義。之後若要做盤中圖是另一個功能。
RANGE_OPTIONS = {"1個月": 21, "3個月": 63, "6個月": 126, "1年": 252, "全部": None}
selected_range = st.segmented_control("time range", options=list(RANGE_OPTIONS.keys()), default="3個月", label_visibility="collapsed")
selected_range = selected_range or "3個月"

for item in WATCHLIST:
    symbol, name = item["symbol"], item["name"]

    df = load_history(symbol)
    price = get_current_price(symbol, df)
    df = add_moving_averages(df, MA_WINDOWS)  # 用全部歷史算，均線在顯示範圍起點才不會不準
    df = add_bollinger_bands(df)
    latest = df.iloc[-1]
    n = RANGE_OPTIONS[selected_range]
    display_df = df if n is None else df.tail(n)
    signal = front_high_signal(df, price)

    # 判斷「前一收盤」：如果目前價格已經跟歷史最後一筆一樣（代表當下沒有更新的即時價，
    # 例如休市中），前一收盤要往前抓一天，不然漲跌會算成 0
    if abs(price - float(df["Close"].iloc[-1])) < 0.01:
        prev_close = float(df["Close"].iloc[-2])
    else:
        prev_close = float(df["Close"].iloc[-1])
    change = price - prev_close
    change_pct = change / prev_close * 100 if prev_close else 0.0
    up = change >= 0
    change_color = "#ef5350" if up else "#4caf50"  # 台股慣例：紅漲綠跌
    arrow = "▲" if up else "▼"

    with st.container(border=True):
        st.markdown(
            f"<span style='color:{TEXT_MUTED}; font-size:15px;'>{name}</span> "
            f"<span style='color:{TEXT_MUTED}; font-size:13px;'>{symbol}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div style="display:flex; align-items:baseline; gap:12px; margin:4px 0 8px;">
              <span style="font-size:36px; font-weight:500;">{price:,.2f}</span>
              <span style="color:{change_color}; font-size:18px;">
                {arrow} {abs(change):,.2f} ({abs(change_pct):.2f}%)
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if signal:
            st.markdown(
                f"<div style='background:{ACCENT}22; color:{ACCENT}; border-radius:6px; "
                f"padding:6px 12px; font-size:13px; display:inline-block; margin-bottom:8px;'>"
                f"{signal['message']}</div>",
                unsafe_allow_html=True,
            )

        dates_str = display_df.index.strftime("%Y-%m-%d")  # 類別軸用字串日期，天然跳過週末不留空隙

        fig = go.Figure()
        fig.add_trace(
            go.Candlestick(
                x=dates_str,
                open=display_df["Open"],
                high=display_df["High"],
                low=display_df["Low"],
                close=display_df["Close"],
                name="K線",
                showlegend=False,
                line=dict(width=1),
                # 台股慣例：紅漲、綠跌（跟 Plotly 預設的美式紅跌綠漲相反）
                increasing_line_color="#ef5350",
                increasing_fillcolor="#ef5350",
                decreasing_line_color="#4caf50",
                decreasing_fillcolor="#4caf50",
            )
        )
        # 布林通道：先畫下軌（不填色）、再畫上軌並往下填色到下軌，形成一個帶狀區間
        fig.add_trace(
            go.Scatter(
                x=dates_str, y=display_df["BB_lower"], name="布林下軌",
                line=dict(color="#5f5e5a", width=1, dash="dot"), showlegend=False,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=dates_str, y=display_df["BB_upper"], name="布林通道",
                line=dict(color="#5f5e5a", width=1, dash="dot"),
                fill="tonexty", fillcolor="rgba(95,94,90,0.12)",
            )
        )
        for w in MA_WINDOWS:
            ma_value = latest[f"MA{w}"]
            label = f"MA{w} {ma_value:.1f}" if pd.notna(ma_value) else f"MA{w} N/A"
            fig.add_trace(
                go.Scatter(
                    x=dates_str,
                    y=display_df[f"MA{w}"],
                    name=label,
                    line=dict(color=MA_COLORS[w], width=1),
                )
            )
        if signal:
            # 標出前高位置：橘色虛線＋價位標籤，跟警示標籤同色系一眼對得起來
            fig.add_hline(
                y=signal["front_high"],
                line=dict(color=ACCENT, width=1.2, dash="dash"),
                annotation_text=f"前高 {signal['front_high']:.1f}",
                annotation_position="top left",
                annotation_font=dict(color=ACCENT, size=11),
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
            xaxis=dict(type="category", showgrid=False, color=TEXT_MUTED, nticks=8),
            yaxis=dict(gridcolor=GRID, color=TEXT_MUTED),
        )
        st.plotly_chart(fig, width="stretch")
