"""台股投資 AI 工具 — Streamlit dashboard（v1 骨架）。

Hour 5：只顯示追蹤清單的走勢圖 + 均線疊圖，警示/agent 在後面的 checkpoint 才加。
風格參考使用者提供的深色終端機風 dashboard：深色底、等寬字、橘色重點色、卡片分區。
"""
import os
import sys
from datetime import datetime

# 保險起見明確把專案根目錄加進 sys.path——不加的話，Streamlit 重新執行腳本時
# 有時候找不到同層的 config/、data/ 這些本地 package（曾經在瀏覽器實測時遇到
# ModuleNotFoundError: No module named 'market_data.fetch'，本機單獨跑 python3 -m 不會重現）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# 部署到 Streamlit Cloud 時沒有本機的 .env，改把雲端 secrets 灌進環境變數，
# 讓下面 data/、agent/ 模組既有的 os.environ.get(...) 在雲端也讀得到 key。
# 必須在 import 那些模組「之前」做——data/fetch.py 在 import 當下就會讀 token 並登入。
for _key in ("ANTHROPIC_API_KEY", "FINMIND_API_TOKEN"):
    try:
        if not os.environ.get(_key) and _key in st.secrets:
            os.environ[_key] = str(st.secrets[_key])
    except Exception:
        pass

try:
    from agent.stock_analyst import build_stock_context, generate_stock_analysis
    from agent.spend_tracker import add_spend, load_total_spend
    from config.watchlist import WATCHLIST
    from market_data.corporate_actions_fetch import fetch_share_basis_changes
    from market_data.eps_adjustment import prepare_split_adjusted_eps_summary
    from market_data.eps_fetch import fetch_quarterly_eps
    from market_data.fundamental_fetch import fetch_monthly_revenue
    from market_data.fundamentals import is_company_fundamentals_applicable, prepare_revenue_trend
    from market_data.institutional_fetch import (
        fetch_foreign_shareholding,
        fetch_institutional_investors,
        fetch_margin_short,
    )
    from market_data.institutional import (
        is_institutional_applicable,
        prepare_foreign_shareholding,
        prepare_institutional_net,
        prepare_margin_short,
    )
    from market_data.fetch import fetch_history, get_current_price
    from market_data.indicators import (
        MA_WINDOWS,
        add_bollinger_bands,
        add_moving_averages,
        front_high_signal,
        moving_average_cross_signals,
    )
    from market_data.macro import fetch_foreign_futures_position, fetch_sox, fetch_twd_usd, value_and_change
    from market_data.overnight import fetch_overnight_intraday, get_overnight_sentiment
    from market_data.pe_fetch import fetch_pe_history
    from market_data.valuation import build_pe_river, is_pe_river_applicable
except ModuleNotFoundError as exc:
    # Streamlit Cloud 的預設錯誤頁會隱藏真正缺少的模組名稱，導致無法遠端診斷。
    # 只顯示 exc.name（不含路徑、環境變數或 traceback），不會洩漏 secrets。
    st.error("部署環境缺少必要的 Python 模組")
    st.code(f"ModuleNotFoundError: No module named '{exc.name}'")
    st.caption("請將這一行回報給開發者，以便修正 requirements.txt。")
    st.stop()

BUDGET_USD = 5.0  # AI 摘要功能的花費上限提示，之後隨時可以改

st.set_page_config(page_title="台股投資雷達", layout="wide")

# 主題色盤：暗色（終端機風）與亮色兩套。畫面所有顏色（含 plotly 圖）都吃這幾個常數，
# 所以切換主題只要換這組值 + 注入對應 CSS 蓋掉 Streamlit 外框即可。
PALETTES = {
    "暗色": {"ACCENT": "#e8935a", "BG": "#0d0d0d", "CARD_BG": "#161616",
             "GRID": "#2a2a2a", "TEXT_MUTED": "#8a8880", "TEXT_LIGHT": "#e8e6e0"},
    "亮色": {"ACCENT": "#c0621f", "BG": "#ece7dc", "CARD_BG": "#ffffff",
             "GRID": "#c9c0ad", "TEXT_MUTED": "#585245", "TEXT_LIGHT": "#26231d"},
}
theme_name = st.session_state.get("theme_choice", "暗色")
_pal = PALETTES.get(theme_name, PALETTES["暗色"])
ACCENT = _pal["ACCENT"]
BG = _pal["BG"]
CARD_BG = _pal["CARD_BG"]
GRID = _pal["GRID"]
TEXT_MUTED = _pal["TEXT_MUTED"]
TEXT_LIGHT = _pal["TEXT_LIGHT"]

