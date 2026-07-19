"""實際季度 EPS 整理測試。"""
import unittest

import pandas as pd

from market_data.earnings import prepare_eps_summary


class EpsSummaryTest(unittest.TestCase):
    def test_calculates_latest_ttm_and_same_quarter_yoy(self):
        dates = pd.to_datetime(
            ["2024-03-31", "2024-06-30", "2024-09-30", "2024-12-31",
             "2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"]
        )
        raw = pd.DataFrame({"EPS": [2, 3, 4, 5, 4, 6, 8, 10]}, index=dates)

        result = prepare_eps_summary(raw)

        self.assertEqual(result["latest_date"], pd.Timestamp("2025-12-31"))
        self.assertEqual(result["latest_eps"], 10)
        self.assertEqual(result["ttm_eps"], 28)
        self.assertEqual(result["quarterly_yoy_pct"], 100)

    def test_requires_four_quarters_for_ttm(self):
        raw = pd.DataFrame(
            {"EPS": [1, 2, 3]},
            index=pd.to_datetime(["2025-03-31", "2025-06-30", "2025-09-30"]),
        )
        with self.assertRaisesRegex(ValueError, "至少需要 4 季"):
            prepare_eps_summary(raw)


if __name__ == "__main__":
    unittest.main()
