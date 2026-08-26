"""保存每檔股票最後一次成功的 AI 分析。

Streamlit 的 ``session_state`` 足以應付一般 rerun，但換瀏覽器或重建 session 後會消失。
這裡用一個被 ``*.db`` 規則排除的本機 SQLite 檔再保存一層；Streamlit Cloud 重新部署
可能會清除容器檔案，因此 session 與資料庫任一層可用時都能讀回最近結果。
"""

import os
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo


TAIPEI_TZ = ZoneInfo("Asia/Taipei")
DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".ai_analysis_history.db",
)


def taipei_now_text() -> str:
    """回傳適合直接顯示的台北時間。"""
    return datetime.now(TAIPEI_TZ).strftime("%Y-%m-%d %H:%M:%S")


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS latest_analysis (
            symbol TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            text TEXT NOT NULL,
            cost_usd REAL NOT NULL,
            analyzed_at TEXT NOT NULL
        )
        """
    )


def save_latest_analysis(
    symbol: str,
    name: str,
    text: str,
    cost_usd: float,
    analyzed_at: str | None = None,
    db_path: str = DEFAULT_DB_PATH,
) -> dict:
    """新增或覆蓋某檔股票最後一次成功分析，並回傳可直接放進畫面的資料。"""
    record = {
        "symbol": symbol,
        "name": name,
        "text": text,
        "cost": float(cost_usd),
        "at": analyzed_at or taipei_now_text(),
        "error": None,
    }
    with sqlite3.connect(db_path) as conn:
        _ensure_table(conn)
        conn.execute(
            """
            INSERT INTO latest_analysis (symbol, name, text, cost_usd, analyzed_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                name = excluded.name,
                text = excluded.text,
                cost_usd = excluded.cost_usd,
                analyzed_at = excluded.analyzed_at
            """,
            (symbol, name, text, record["cost"], record["at"]),
        )
    return record


def load_latest_analysis(symbol: str, db_path: str = DEFAULT_DB_PATH) -> dict | None:
    """讀取某檔股票最後一次成功分析；沒有紀錄或資料庫尚未建立時回傳 ``None``。"""
    if not os.path.exists(db_path):
        return None
    with sqlite3.connect(db_path) as conn:
        _ensure_table(conn)
        row = conn.execute(
            """
            SELECT symbol, name, text, cost_usd, analyzed_at
            FROM latest_analysis
            WHERE symbol = ?
            """,
            (symbol,),
        ).fetchone()
    if row is None:
        return None
    return {
        "symbol": row[0],
        "name": row[1],
        "text": row[2],
        "cost": float(row[3]),
        "at": row[4],
        "error": None,
    }
