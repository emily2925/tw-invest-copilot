"""個股 AI 綜合分析 — OpenAI Agents SDK + LiteLLM 接 Claude Opus 5（medium 推理強度）。

把某一檔個股「最新」的技術面／基本面／籌碼面資料餵給一位「三面向都很專業的資深分析師」，
請它先分別給出三面向看法（每個判斷附簡要邏輯），最後給明確的操作建議：買/賣/觀望、
進出場時機、預計持有時間、預期報酬%。這是整個專案真正用到 agent framework 的地方。

模型用 anthropic/claude-opus-5（比 daily brief 的 Sonnet 更強，適合這種需要仔細研讀多面向
資料下判斷的任務），推理強度 medium 平衡品質與成本。輸出要求精簡以節省 token。
"""
import os

from agents import Agent, ModelSettings, Runner, set_tracing_disabled
from agents.extensions.models.litellm_model import LitellmModel
from dotenv import load_dotenv

load_dotenv()
set_tracing_disabled(True)

MODEL_NAME = "anthropic/claude-opus-5"

# Claude Opus 5 計價（$5 / $25 per 1M tokens）。medium 推理會產生 thinking token，
# 一併算進 output_tokens 由 API 回報，所以成本估算會涵蓋到。
INPUT_PRICE_PER_MILLION = 5.00
OUTPUT_PRICE_PER_MILLION = 25.00

INSTRUCTIONS = """你是一位對台股「基本面、技術面、籌碼面」都非常專業的資深分析師。
使用者會提供某一檔個股「最新」的三面向資料，請你仔細研讀後給出操作建議。

務必依下列結構用繁體中文輸出，先分述三面向、最後才下結論；每個判斷都要附「一句」簡要邏輯，
用字精簡有效率、重點清楚，不要長篇大論：

【基本面】你的看法 ＋ 依據（營收成長、EPS、本益比位階等）
【技術面】你的看法 ＋ 依據（均線排列、前高支撐、布林位置、均線穿越等）
【籌碼面】你的看法 ＋ 依據（三大法人買賣超、外資連續動向、融資融券、外資持股）
【結論】綜合以上，明確給出：
- 操作建議：買進 / 賣出 / 觀望（擇一，並一句話說為什麼）
- 進出場時機：具體條件（例如「跌破 XXX 元」「站上 20MA」「外資轉買超」）
- 預計持有時間：大約多久（例如數天／數週／數月）
- 預期報酬：大約 +X%（或提示下檔風險 -X%），並說明這個數字怎麼來的

規則：
- 只根據提供的資料判斷，不要編造沒有的數據
- 某一面向資料不足時，明講「該面向資料不足」，但仍就其他面向給出結論，不要整段拒絕
- 這是你的分析觀點，不是保證；不用寫免責聲明（畫面上已有）
"""


def _fmt_num(v, suffix="", plus=False):
    if v is None:
        return "N/A"
    return (f"{v:+,.0f}" if plus else f"{v:,.0f}") + suffix


def build_stock_context(
    name: str,
    symbol: str,
    price: float | None = None,
    change_pct: float | None = None,
    technical: dict | None = None,
    fundamental: dict | None = None,
    chips: dict | None = None,
) -> str:
    """把一檔股票的三面向資料整理成給 LLM 看的密集文字（缺的面向就跳過）。"""
    lines = [f"股票：{name}（{symbol}）"]
    if price is not None:
        chg = "" if change_pct is None else f"，今日 {change_pct:+.2f}%"
        lines.append(f"現價：{price:,.2f}{chg}")

    lines.append("\n[技術面]")
    if technical:
        if technical.get("ma"):
            lines.append("均線：" + "、".join(technical["ma"]))
        for msg in technical.get("signals", []):
            lines.append(f"- {msg}")
        if technical.get("bollinger"):
            lines.append(f"布林通道：{technical['bollinger']}")
        if not technical.get("ma") and not technical.get("signals"):
            lines.append("（無明顯技術訊號）")
    else:
        lines.append("（技術面資料不足）")

    lines.append("\n[基本面]")
    if fundamental:
        rev = fundamental.get("revenue")
        if rev:
            lines.append(
                f"月營收：{rev.get('period')} {rev.get('latest_100m'):,.1f} 億元，"
                f"MoM {rev.get('mom')}，YoY {rev.get('yoy')}"
            )
        eps = fundamental.get("eps")
        if eps:
            lines.append(
                f"EPS：{eps.get('quarter')} 單季 {eps.get('latest'):.2f} 元、"
                f"近四季 {eps.get('ttm'):.2f} 元、單季 YoY {eps.get('yoy')}"
            )
        pe = fundamental.get("pe")
        if pe:
            lines.append(
                f"本益比：目前 {pe.get('value'):.1f}x"
                + (f"，近5年百分位 {pe.get('percentile'):.0f}%" if pe.get("percentile") is not None else "")
            )
        if not rev and not eps and not pe:
            lines.append("（基本面資料不足）")
    else:
        lines.append("（基本面資料不足，可能是指數或 ETF）")

    lines.append("\n[籌碼面]")
    if chips:
        net = chips.get("institutional")
        if net:
            streak = net.get("streak") or {}
            streak_txt = ""
            if streak.get("direction"):
                d = "買超" if streak["direction"] == "buy" else "賣超"
                streak_txt = f"，外資連 {streak['days']} 日{d}"
            lines.append(
                f"三大法人（張）：外資 {_fmt_num(net.get('foreign'), plus=True)}、"
                f"投信 {_fmt_num(net.get('trust'), plus=True)}、自營 {_fmt_num(net.get('dealer'), plus=True)}"
                f"{streak_txt}，近20日外資累計 {_fmt_num(net.get('cum20'), plus=True)}"
            )
        ms = chips.get("margin")
        if ms:
            lines.append(
                f"融資餘額 {_fmt_num(ms.get('margin'))} 張、融券餘額 {_fmt_num(ms.get('short'))} 張"
            )
        fh = chips.get("foreign_holding")
        if fh is not None:
            lines.append(f"外資持股比率 {fh:.2f}%")
        if not net and not ms and fh is None:
            lines.append("（籌碼面資料不足）")
    else:
        lines.append("（籌碼面資料不足，指數無個股籌碼）")

    return "\n".join(lines)


def generate_stock_analysis(context_text: str) -> dict:
    """呼叫一次分析師 agent，回傳分析文字＋這次的 token 用量／花費。"""
    agent = Agent(
        name="stock_analyst",
        instructions=INSTRUCTIONS,
        model=LitellmModel(model=MODEL_NAME),
        model_settings=ModelSettings(reasoning_effort="medium"),
    )
    result = Runner.run_sync(agent, context_text)
    usage = result.context_wrapper.usage
    cost_usd = (
        usage.input_tokens * INPUT_PRICE_PER_MILLION
        + usage.output_tokens * OUTPUT_PRICE_PER_MILLION
    ) / 1_000_000
    return {
        "text": result.final_output,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cost_usd": cost_usd,
    }
