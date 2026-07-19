"""股票分割後 EPS 基準調整測試。"""
import unittest

import pandas as pd

from market_data.eps_adjustment import (
    adjust_eps_for_share_basis_changes,
    prepare_split_adjusted_eps_summary,
)


class EpsAdjustmentTest(unittest.TestCase):
    def setUp(self):
        self.raw = pd.DataFrame(
            {"EPS": [11.02, 13.02, 11.01, 7.07, 10.77, 9.74, 3.10, 3.29]},
            index=pd.to_datetime(
                [
                    "2024-03-31", "2024-06-30", "2024-09-30", "2024-12-31",
                    "2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31",
                ]
            ),
        )
        self.changes = pd.DataFrame(
            {
                "date": pd.to_datetime(["2025-08-25"]),
                "type": ["面額變更"],
                "before_price": [546.0],
                "after_price": [136.5],
                "basis_factor": [0.25],
            }
        )

    def test_adjusts_only_eps_before_split(self):
        adjusted = adjust_eps_for_share_basis_changes(self.raw, self.changes)

        self.assertAlmostEqual(adjusted.loc["2024-09-30", "EPS"], 2.7525)
        self.assertAlmostEqual(adjusted.loc["2025-06-30", "EPS"], 2.435)
        self.assertAlmostEqual(adjusted.loc["2025-09-30", "EPS"], 3.10)

    def test_yoy_and_ttm_use_same_share_basis(self):
        result = prepare_split_adjusted_eps_summary(self.raw, self.changes)

        self.assertAlmostEqual(result["quarterly_yoy_pct"], 86.1386, places=3)
        self.assertAlmostEqual(result["ttm_eps"], 11.5175)
        self.assertEqual(len(result["basis_adjustments"]), 1)

    def test_no_change_preserves_eps(self):
        adjusted = adjust_eps_for_share_basis_changes(self.raw, pd.DataFrame())
        pd.testing.assert_series_equal(adjusted["EPS"], self.raw["EPS"])


if __name__ == "__main__":
    unittest.main()
