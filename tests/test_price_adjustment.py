"""股票／ETF 分割後歷史行情還原測試。"""
import unittest

import pandas as pd

from market_data.price_adjustment import adjust_ohlcv_for_share_basis_changes


class PriceAdjustmentTest(unittest.TestCase):
    def test_split_adjusts_old_ohlc_and_inverse_adjusts_volume(self):
        raw = pd.DataFrame(
            {
                "Open": [300.0, 13.0], "High": [312.0, 13.2],
                "Low": [288.0, 12.0], "Close": [306.0, 12.75],
                "Volume": [1_000.0, 24_000.0],
            },
            index=pd.to_datetime(["2026-06-30", "2026-07-07"]),
        )
        changes = pd.DataFrame(
            {
                "date": pd.to_datetime(["2026-07-07"]),
                "type": ["分割"],
                "before_price": [306.0], "after_price": [12.75],
                "basis_factor": [1 / 24],
            }
        )

        adjusted = adjust_ohlcv_for_share_basis_changes(raw, changes)

        self.assertAlmostEqual(adjusted.loc["2026-06-30", "Close"], 12.75)
        self.assertAlmostEqual(adjusted.loc["2026-06-30", "Open"], 12.50)
        self.assertAlmostEqual(adjusted.loc["2026-06-30", "Volume"], 24_000)
        self.assertAlmostEqual(adjusted.loc["2026-07-07", "Close"], 12.75)
        self.assertEqual(len(adjusted.attrs["share_basis_adjustments"]), 1)

    def test_reverse_split_multiplies_old_price(self):
        raw = pd.DataFrame(
            {"Open": [5.0], "High": [5.2], "Low": [4.8], "Close": [5.0], "Volume": [10_000.0]},
            index=pd.to_datetime(["2025-01-01"]),
        )
        changes = pd.DataFrame(
            {"date": pd.to_datetime(["2025-01-02"]), "basis_factor": [4.0]}
        )

        adjusted = adjust_ohlcv_for_share_basis_changes(raw, changes)

        self.assertAlmostEqual(adjusted.iloc[0]["Close"], 20.0)
        self.assertAlmostEqual(adjusted.iloc[0]["Volume"], 2_500.0)
