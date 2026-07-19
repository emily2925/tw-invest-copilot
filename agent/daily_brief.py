"""AI 今日重點摘要 — OpenAI Agents SDK + LiteLLM 接 Claude Sonnet 5。

這是這個週末唯一真正練到 agent framework 的地方：其餘模組都是決定性的資料
處理/規則判斷，這裡才是「把算好的訊號丟給 LLM，生成一段自然語言摘要」。

用 openai-agents[litellm] 的 LitellmModel 指定 anthropic/claude-sonnet-5，
讓你可以用 OpenAI SDK 的寫法，但底層實際呼叫 Claude（不是 Gemini/GPT-4o-mini）。
"""
import os

from agents import Agent, Runner, set_tracing_disabled
from agents.extensions.models.litellm_model import LitellmModel
from dotenv import load_dotenv

load_dotenv()
set_tracing_disabled(True)  # 沒有設定 OPENAI_API_KEY，追蹤功能用不到，關掉避免噪音警告

MODEL_NAME = "anthropic/claude-sonnet-5"

# Claude Sonnet 5 優惠價（2026-08-31 前），過了這個日期要改回原價 $3.00 / $15.00
INPUT_PRICE_PER_MILLION = 2.00
OUTPUT_PRICE_PER_MILLION = 10.00

INSTRUCTIONS = """你是台股投資助理，根據使用者提供的今日訊號資料，用繁體中文寫一段簡短的
「今日重點」摘要（3-5句話，不要條列、不要冗長）。

規則：
- 只根據提供的資料做摘要，不要編造資料中沒有的內容
- 提供的訊號可能不齊全（某些資料當下抓不到），這是正常的：就用「手上有的資料」
  照樣寫出重點，不要因為缺了某幾項就拒絕產出或整段都在講「資料不足」。頂多用一句話
  輕描淡寫帶過缺哪項即可。
- 語氣中性、務實，不要過度樂觀或悲觀
- 如果有前高跌破訊號的標的，點出來
- 如果外資空單、台指夜盤、費半、匯率有明顯異常方向，一併提到
- 最後不需要加免責聲明，畫面上已經有了
"""


def build_signal_summary(
    overnight: dict | None = None,
    foreign_futures_current: float | None = None,
    foreign_futures_change_pct: float | None = None,
    twd_current: float | None = None,
    sox_current: float | None = None,
    sox_change_pct: float | None = None,
    front_high_signals: list[dict] | None = None,
) -> str:
    """把算好的訊號整理成給 LLM 看的文字（不是給人看的，所以直接、資訊密度高就好）。

    每一項都是可選的：當下抓不到的資料源就傳 None，這裡只會列出「有值」的項目，
    讓 AI 能根據手上有的資料照樣產出摘要，而不是缺一項就整段失敗。
    """
    lines = []
    if overnight is not None:
        lines.append(
            f"台指夜盤：收 {overnight['close']:.0f}，{overnight['change']}"
            f"（{overnight['change_pct']:+.2f}%），{overnight['sentiment']}"
        )
    if foreign_futures_current is not None:
        change_str = (
            f"，近1個月變化 {foreign_futures_change_pct:+.2f}%"
            if foreign_futures_change_pct is not None else ""
        )
        lines.append(
            f"外資台指期未平倉淨額：{foreign_futures_current:,.0f} 口"
            f"（負值代表淨空單{change_str}）"
        )
    if twd_current is not None:
        lines.append(f"台幣兌美元：{twd_current:.3f}")
    if sox_current is not None:
        change_str = (
            f"（近1個月變化 {sox_change_pct:+.2f}%）"
            if sox_change_pct is not None else ""
        )
        lines.append(f"費城半導體指數：{sox_current:,.0f}{change_str}")

    if front_high_signals:
        lines.append("前高跌破訊號：")
        for s in front_high_signals:
            lines.append(f"- {s['name']}：{s['message']}")
    elif front_high_signals is not None:
        lines.append("前高跌破訊號：目前追蹤清單中沒有標的觸發")

    if not lines:
        return "（今日各項訊號資料當下都暫時抓不到，請就這個情況簡短說明一句即可）"
    return "\n".join(lines)


def generate_daily_brief(signal_text: str) -> dict:
    """呼叫一次 agent，回傳文字＋這次呼叫的 token 用量／花費（給按鈕觸發時做花費追蹤用）。"""
    agent = Agent(name="daily_brief", instructions=INSTRUCTIONS, model=LitellmModel(model=MODEL_NAME))
    result = Runner.run_sync(agent, signal_text)
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


if __name__ == "__main__":
    demo_signals = build_signal_summary(
        overnight={"close": 43481.0, "change": "▲877", "change_pct": 2.06, "sentiment": "大漲"},
        foreign_futures_current=-86189.0,
        foreign_futures_change_pct=26.12,
        twd_current=32.365,
        sox_current=11673.89,
        sox_change_pct=5.3,
        front_high_signals=[
            {"name": "台積電", "message": "跌破前高 2425.0 了，可能是買點"},
            {"name": "0050", "message": "跌破前高 107.6 了，可能是買點"},
        ],
    )
    print("=== 丟給 agent 的訊號摘要 ===")
    print(demo_signals)
    print()
    print("=== AI 生成的今日重點 ===")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("（沒有設定 ANTHROPIC_API_KEY，跳過實際呼叫）")
    else:
        result = generate_daily_brief(demo_signals)
        print(result["text"])
        print(f"\n(input={result['input_tokens']} output={result['output_tokens']} tokens, "
              f"cost=${result['cost_usd']:.4f})")
