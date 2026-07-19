"""TAIFEX 外資台指期未平倉資料與增量檔案快取。"""
from datetime import date, timedelta
from pathlib import Path
from tempfile import gettempdir
from typing import Callable
from uuid import uuid4

import pandas as pd
import requests
from bs4 import BeautifulSoup

TAIFEX_FUT_CONTRACTS_URL = "https://www.taifex.com.tw/cht/3/futContractsDate"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEED_CACHE_PATH = PROJECT_ROOT / "data_cache" / "foreign_futures.csv"
RUNTIME_CACHE_PATH = Path(gettempdir()) / "tw-invest-copilot-foreign-futures.csv"


def fetch_foreign_tx_net_oi(query_date: date) -> float | None:
    """抓單一天外資 TXF 未平倉多空淨額；非交易日或尚未公告時回傳 None。"""
    payload = {
        "queryType": "2", "goDay": "", "doQuery": "1", "dateaddcnt": "",
        "commodityId": "TXF", "queryDate": query_date.strftime("%Y/%m/%d"),
    }
    resp = requests.post(
        TAIFEX_FUT_CONTRACTS_URL,
        data=payload,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=10,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    table = soup.find("table", class_="table_f")
    if table is None or table.find("tbody") is None:
        return None
    for row in table.find("tbody").find_all("tr"):
        cells = [cell.get_text(strip=True) for cell in row.find_all("td")]
        if cells and cells[0] == "外資":
            return float(cells[11].replace(",", ""))
    return None


def _read_cache(*paths: Path) -> pd.DataFrame:
    frames = []
    seen = set()
    for path in paths:
        resolved = path.resolve()
        if resolved in seen or not path.exists():
            continue
        seen.add(resolved)
        try:
            frame = pd.read_csv(path)
            frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
            frame["Close"] = pd.to_numeric(frame["Close"], errors="coerce")
            frames.append(frame.dropna(subset=["date", "Close"])[["date", "Close"]])
        except Exception:
            continue
    if not frames:
        return pd.DataFrame(columns=["Close"], index=pd.DatetimeIndex([], name="date"))
    merged = pd.concat(frames, ignore_index=True).drop_duplicates("date", keep="last")
    return merged.sort_values("date").set_index("date")


def _write_cache(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{uuid4().hex}.tmp")
    df.rename_axis("date").to_csv(temporary)
    temporary.replace(path)


def update_foreign_futures_cache(
    *,
    cache_path: Path = RUNTIME_CACHE_PATH,
    seed_path: Path = SEED_CACHE_PATH,
    as_of: date | None = None,
    keep_trading_days: int = 25,
    fetcher: Callable[[date], float | None] = fetch_foreign_tx_net_oi,
) -> pd.DataFrame:
    """讀取既有月份，只補到 D-1 為止的缺少日期並寫回。

    首頁不查當日資料，因為法人未平倉屬盤後資料；排程與執行期共用同一邏輯。
    網路失敗時仍回傳最後一份已驗證快取，不讓整個首頁被拖垮。
    """
    today = as_of or date.today()
    end_date = today - timedelta(days=1)
    cached = _read_cache(seed_path, cache_path)
    if cached.empty:
        start_date = end_date - timedelta(days=45)
    else:
        start_date = cached.index[-1].date() + timedelta(days=1)

    records = []
    cursor = start_date
    while cursor <= end_date:
        if cursor.weekday() < 5:
            try:
                value = fetcher(cursor)
                if value is not None:
                    records.append((pd.Timestamp(cursor), float(value)))
            except Exception:
                pass
        cursor += timedelta(days=1)

    if records:
        additions = pd.DataFrame(records, columns=["date", "Close"]).set_index("date")
        cached = pd.concat([cached, additions])
        cached = cached[~cached.index.duplicated(keep="last")].sort_index()
        _write_cache(cached.tail(keep_trading_days), cache_path)

    if cached.empty:
        raise RuntimeError("抓不到外資期貨未平倉資料，且沒有可用快取")
    return cached.tail(keep_trading_days)


def fetch_foreign_futures_position(lookback_trading_days: int = 20) -> pd.DataFrame:
    """回傳近 N 個交易日，正常載入只需 0～1 次 TAIFEX 查詢。"""
    cached = update_foreign_futures_cache(keep_trading_days=max(25, lookback_trading_days))
    return cached.tail(lookback_trading_days)
