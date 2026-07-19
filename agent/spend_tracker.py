"""本地累積花費追蹤。

用一個小 JSON 檔記「目前總共花了多少錢」，而不是放進 st.session_state——
session_state 只要重新整理伺服器（或重新部署）就會歸零，沒辦法真的追蹤到「總共」。
"""
import json
import os

SPEND_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".spend_tracker.json")


def load_total_spend() -> float:
    if not os.path.exists(SPEND_FILE):
        return 0.0
    with open(SPEND_FILE) as f:
        return json.load(f).get("total_spend_usd", 0.0)


def add_spend(amount: float) -> float:
    """累加一筆花費，回傳累加後的總額。"""
    total = load_total_spend() + amount
    with open(SPEND_FILE, "w") as f:
        json.dump({"total_spend_usd": total}, f)
    return total