# 注入主題 CSS：蓋掉 Streamlit 內建的頁面底色、文字色、卡片底色與邊框。
st.markdown(
    f"""
    <style>
      html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
      [data-testid="stHeader"] {{ background-color: {BG} !important; }}
      [data-testid="stAppViewContainer"], .stApp, [data-testid="stMarkdownContainer"],
      .stMarkdown, p, span, label, h1, h2, h3, [data-testid="stWidgetLabel"] p {{
        color: {TEXT_LIGHT};
      }}
      [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {{
        color: {TEXT_MUTED} !important;
      }}
      /* st.container(border=True) 卡片底色與明顯邊框 */
      [data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: {CARD_BG} !important;
        border: 1px solid {GRID} !important;
      }}
      /* 一般按鈕（例：產生今日重點） */
      .stButton > button {{
        background-color: {CARD_BG} !important; color: {TEXT_LIGHT} !important;
        border: 1px solid {GRID} !important;
      }}
      /* 下拉選單（產業篩選）收合框：整個控制項換成卡片底色＋主題文字色 */
      [data-testid="stSelectbox"] div {{ background-color: {CARD_BG} !important; }}
      [data-testid="stSelectbox"] * {{ color: {TEXT_LIGHT} !important; }}
      /* 下拉展開的選項清單（實際 testid 是 stSelectboxVirtualDropdown，畫在 body portal） */
      [data-testid="stSelectboxVirtualDropdown"] {{ background-color: {CARD_BG} !important; }}
      [data-testid="stSelectboxVirtualDropdown"] * {{ color: {TEXT_LIGHT} !important; }}
      [data-testid="stSelectboxVirtualDropdown"] li:hover {{ background-color: {GRID} !important; }}
      /* 分段控制（時間範圍／主題／面向）：未選取吃卡片底色，選取維持橘色高亮 */
      [data-testid="stButtonGroup"] button[aria-checked="false"] {{
        background-color: {CARD_BG} !important; color: {TEXT_LIGHT} !important;
        border-color: {GRID} !important;
      }}
      [data-testid="stButtonGroup"] button[aria-checked="true"] {{
        background-color: {ACCENT}33 !important; color: {ACCENT} !important;
        border-color: {ACCENT} !important;
      }}
    </style>
    """,
    unsafe_allow_html=True,
)

