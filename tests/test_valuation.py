"""本益比河流圖計算測試。"""
import unittest

import pandas as pd

from market_data.valuation import build_pe_river, is_pe_river_applicable


class PeRiverTest(unittest.TestCase):
    def test_index_and_etf_are_not_applicable(self):
        self.assertFalse(is_pe_river_applicable("^TWII"))
        self.assertFalse(is_pe_river_applicable("00685L.TW"))
        self.assertTrue(is_pe_river_applicable("2330.TW"))

    def test_builds_bands_from_historical_percentiles(self):
        dates = pd.date_range("2025-01-01", periods=10)
        prices = pd.DataFrame({"Close": [100.0] * 10}, index=dates)
        pe = pd.DataFrame({"PER": list(range(10, 20))}, index=dates)

        result = build_pe_river(prices, pe, min_observations=5)

        self.assertEqual(result["observations"], 10)
        self.assertAlmostEqual(result["current_pe"], 19)
        self.assertIn("PE_P20", result["data"].columns)
        expected = (100 / 19) * result["percentiles"][20]
        self.assertAlmostEqual(result["data"]["PE_P20"].iloc[-1], expected)

    def test_preserves_price_basis_adjustment_metadata(self):
        dates = pd.date_range("2025-01-01", periods=10)
        prices = pd.DataFrame({"Close": [100.0] * 10}, index=dates)
        prices.attrs["share_basis_adjustments"] = [
            {"date": pd.Timestamp("2025-06-01"), "type": "面額變更", "basis_factor": 0.25}
        ]
        pe = pd.DataFrame({"PER": [10.0] * 10}, index=dates)

        result = build_pe_river(prices, pe, min_observations=5)

        self.assertEqual(result["basis_adjustments"][0]["basis_factor"], 0.25)

    def test_rejects_low_positive_pe_coverage(self):
        dates = pd.date_range("2025-01-01", periods=10)
        prices = pd.DataFrame({"Close": [100.0] * 10}, index=dates)
        pe = pd.DataFrame({"PER": [10.0, 11.0] + [0.0] * 8}, index=dates)

        with self.assertRaisesRegex(ValueError, "覆蓋率"):
            build_pe_river(prices, pe, min_observations=2, min_positive_pe_coverage=0.8)


if __name__ == "__main__":
    unittest.main()
