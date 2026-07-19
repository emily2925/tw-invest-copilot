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

from agent.daily_brief import build_signal_summary, generate_daily_brief
from config.watchlist import WATCHLIST
from data.fetch import fetch_history, get_current_price
from data.indicators import add_bollinger_bands, add_moving_averages, front_high_signal, MA_WINDOWS
from data.macro import fetch_foreign_futures_position, fetch_sox, fetch_twd_usd, value_and_change
from data.overnight import fetch_overnight_intraday, get_overnight_sentiment

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


@st.cache_data(ttl=21600)  # 6小時：這幾個都要逐日查詢很慢，拉長快取效期
def load_macro_series(kind: str):
    if kind == "twd":
        return fetch_twd_usd(period="1mo")
    if kind == "sox":
        return fetch_sox(period="1mo")
    if kind == "foreign_futures":
        return fetch_foreign_futures_position(lookback_trading_days=20)
    raise ValueError(kind)


@st.cache_data(ttl=1800)
def load_overnight_summary():
    return get_overnight_sentiment()


@st.cache_data(ttl=1800)
def load_overnight_intraday():
    return fetch_overnight_intraday()


def day_over_day_change(df: pd.DataFrame) -> dict:
    """跟前一筆比（不是跟整段區間第一筆比）。夜盤用這個比較合理——
    要看的是「昨晚 vs 前一晚」的動能，不是跟一個月前比。"""
    current = float(df["Close"].iloc[-1])
    prev = float(df["Close"].iloc[-2])
    change_pct = (current - prev) / prev * 100 if prev else 0.0
    return {"current": current, "change_pct": change_pct}


def render_sparkline(df, up: bool):
    """直條圖：一天一根柱子，柱子頂端的連線就能看出趨勢，也能個別看到每日數值。
    y 軸緊貼資料範圍（不然像匯率這種變動幅度小的會被壓平看不出變化），
    x 軸留頭尾日期刻度當參考。"""
    bar_color = "#ef5350" if up else "#4caf50"  # 台股慣例：紅漲綠跌，跟主圖一致
    values = df["Close"]
    pad = (values.max() - values.min()) * 0.15 or values.max() * 0.01
    dates_str = df.index.strftime("%Y/%m/%d") if hasattr(df.index, "strftime") else [str(i) for i in df.index]
    tick_dates_str = df.index.strftime("%m/%d") if hasattr(df.index, "strftime") else dates_str

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=list(range(len(df))), y=values, marker_color=bar_color,
            text=dates_str, hovertemplate="%{text}<br>%{y:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        height=70,
        margin=dict(l=0, r=0, t=4, b=4),
        showlegend=False,
        bargap=0.25,
        plot_bgcolor=CARD_BG,
        paper_bgcolor=CARD_BG,
        yaxis=dict(
            visible=False,
            range=[values.min() - pad, values.max() + pad],
        ),
        xaxis=dict(
            tickmode="array",
            tickvals=[0, len(df) - 1],
            ticktext=[tick_dates_str[0], tick_dates_str[-1]],
            tickfont=dict(color=TEXT_MUTED, size=10),
            showgrid=False,
        ),
    )
    return fig


def render_intraday_line(df):
    """夜盤走勢圖：整個交易時段的逐分鐘折線（不是逐日收盤價），x 軸留開盤/收盤時間點。"""
    values = df["Close"]
    up = values.iloc[-1] >= values.iloc[0]
    line_color = "#ef5350" if up else "#4caf50"
    pad = (values.max() - values.min()) * 0.15 or values.max() * 0.01

    time_labels = [f"{t[:2]}:{t[2:]}" for t in df["Time"]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=list(range(len(df))), y=values, mode="lines", line=dict(color=line_color, width=1.5),
            text=time_labels, hovertemplate="%{text}<br>%{y:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        height=70,
        margin=dict(l=0, r=0, t=4, b=4),
        showlegend=False,
        plot_bgcolor=CARD_BG,
        paper_bgcolor=CARD_BG,
        yaxis=dict(visible=False, range=[values.min() - pad, values.max() + pad]),
        xaxis=dict(
            tickmode="array",
            tickvals=[0, len(df) - 1],
            ticktext=[time_labels[0], time_labels[-1]],
            tickfont=dict(color=TEXT_MUTED, size=10),
            showgrid=False,
        ),
    )
    return fig


st.markdown(
    f"<div style='color:{ACCENT}; font-size:16px; margin-bottom:8px;'>警示指標</div>",
    unsafe_allow_html=True,
)

alert_cols = st.columns(4)

# 台指夜盤：獨立處理——走勢圖是「最近一次整個交易時段」的逐分鐘折線，
# 不是逐日收盤價；標題數值/漲跌%用 TAIFEX 每日行情表的官方收盤數字（跟逐分鐘資料最後一筆
# 會有些微差異，屬正常現象，官方數字才是準的）。
with alert_cols[0]:
    with st.container(border=True):
        try:
            summary = load_overnight_summary()
            intraday = load_overnight_intraday()
            up = summary["change_pct"] >= 0
            c = "#ef5350" if up else "#4caf50"
            st.markdown(
                f"""
                <div style="color:{TEXT_MUTED}; font-size:12px;">台指夜盤（昨夜，{summary['expiry']}）</div>
                <div style="font-size:24px; margin:2px 0;">{summary['close']:,.0f}</div>
                <div style="color:{c}; font-size:13px;">{summary['change']} ({summary['change_pct']:+.2f}%)</div>
                """,
                unsafe_allow_html=True,
            )
            st.plotly_chart(render_intraday_line(intraday), width="stretch", config={"displayModeBar": False})
        except Exception as e:
            st.markdown(f"<div style='color:{TEXT_MUTED}; font-size:12px;'>台指夜盤：暫時抓不到（{e}）</div>", unsafe_allow_html=True)

