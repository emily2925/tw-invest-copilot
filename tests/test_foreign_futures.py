"""外資期貨增量快取測試。"""
import tempfile
import unittest
from datetime import date
from pathlib import Path

from market_data.foreign_futures import update_foreign_futures_cache


class ForeignFuturesCacheTest(unittest.TestCase):
    def test_only_fetches_missing_weekdays_and_reuses_written_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seed = root / "seed.csv"
            runtime = root / "runtime.csv"
            seed.write_text("date,Close\n2026-07-15,-79557\n", encoding="utf-8")
            calls = []

            def fake_fetcher(query_date):
                calls.append(query_date)
                return {date(2026, 7, 16): -84453, date(2026, 7, 17): -86189}.get(query_date)

            first = update_foreign_futures_cache(
                cache_path=runtime,
                seed_path=seed,
                as_of=date(2026, 7, 18),
                fetcher=fake_fetcher,
            )
            self.assertEqual(calls, [date(2026, 7, 16), date(2026, 7, 17)])
            self.assertEqual(float(first.iloc[-1]["Close"]), -86189)

            calls.clear()
            second = update_foreign_futures_cache(
                cache_path=runtime,
                seed_path=seed,
                as_of=date(2026, 7, 18),
                fetcher=fake_fetcher,
            )
            self.assertEqual(calls, [])
            self.assertEqual(len(second), 3)


if __name__ == "__main__":
    unittest.main()
