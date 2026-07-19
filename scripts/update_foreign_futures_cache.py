"""供 GitHub Actions 每日增量更新外資期貨公開快取。"""
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from market_data.foreign_futures import update_foreign_futures_cache  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data_cache" / "foreign_futures.csv",
    )
    args = parser.parse_args()
    result = update_foreign_futures_cache(
        cache_path=args.output,
        seed_path=args.output,
        keep_trading_days=25,
    )
    print(f"外資期貨快取：{result.index[0].date()}～{result.index[-1].date()}，共 {len(result)} 筆")


if __name__ == "__main__":
    main()
