"""月營收趨勢計算測試。"""
import unittest

import pandas as pd

from market_data.fundamentals import is_company_fundamentals_applicable, prepare_revenue_trend


class RevenueTrendTest(unittest.TestCase):
    def test_index_and_etf_are_not_applicable(self):
        self.assertFalse(is_company_fundamentals_applicable("^TWII"))
        self.assertFalse(is_company_fundamentals_applicable("00685L.TW"))
        self.assertTrue(is_company_fundamentals_applicable("2330.TW"))

    def test_uses_revenue_period_and_calculates_changes(self):
        periods = pd.date_range("2025-01-01", periods=14, freq="MS")
        revenue = [100_000_000 * (i + 1) for i in range(14)]
        raw = pd.DataFrame(
            {
                "revenue": revenue,
                "revenue_year": periods.year,
                "revenue_month": periods.month,
                "announcement_date": periods + pd.Timedelta(days=10),
                "record_date": periods + pd.offsets.MonthBegin(1),
            }
        )

        result = prepare_revenue_trend(raw, display_months=12)

        self.assertEqual(result["latest_period"], pd.Timestamp("2026-02-01"))
        self.assertEqual(len(result["data"]), 12)
        self.assertAlmostEqual(result["latest_revenue_100m"], 14)
        self.assertAlmostEqual(result["mom_pct"], (14 / 13 - 1) * 100)
        self.assertAlmostEqual(result["yoy_pct"], (14 / 2 - 1) * 100)

    def test_requires_minimum_two_months(self):
        raw = pd.DataFrame({"revenue": [1], "revenue_year": [2026], "revenue_month": [1]})
        with self.assertRaisesRegex(ValueError, "至少需要 2 個月"):
            prepare_revenue_trend(raw)


if __name__ == "__main__":
    unittest.main()