head_col, theme_col = st.columns([5, 1])
with head_col:
    st.markdown(
        f"""
        <div style="display:flex; align-items:baseline; gap:12px;
                    padding-bottom:12px; margin-bottom:8px;">
          <span style="color:{ACCENT}; font-size:22px;">台股投資雷達</span>
          <span style="color:{TEXT_MUTED}; font-size:13px;">tw-invest-copilot · v1</span>
          <span style="color:{TEXT_MUTED}; font-size:13px;">
            · last update: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
with theme_col:
    st.segmented_control(
        "主題", options=["暗色", "亮色"], default="暗色",
        key="theme_choice", label_visibility="collapsed",
    )
st.markdown(
    f"<div style='border-bottom:1px solid {GRID}; margin-bottom:20px;'></div>",
    unsafe_allow_html=True,
)

# 分類順序依 WATCHLIST 第一次出現的順序，避免每次重跑後選項跳動。
categories = list(dict.fromkeys(item["category"] for item in WATCHLIST))
RANGE_OPTIONS = {"1個月": 21, "3個月": 63, "6個月": 126, "1年": 252, "全部": None}

# 控制元件會畫在警示指標下方；這裡先讀 session_state，讓篩選結果能供上方 AI 摘要使用。
selected_category = st.session_state.get("category_filter", "全部")
if selected_category not in ["全部", *categories]:
    selected_category = "全部"
selected_range = st.session_state.get("range_filter", "3個月")
if selected_range not in RANGE_OPTIONS:
    selected_range = "3個月"

if selected_category == "全部":
    filtered_watchlist = WATCHLIST
else:
    filtered_watchlist = [item for item in WATCHLIST if item["category"] == selected_category]
@st.cache_data(ttl=300)
def load_history(symbol: str):
    return fetch_history(symbol)


@st.cache_data(ttl=21600)
def load_pe_river(symbol: str):
    """需要時才抓近5年價格與 PE，避免首頁一次載入所有個股的長期估值資料。"""
    price_history = fetch_history(symbol, lookback_days=1900)
    pe_history = fetch_pe_history(symbol, lookback_days=1900)
    return build_pe_river(price_history, pe_history)


@st.cache_data(ttl=21600)
def load_revenue_trend(symbol: str):
    """抓足夠月份計算 YoY，但畫面只顯示最近12個月。"""
    revenue = fetch_monthly_revenue(symbol, lookback_months=30)
    return prepare_revenue_trend(revenue, display_months=12)


@st.cache_data(ttl=21600)
def load_eps_summary(symbol: str):
    eps = fetch_quarterly_eps(symbol, lookback_years=4)
    basis_changes = fetch_share_basis_changes(symbol, lookback_years=5)
    return prepare_split_adjusted_eps_summary(eps, basis_changes)


@st.cache_data(ttl=21600)
def load_current_pe(symbol: str):
    pe = fetch_pe_history(symbol, lookback_days=180)
    valid = pe[pe["PER"] > 0].dropna(subset=["PER"])
    if valid.empty:
        raise ValueError("最近半年沒有正本益比資料")
    return {"value": float(valid["PER"].iloc[-1]), "date": valid.index[-1]}


@st.cache_data(ttl=21600)  # 籌碼是盤後 D-1，一天只更新一次，快取拉長到 6 小時
def load_institutional_net(symbol: str):
    return prepare_institutional_net(fetch_institutional_investors(symbol))


@st.cache_data(ttl=21600)
def load_margin_short(symbol: str):
    return prepare_margin_short(fetch_margin_short(symbol))


@st.cache_data(ttl=21600)
def load_foreign_shareholding(symbol: str):
    return prepare_foreign_shareholding(fetch_foreign_shareholding(symbol))


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


# 追蹤清單先做「只算資料、不畫圖」這一輪，因為 AI 今日重點需要前高訊號，
# 而今日重點被移到頁面最上面，得在畫任何卡片之前就先把訊號算出來。
# 下面實際畫圖的迴圈會直接重用這裡算好的 df/price/signal，不會重算一次
# （尤其 get_current_price 會打即時報價 API，重算等於多打一次）。
ticker_data = []
for item in filtered_watchlist:
    _symbol, _name = item["symbol"], item["name"]
    _df = load_history(_symbol)
    _price = get_current_price(_symbol, _df)
    _df = add_moving_averages(_df, MA_WINDOWS)
    _df = add_bollinger_bands(_df)
    _signal = front_high_signal(_df, _price)
    _ma_signals = moving_average_cross_signals(_df, _price, MA_WINDOWS)
    ticker_data.append(
        {
            "symbol": _symbol,
            "name": _name,
            "category": item["category"],
            "df": _df,
            "price": _price,
            "signal": _signal,
            "ma_signals": _ma_signals,
        }
    )

# AI 功能的密碼保護：部署到公開網址後，任何人點 AI 分析都是花「我的」API 額度，
# 設了 AI_UNLOCK_PASSWORD secret 就要輸入一次密碼才能用（本機不設則零摩擦）。
def _ai_unlock_password() -> str:
    try:
        return st.secrets.get("AI_UNLOCK_PASSWORD", "")
    except Exception:
        return ""


_ai_required_pw = _ai_unlock_password()
ai_unlocked = (not _ai_required_pw) or st.session_state.get("ai_unlocked", False)


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
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
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
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
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


def render_pe_river(result: dict):
    """本益比歷史分位河流：估值帶在下、正式收盤價在最上層。"""
    df = result["data"]
    percentiles = result["percentiles"]
    band_specs = [
        (20, "#4caf50", None),
        (40, "#62b6a7", "rgba(76,175,80,0.10)"),
        (60, "#f0b429", "rgba(240,180,41,0.10)"),
        (80, "#e8935a", "rgba(232,147,90,0.12)"),
    ]

    fig = go.Figure()
    for percentile, color, fill_color in band_specs:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[f"PE_P{percentile}"],
                name=f"P{percentile} · {percentiles[percentile]:.1f}x",
                mode="lines",
                line=dict(color=color, width=1),
                fill="tonexty" if fill_color else None,
                fillcolor=fill_color,
                hovertemplate=f"P{percentile} 估值線 %{{y:,.2f}}<extra></extra>",
            )
        )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Close"],
            name="收盤價",
            mode="lines",
            line=dict(color="#f2f0e9", width=2),
            hovertemplate="收盤價 %{y:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        height=340,
        margin=dict(l=10, r=10, t=12, b=10),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(color=TEXT_MUTED, size=10),
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_MUTED, family="monospace", size=12),
        hovermode="x unified",
        xaxis=dict(showgrid=False, color=TEXT_MUTED),
        yaxis=dict(gridcolor=GRID, color=TEXT_MUTED),
    )
    return fig


def render_revenue_trend(result: dict, months: int = 12):
    """月營收柱狀圖搭配 YoY 折線，左右軸各自保留單位。"""
    df = result["data"].tail(months)
    month_labels = df.index.strftime("%Y/%m")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=month_labels,
            y=df["revenue_100m"],
            name="月營收（億元）",
            marker_color="#5b9bd5",
            hovertemplate="%{x}<br>營收 %{y:,.1f} 億元<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=month_labels,
            y=df["yoy_pct"],
            name="YoY",
            mode="lines+markers",
            line=dict(color=ACCENT, width=2),
            marker=dict(size=5),
            hovertemplate="%{x}<br>YoY %{y:+.1f}%<extra></extra>",
        ),
        secondary_y=True,
    )
    fig.update_layout(
        height=310,
        margin=dict(l=10, r=10, t=12, b=10),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(color=TEXT_MUTED, size=10),
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_MUTED, family="monospace", size=12),
        hovermode="x unified",
        xaxis=dict(type="category", showgrid=False, color=TEXT_MUTED),
    )
    fig.update_yaxes(title_text="億元", gridcolor=GRID, color=TEXT_MUTED, secondary_y=False)
    fig.update_yaxes(title_text="YoY %", showgrid=False, color=ACCENT, secondary_y=True)
    return fig


def _metric_cards(items: list[tuple]) -> str:
    """把 (標題, 值 HTML, 值顏色) 串成一排等寬卡片的 HTML。"""
    cells = "".join(
        f"<div style='flex:1; min-width:120px; background:{GRID}55; border-radius:7px; padding:9px 13px;'>"
        f"<div style='color:{TEXT_MUTED}; font-size:12px;'>{title}</div>"
        f"<div style='color:{color}; font-size:20px;'>{value}</div></div>"
        for title, value, color in items
    )
    return f"<div style='display:flex; gap:12px; flex-wrap:wrap; margin:7px 0 4px;'>{cells}</div>"


def render_chips_tab(symbol: str):
    """籌碼面：三大法人買賣超、融資融券、外資持股比率（皆為盤後 D-1 資料）。"""

    def net_color(v):
        return "#ef5350" if v >= 0 else "#4caf50"  # 台股：買超紅、賣超綠

    # --- 三大法人買賣超 ---
    try:
        net = load_institutional_net(symbol)
        d = net["latest_date"].strftime("%Y-%m-%d")
        st.markdown(
            f"<div style='color:{ACCENT}; font-size:14px;'>三大法人買賣超（張）</div>"
            + _metric_cards([
                ("外資", f"{net['foreign_net']:+,.0f}", net_color(net["foreign_net"])),
                ("投信", f"{net['trust_net']:+,.0f}", net_color(net["trust_net"])),
                ("自營商", f"{net['dealer_net']:+,.0f}", net_color(net["dealer_net"])),
            ]),
            unsafe_allow_html=True,
        )
        streak = net["foreign_streak"]
        if streak["direction"]:
            dir_text = "買超" if streak["direction"] == "buy" else "賣超"
            dir_color = net_color(1 if streak["direction"] == "buy" else -1)
            st.markdown(
                f"<div style='background:{dir_color}18; color:{dir_color}; border:1px solid {dir_color}55; "
                f"border-radius:6px; padding:5px 10px; font-size:12px; display:inline-block; margin:2px 0 8px;'>"
                f"外資連 {streak['days']} 日{dir_text} · 近20日累計 {net['foreign_cum_20d']:+,.0f} 張</div>",
                unsafe_allow_html=True,
            )
        data = net["data"]
        labels = data.index.strftime("%m/%d")
        bar_colors = [net_color(v) for v in data["foreign"]]
        fig = go.Figure(
            go.Bar(
                x=labels, y=data["foreign"], marker_color=bar_colors,
                hovertemplate="%{x}<br>外資 %{y:+,.0f} 張<extra></extra>",
            )
        )
        fig.update_layout(
            height=220, margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT_MUTED, family="monospace", size=12),
            xaxis=dict(type="category", showgrid=False, color=TEXT_MUTED, nticks=10),
            yaxis=dict(gridcolor=GRID, color=TEXT_MUTED, title="外資淨買賣超（張）"),
        )
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        st.caption(
            f"資料源：FinMind TaiwanStockInstitutionalInvestorsBuySell，資料截至 {d}。"
            "正值買超、負值賣超；1 張＝1000 股。"
        )
    except Exception as e:
        st.info(f"三大法人買賣超目前抓不到：{e}")

    # --- 融資融券 ---
    try:
        ms = load_margin_short(symbol)
        d = ms["latest_date"].strftime("%Y-%m-%d")
        margin_chg = "" if ms["margin_change"] is None else f"（日變 {ms['margin_change']:+,.0f}）"
        short_chg = "" if ms["short_change"] is None else f"（日變 {ms['short_change']:+,.0f}）"
        st.markdown(
            f"<div style='color:{ACCENT}; font-size:14px; margin-top:12px;'>融資融券餘額（張）</div>"
            + _metric_cards([
                ("融資餘額", f"{ms['margin_balance']:,.0f} {margin_chg}", TEXT_LIGHT),
                ("融券餘額", f"{ms['short_balance']:,.0f} {short_chg}", TEXT_LIGHT),
            ]),
            unsafe_allow_html=True,
        )
        md = ms["data"]
        mlabels = md.index.strftime("%m/%d")
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Scatter(x=mlabels, y=md["margin_balance"], name="融資餘額",
                       line=dict(color="#e8935a", width=2)), secondary_y=False)
        fig.add_trace(
            go.Scatter(x=mlabels, y=md["short_balance"], name="融券餘額",
                       line=dict(color="#6ea6c9", width=2)), secondary_y=True)
        fig.update_layout(
            height=220, margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                        font=dict(color=TEXT_MUTED, size=10)),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT_MUTED, family="monospace", size=12),
            xaxis=dict(type="category", showgrid=False, color=TEXT_MUTED, nticks=10),
        )
        fig.update_yaxes(title_text="融資", gridcolor=GRID, color="#e8935a", secondary_y=False)
        fig.update_yaxes(title_text="融券", showgrid=False, color="#6ea6c9", secondary_y=True)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        st.caption(
            f"資料源：FinMind TaiwanStockMarginPurchaseShortSale，資料截至 {d}。"
            "融資餘額升＝散戶追多、融券餘額升＝空方增加。"
        )
    except Exception as e:
        st.info(f"融資融券目前抓不到：{e}")

    # --- 外資持股比率 ---
    try:
        fh = load_foreign_shareholding(symbol)
        d = fh["latest_date"].strftime("%Y-%m-%d")
        change_text = "" if fh["ratio_change"] is None else f"（區間 {fh['ratio_change']:+.2f}%）"
        st.markdown(
            f"<div style='color:{ACCENT}; font-size:14px; margin-top:12px;'>外資持股比率</div>"
            + _metric_cards([
                ("外資持股", f"{fh['foreign_ratio']:.2f}% {change_text}", TEXT_LIGHT),
            ]),
            unsafe_allow_html=True,
        )
        hd = fh["data"]
        hlabels = hd.index.strftime("%m/%d")
        fig = go.Figure(
            go.Scatter(x=hlabels, y=hd["foreign_ratio"], mode="lines",
                       line=dict(color="#e8935a", width=2),
                       hovertemplate="%{x}<br>外資持股 %{y:.2f}%<extra></extra>")
        )
        fig.update_layout(
            height=200, margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT_MUTED, family="monospace", size=12),
            xaxis=dict(type="category", showgrid=False, color=TEXT_MUTED, nticks=8),
            yaxis=dict(gridcolor=GRID, color=TEXT_MUTED, title="%"),
        )
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        st.caption(
            f"資料源：FinMind TaiwanStockShareholding，資料截至 {d}。外資總持股占已發行股數比例。"
        )
    except Exception as e:
        st.info(f"外資持股比率目前抓不到：{e}")


def render_fundamentals_tab(symbol: str):
    """基本面：月營收趨勢、實際 EPS 與估值、本益比河流圖（河流圖較重，放在子開關後）。"""
    try:
        revenue_result = load_revenue_trend(symbol)
        period = revenue_result["latest_period"].strftime("%Y/%m")
        mom = revenue_result["mom_pct"]
        yoy = revenue_result["yoy_pct"]
        mom_text = "N/A" if mom is None else f"{mom:+.1f}%"
        yoy_text = "N/A" if yoy is None else f"{yoy:+.1f}%"
        mom_color = TEXT_MUTED if mom is None else ("#ef5350" if mom >= 0 else "#4caf50")
        yoy_color = TEXT_MUTED if yoy is None else ("#ef5350" if yoy >= 0 else "#4caf50")
        announcement = revenue_result["announcement_date"]
        announcement_text = announcement.strftime("%Y-%m-%d") if pd.notna(announcement) else "未提供"
        st.markdown(
            f"<div style='color:{ACCENT}; font-size:14px;'>月營收趨勢</div>"
            + _metric_cards([
                (f"{period} 營收", f"{revenue_result['latest_revenue_100m']:,.1f} 億元", TEXT_LIGHT),
                ("月增率 MoM", mom_text, mom_color),
                ("年增率 YoY", yoy_text, yoy_color),
            ]),
            unsafe_allow_html=True,
        )
        revenue_range = st.segmented_control(
            "營收趨勢範圍", options=["3個月", "6個月", "12個月"],
            default="12個月", key=f"revenue_range_{symbol}",
        )
        revenue_months = int((revenue_range or "12個月").replace("個月", ""))
        st.plotly_chart(
            render_revenue_trend(revenue_result, months=revenue_months),
            width="stretch", config={"displayModeBar": False},
        )
        st.caption(
            f"資料源：FinMind TaiwanStockMonthRevenue；實際營收月份 {period}，"
            f"資料建立／記錄日期 {announcement_text}。營收單位為新台幣億元。"
        )
    except Exception as e:
        st.info(f"月營收趨勢目前抓不到：{e}")

    try:
        eps_result = load_eps_summary(symbol)
        eps_date = eps_result["latest_date"]
        quarter = f"{eps_date.year} Q{(eps_date.month - 1) // 3 + 1}"
        eps_yoy = eps_result["quarterly_yoy_pct"]
        eps_yoy_text = "N/A" if eps_yoy is None else f"{eps_yoy:+.1f}%"
        eps_yoy_color = TEXT_MUTED if eps_yoy is None else ("#ef5350" if eps_yoy >= 0 else "#4caf50")
        try:
            current_pe = load_current_pe(symbol)
            pe_text = f"{current_pe['value']:.1f}x"
            pe_date_text = current_pe["date"].strftime("%Y-%m-%d")
        except Exception:
            pe_text = "N/A"
            pe_date_text = "無正 PE 資料"
        st.markdown(
            f"<div style='color:{ACCENT}; font-size:14px; margin-top:12px;'>實際獲利與估值</div>"
            + _metric_cards([
                (f"{quarter} 單季 EPS", f"{eps_result['latest_eps']:.2f} 元", TEXT_LIGHT),
                ("近四季實際 EPS", f"{eps_result['ttm_eps']:.2f} 元", TEXT_LIGHT),
                ("單季 EPS YoY", eps_yoy_text, eps_yoy_color),
                ("目前官方 PE", pe_text, TEXT_LIGHT),
            ]),
            unsafe_allow_html=True,
        )
        st.caption(
            f"EPS 資料源：FinMind TaiwanStockFinancialStatements，最新財報季度 {quarter}；"
            f"PE 資料源：TaiwanStockPER，資料日期 {pe_date_text}。以上皆為已公告實際值。"
        )
        for adjustment in eps_result["basis_adjustments"]:
            factor = float(adjustment["basis_factor"])
            action_date = pd.Timestamp(adjustment["date"]).strftime("%Y-%m-%d")
            ratio_text = f"÷ {1 / factor:g}" if factor < 1 else f"× {factor:g}"
            st.caption(
                f"↳ 已依 {action_date}「{adjustment['type']}」將事件日前 EPS {ratio_text}，"
                "統一成目前股數基準後再計算 TTM 與 YoY。"
            )
    except Exception as e:
        st.info(f"實際 EPS 摘要目前抓不到：{e}")

    if st.toggle("顯示本益比河流圖", key=f"show_pe_river_{symbol}"):
        try:
            river = load_pe_river(symbol)
            latest_date = river["latest_date"].strftime("%Y-%m-%d")
            st.markdown(
                f"<div style='display:flex; gap:24px; align-items:baseline; margin-top:6px;'>"
                f"<span style='color:{ACCENT}; font-size:14px;'>本益比歷史分位河流</span>"
                f"<span style='font-size:13px;'>目前 PE {river['current_pe']:.1f}x</span>"
                f"<span style='color:{TEXT_MUTED}; font-size:12px;'>"
                f"近5年百分位 {river['current_percentile']:.0f}% · 資料截至 {latest_date}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.plotly_chart(render_pe_river(river), width="stretch", config={"displayModeBar": False})
            st.caption(
                "資料源：FinMind TaiwanStockPER。P20／P40／P60／P80 是此股票近5年正本益比的"
                "歷史分位數；估值線＝每日反推近四季 EPS × 各分位 PE，並非目標價。"
            )
            for adjustment in river["basis_adjustments"]:
                factor = float(adjustment["basis_factor"])
                action_date = pd.Timestamp(adjustment["date"]).strftime("%Y-%m-%d")
                price_action = f"÷ {1 / factor:g}" if factor < 1 else f"× {factor:g}"
                st.caption(
                    f"↳ 河流圖已依 {action_date}「{adjustment['type']}」將事件日前價格 "
                    f"{price_action}；官方 PE 比率本身維持不變，避免重複調整。"
                )
        except Exception as e:
            st.info(f"本益比河流圖目前不適用：{e}")


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
                    note = spec["note"]
                    if spec["key"] == "foreign_futures":
                        latest_data_date = pd.Timestamp(series.index[-1]).strftime("%Y-%m-%d")
                        note += f"；最新資料日 {latest_data_date}，採盤後增量快取"
                    st.markdown(
                        f"<div style='color:{TEXT_MUTED}; font-size:10px;'>{note}</div>",
                        unsafe_allow_html=True,
                    )
            except Exception as e:
                st.markdown(
                    f"<div style='color:{TEXT_MUTED}; font-size:12px;'>{spec['label']}：暫時抓不到（{e}）</div>",
                    unsafe_allow_html=True,
                )


def render_technical_tab(symbol, df, display_df, latest, signal, ma_signals):
    """技術面：K 線（疊布林、均線）。規則式警告徽章與前高線已移除，改由 AI 綜合分析詮釋。"""
    dates_str = display_df.index.strftime("%Y-%m-%d")  # 類別軸用字串日期，天然跳過週末不留空隙
    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=dates_str, open=display_df["Open"], high=display_df["High"],
            low=display_df["Low"], close=display_df["Close"],
            name="K線", showlegend=False, line=dict(width=1),
            increasing_line_color="#ef5350", increasing_fillcolor="#ef5350",
            decreasing_line_color="#4caf50", decreasing_fillcolor="#4caf50",
        )
    )
    fig.add_trace(
        go.Scatter(x=dates_str, y=display_df["BB_lower"], name="布林下軌",
                   line=dict(color="#5f5e5a", width=1, dash="dot"), showlegend=False)
    )
    fig.add_trace(
        go.Scatter(x=dates_str, y=display_df["BB_upper"], name="布林通道",
                   line=dict(color="#5f5e5a", width=1, dash="dot"),
                   fill="tonexty", fillcolor="rgba(95,94,90,0.12)")
    )
    for w in MA_WINDOWS:
        ma_value = latest[f"MA{w}"]
        label = f"MA{w} {ma_value:.1f}" if pd.notna(ma_value) else f"MA{w} N/A"
        fig.add_trace(
            go.Scatter(x=dates_str, y=display_df[f"MA{w}"], name=label,
                       line=dict(color=MA_COLORS[w], width=1.3))
        )
    fig.update_layout(
        height=300, margin=dict(l=8, r=8, t=8, b=8),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(color=TEXT_MUTED, size=12)),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_LIGHT, family="monospace", size=12),
        hovermode="x unified",
        xaxis=dict(type="category", showgrid=False, color=TEXT_MUTED,
                   tickfont=dict(size=12), nticks=8),
        yaxis=dict(gridcolor=GRID, color=TEXT_MUTED, tickfont=dict(size=12)),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    for adjustment in df.attrs.get("share_basis_adjustments", []):
        factor = float(adjustment["basis_factor"])
        action_date = pd.Timestamp(adjustment["date"]).strftime("%Y-%m-%d")
        if factor < 1:
            price_action, volume_action = f"÷ {1 / factor:g}", f"× {1 / factor:g}"
        else:
            price_action, volume_action = f"× {factor:g}", f"÷ {factor:g}"
        st.caption(
            f"↳ {action_date}「{adjustment['type']}」：事件日前價格已 {price_action}、"
            f"成交量已 {volume_action} 還原為目前單位基準；圖上的落差不計為漲跌。"
        )


def render_ai_analysis(symbol, name, df, latest, signal, ma_signals, price, change_pct):
    """個股 AI 綜合分析：只在按鈕點下時才呼叫 Opus（刷新頁面不會重跑），結果存 session_state。"""
    state_key = f"ai_analysis_{symbol}"
    total_spend = load_total_spend()

    head_col, cost_col = st.columns([3, 1])
    with head_col:
        st.markdown(
            f"<div style='color:{ACCENT}; font-size:15px; font-weight:600;'>🤖 AI 綜合分析</div>"
            f"<div style='color:{TEXT_MUTED}; font-size:11px;'>Opus 仔細研讀技術／基本／籌碼三面向後給操作建議（按鈕才產生，刷新不會）</div>",
            unsafe_allow_html=True,
        )
    with cost_col:
        frac = min(total_spend / BUDGET_USD, 1.0) if BUDGET_USD else 0.0
        st.markdown(
            f"<div style='text-align:right; color:{TEXT_MUTED}; font-size:11px;'>AI 花費</div>"
            f"<div style='text-align:right; font-size:12px;'>${total_spend:.3f} / ${BUDGET_USD:.0f}</div>",
            unsafe_allow_html=True,
        )
        st.progress(frac)

    if _ai_required_pw and not ai_unlocked:
        pw = st.text_input("🔒 AI 分析需要密碼（圖表不用）", type="password", key="ai_pw_input",
                           placeholder="輸入密碼以解鎖 AI 分析")
        if pw == _ai_required_pw:
            st.session_state.ai_unlocked = True
            st.rerun()
        elif pw:
            st.markdown(f"<div style='color:#e06c75; font-size:12px;'>密碼錯誤</div>", unsafe_allow_html=True)

    if st.button(f"🤖 分析 {name}", disabled=not ai_unlocked, key=f"ai_btn_{symbol}"):
        with st.spinner("AI 正在研讀基本面／技術面／籌碼面…"):
            try:
                tech = {
                    "ma": [f"MA{w} {latest[f'MA{w}']:.1f}" for w in MA_WINDOWS if pd.notna(latest[f"MA{w}"])],
                    "signals": ([signal["message"]] if signal else []) + [s["message"] for s in ma_signals],
                    "bollinger": (f"上軌 {latest['BB_upper']:.1f} / 下軌 {latest['BB_lower']:.1f}"
                                  if pd.notna(latest.get("BB_upper")) else None),
                }
                fund = None
                if is_company_fundamentals_applicable(symbol):
                    fund = {}
                    try:
                        r = load_revenue_trend(symbol)
                        fund["revenue"] = {
                            "period": r["latest_period"].strftime("%Y/%m"),
                            "latest_100m": r["latest_revenue_100m"],
                            "mom": None if r["mom_pct"] is None else f"{r['mom_pct']:+.1f}%",
                            "yoy": None if r["yoy_pct"] is None else f"{r['yoy_pct']:+.1f}%",
                        }
                    except Exception:
                        pass
                    try:
                        e = load_eps_summary(symbol)
                        fund["eps"] = {
                            "quarter": f"{e['latest_date'].year} Q{(e['latest_date'].month - 1) // 3 + 1}",
                            "latest": e["latest_eps"], "ttm": e["ttm_eps"],
                            "yoy": None if e["quarterly_yoy_pct"] is None else f"{e['quarterly_yoy_pct']:+.1f}%",
                        }
                    except Exception:
                        pass
                    try:
                        fund["pe"] = {"value": load_current_pe(symbol)["value"]}
                    except Exception:
                        pass
                chips = None
                if is_institutional_applicable(symbol):
                    chips = {}
                    try:
                        n = load_institutional_net(symbol)
                        chips["institutional"] = {
                            "foreign": n["foreign_net"], "trust": n["trust_net"], "dealer": n["dealer_net"],
                            "streak": n["foreign_streak"], "cum20": n["foreign_cum_20d"],
                        }
                    except Exception:
                        pass
                    try:
                        m = load_margin_short(symbol)
                        chips["margin"] = {"margin": m["margin_balance"], "short": m["short_balance"]}
                    except Exception:
                        pass
                    try:
                        chips["foreign_holding"] = load_foreign_shareholding(symbol)["foreign_ratio"]
                    except Exception:
                        pass

                ctx = build_stock_context(name, symbol, price, change_pct, tech, fund, chips)
                res = generate_stock_analysis(ctx)
                add_spend(res["cost_usd"])
                st.session_state[state_key] = {
                    "text": res["text"], "cost": res["cost_usd"],
                    "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "error": None,
                }
            except Exception as e:
                st.session_state[state_key] = {"text": None, "error": str(e)}
        st.rerun()

    result = st.session_state.get(state_key)
    if result and result.get("error"):
        st.info(f"AI 分析暫時產生不了：{result['error']}")
    elif result and result.get("text"):
        st.markdown(result["text"])
        st.caption(
            f"產生時間 {result['at']} · 這次花費 ${result['cost']:.4f} · "
            "本分析由 AI 生成、僅供參考，不構成投資建議"
        )
    else:
        st.caption("尚未產生。點上面的按鈕，讓 AI 讀完三面向最新資料後給你操作建議。")


# 標的篩選緊接在警示指標之後，讓「市場警示 → 選擇標的 → K 線」形成連續閱讀順序。
with st.container(border=True):
    st.markdown(
        f"<div style='color:{ACCENT}; font-size:14px; margin-bottom:4px;'>標的檢視</div>",
        unsafe_allow_html=True,
    )
    category_col, range_col = st.columns([1, 2])
    with category_col:
        st.selectbox(
            "產業篩選",
            options=["全部", *categories],
            key="category_filter",
        )
    with range_col:
        st.segmented_control(
            "時間範圍",
            options=list(RANGE_OPTIONS.keys()),
            default="3個月",
            key="range_filter",
        )
    st.caption(f"目前顯示 {len(filtered_watchlist)} 個標的")


# MA 線刻意避開紅/綠（留給K線漲跌用），深色底上要夠亮才看得清楚
MA_COLORS = {5: "#5b9bd5", 10: "#a89ef0", 20: "#f0b429", 60: "#c4c1b8"}

# 「今日」沒有放進來：我們的歷史資料是日線（一天一根K棒），沒有分鐘級盤中資料，
# 「今日」放進日K圖只會看到1根棒子沒有意義。之後若要做盤中圖是另一個功能。
def _stock_change_pct(t) -> float:
    """個股相對前一收盤的漲跌%（休市中即時價=最後一筆時，前收要往前抓一天）。"""
    df, price = t["df"], t["price"]
    if abs(price - float(df["Close"].iloc[-1])) < 0.01:
        prev_close = float(df["Close"].iloc[-2])
    else:
        prev_close = float(df["Close"].iloc[-1])
    return (price - prev_close) / prev_close * 100 if prev_close else 0.0


# ── 個股清單（可點選）──────────────────────────────────────────────
# 一眼掃完所有標的；點一列 → 下方顯示該檔「技術面／籌碼面／基本面」三欄並排。
list_rows = []
for t in ticker_data:
    list_rows.append(
        {
            "名稱": t["name"],
            "代號": t["symbol"],
            "產業": t["category"],
            "現價": t["price"],
            "漲跌%": _stock_change_pct(t),
        }
    )
list_df = pd.DataFrame(list_rows)

st.caption("點選任一列，看該檔的技術面／籌碼面／基本面三欄並排詳情")
list_event = st.dataframe(
    list_df,
    hide_index=True,
    width="stretch",
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        "現價": st.column_config.NumberColumn(format="%.2f"),
        "漲跌%": st.column_config.NumberColumn(format="%+.2f%%"),
    },
    key="stock_list",
)
selected_rows = list_event.selection["rows"] if list_event and list_event.selection else []
selected_idx = selected_rows[0] if selected_rows else 0  # 預設看清單第一檔

# ── 選中個股的三欄並排詳情 ──────────────────────────────────────────
sel = ticker_data[selected_idx]
symbol, name, category, df = sel["symbol"], sel["name"], sel["category"], sel["df"]
price, signal, ma_signals = sel["price"], sel["signal"], sel["ma_signals"]
latest = df.iloc[-1]
n = RANGE_OPTIONS[selected_range]
display_df = df if n is None else df.tail(n)
change_pct = _stock_change_pct(sel)
change_color = "#ef5350" if change_pct >= 0 else "#4caf50"  # 台股：紅漲綠跌
arrow = "▲" if change_pct >= 0 else "▼"

with st.container(border=True):
    st.markdown(
        f"<span style='color:{TEXT_LIGHT}; font-size:17px;'>{name}</span> "
        f"<span style='color:{TEXT_MUTED}; font-size:13px;'>{symbol}</span> "
        f"<span style='color:{ACCENT}; font-size:11px; border:1px solid {ACCENT}66; "
        f"border-radius:10px; padding:1px 7px;'>{category}</span>"
        f"<span style='font-size:30px; font-weight:500; margin-left:14px;'>{price:,.2f}</span> "
        f"<span style='color:{change_color}; font-size:16px;'>{arrow} {abs(change_pct):.2f}%</span>",
        unsafe_allow_html=True,
    )

    # AI 綜合分析（按鈕觸發）放在三面向之前，讓使用者一選股就能一鍵拿到操作建議。
    render_ai_analysis(symbol, name, df, latest, signal, ma_signals, price, change_pct)

    # 三列堆疊、每列滿版（圖表都 width="stretch" 撐滿整列）；順序：技術→基本→籌碼。
    def _face_header(title):
        st.markdown(
            f"<div style='color:{ACCENT}; font-size:15px; font-weight:600; "
            f"border-bottom:1px solid {GRID}; padding-bottom:5px; margin:16px 0 8px;'>{title}</div>",
            unsafe_allow_html=True,
        )

    # 第一列：技術面
    _face_header("技術面")
    render_technical_tab(symbol, df, display_df, latest, signal, ma_signals)

    # 第二列：基本面
    _face_header("基本面")
    if is_company_fundamentals_applicable(symbol):
        render_fundamentals_tab(symbol)
    else:
        st.caption("個股基本面與估值圖僅適用一般公司；指數與 ETF 不套用月營收／EPS／PE 模型。")

    # 第三列：籌碼面
    _face_header("籌碼面")
    if is_institutional_applicable(symbol):
        render_chips_tab(symbol)
    else:
        st.caption("指數沒有個股籌碼；三大法人／融資融券／外資持股為個股與 ETF 適用。")