# change_mode: "period"（跟區間第一筆比）／None（不顯示%，外資空單用，
# 因為數值本身是負的，「淨空單越多」是往更負的方向走，%變化不直觀甚至會誤導）
ALERT_INDICATORS = [
    {"key": "twd", "label": "台幣兌美元（近1個月）", "fmt": ".3f", "change_mode": "period", "note": None},
    {"key": "sox", "label": "費城半導體指數（近1個月）", "fmt": ",.0f", "change_mode": "period", "note": None},
    {"key": "foreign_futures", "label": "外資台指期未平倉淨額（近1個月）", "fmt": ",.0f", "change_mode": None,
     "note": "外資台指期貨(TXF)多空未平倉淨額口數，資料源 TAIFEX，負值代表淨空單，越負代表空單越多"},
]

for col, spec in zip(alert_cols[1:], ALERT_INDICATORS):
    with col:
        with st.container(border=True):
            try:
                series = load_macro_series(spec["key"])
                current = float(series["Close"].iloc[-1])
                change_html = ""
                up = True
                if spec["change_mode"] == "day_over_day":
                    vc = day_over_day_change(series)
                    up = vc["change_pct"] >= 0
                    c = "#ef5350" if up else "#4caf50"
                    change_html = f"<div style='color:{c}; font-size:13px;'>{vc['change_pct']:+.2f}%</div>"
                elif spec["change_mode"] == "period":
                    vc = value_and_change(series)
                    up = vc["change_pct"] >= 0
                    c = "#ef5350" if up else "#4caf50"
                    change_html = f"<div style='color:{c}; font-size:13px;'>{vc['change_pct']:+.2f}%</div>"
                else:
                    up = current >= float(series["Close"].iloc[0])  # 沒有%時，柱子顏色跟著整段趨勢方向走

                st.markdown(
                    f"""
                    <div style="color:{TEXT_MUTED}; font-size:12px;">{spec['label']}</div>
                    <div style="font-size:24px; margin:2px 0;">{current:{spec['fmt']}}</div>
                    {change_html}
                    """,
                    unsafe_allow_html=True,
                )
                st.plotly_chart(render_sparkline(series, up), width="stretch", config={"displayModeBar": False})
                if spec["note"]:
                    st.markdown(
                        f"<div style='color:{TEXT_MUTED}; font-size:10px;'>{spec['note']}</div>",
                        unsafe_allow_html=True,
                    )
            except Exception as e:
                st.markdown(
                    f"<div style='color:{TEXT_MUTED}; font-size:12px;'>{spec['label']}：暫時抓不到（{e}）</div>",
                    unsafe_allow_html=True,
                )


# MA 線刻意避開紅/綠（留給K線漲跌用），深色底上要夠亮才看得清楚
MA_COLORS = {5: "#5b9bd5", 10: "#a89ef0", 20: "#f0b429", 60: "#c4c1b8"}

# 「今日」沒有放進來：我們的歷史資料是日線（一天一根K棒），沒有分鐘級盤中資料，
# 「今日」放進日K圖只會看到1根棒子沒有意義。之後若要做盤中圖是另一個功能。
RANGE_OPTIONS = {"1個月": 21, "3個月": 63, "6個月": 126, "1年": 252, "全部": None}
selected_range = st.segmented_control("time range", options=list(RANGE_OPTIONS.keys()), default="3個月", label_visibility="collapsed")
selected_range = selected_range or "3個月"

front_high_signals_for_brief = []  # 給 Hour 7 的今日重點摘要用

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
    if signal:
        front_high_signals_for_brief.append({"name": name, "message": signal["message"]})

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


# Hour 7：AI 今日重點摘要——把上面算好的訊號丟給 agent，生成一段自然語言摘要。
# 這是這個週末唯一真正用到 agent framework（OpenAI Agents SDK + LiteLLM + Claude）的地方，
# 其餘都是決定性的資料處理/規則判斷。


@st.cache_data(ttl=1800)
def load_daily_brief(signal_text: str) -> str:
    return generate_daily_brief(signal_text)


st.markdown(
    f"<div style='color:{ACCENT}; font-size:16px; margin:24px 0 8px;'>今日重點（AI 摘要）</div>",
    unsafe_allow_html=True,
)
try:
    overnight_summary = load_overnight_summary()
    foreign_futures_series = load_macro_series("foreign_futures")
    twd_series = load_macro_series("twd")
    sox_series = load_macro_series("sox")
    foreign_futures_vc = value_and_change(foreign_futures_series)
    sox_vc = value_and_change(sox_series)

    signal_text = build_signal_summary(
        overnight=overnight_summary,
        foreign_futures_current=float(foreign_futures_series["Close"].iloc[-1]),
        foreign_futures_change_pct=foreign_futures_vc["change_pct"],
        twd_current=float(twd_series["Close"].iloc[-1]),
        sox_current=float(sox_series["Close"].iloc[-1]),
        sox_change_pct=sox_vc["change_pct"],
        front_high_signals=front_high_signals_for_brief,
    )
    brief_text = load_daily_brief(signal_text)
    with st.container(border=True):
        st.markdown(f"<div style='line-height:1.7;'>{brief_text}</div>", unsafe_allow_html=True)
except Exception as e:
    st.markdown(f"<div style='color:{TEXT_MUTED}; font-size:13px;'>今日重點暫時生成不了（{e}）</div>", unsafe_allow_html=True)
