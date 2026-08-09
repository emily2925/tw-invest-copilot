"""個股籌碼面計算測試（三大法人買賣超、融資融券、外資持股比率）。"""
import unittest

import pandas as pd

from market_data.institutional import (
    is_institutional_applicable,
    prepare_foreign_shareholding,
    prepare_institutional_net,
    prepare_margin_short,
)


class ApplicabilityTest(unittest.TestCase):
    def test_index_has_no_stock_chips_but_stock_and_etf_do(self):
        self.assertFalse(is_institutional_applicable("^TWII"))
        self.assertTrue(is_institutional_applicable("2330.TW"))
        self.assertTrue(is_institutional_applicable("0050.TW"))


class InstitutionalNetTest(unittest.TestCase):
    def _raw(self):
        # 兩天資料，每天外資/投信/自營各一列；buy/sell 單位為股。
        rows = []
        # day1：外資買超 +1000 股(=+1 張)、投信賣超 -2000 股、自營 self+hedging 合計 +500
        rows += [
            {"date": "2026-08-06", "name": "Foreign_Investor", "buy": 3000, "sell": 2000},
            {"date": "2026-08-06", "name": "Investment_Trust", "buy": 0, "sell": 2000},
            {"date": "2026-08-06", "name": "Dealer_self", "buy": 300, "sell": 0},
            {"date": "2026-08-06", "name": "Dealer_Hedging", "buy": 200, "sell": 0},
        ]
        # day2：外資再買超 +5000 股(=+5 張)、投信買超 +1000、自營賣超 -1000
        rows += [
            {"date": "2026-08-07", "name": "Foreign_Investor", "buy": 6000, "sell": 1000},
            {"date": "2026-08-07", "name": "Investment_Trust", "buy": 1000, "sell": 0},
            {"date": "2026-08-07", "name": "Dealer_self", "buy": 0, "sell": 1000},
        ]
        return pd.DataFrame(rows)

    def test_pivots_and_converts_to_lots(self):
        result = prepare_institutional_net(self._raw(), display_days=20)
        self.assertEqual(result["latest_date"], pd.Timestamp("2026-08-07"))
        self.assertAlmostEqual(result["foreign_net"], 5.0)   # (6000-1000)/1000
        self.assertAlmostEqual(result["trust_net"], 1.0)     # 1000/1000
        self.assertAlmostEqual(result["dealer_net"], -1.0)   # -1000/1000
        self.assertAlmostEqual(result["foreign_cum_20d"], 6.0)  # 1 + 5 張

    def test_foreign_streak_counts_consecutive_buy_days(self):
        result = prepare_institutional_net(self._raw())
        self.assertEqual(result["foreign_streak"], {"days": 2, "direction": "buy"})

    def test_missing_columns_raise(self):
        with self.assertRaisesRegex(ValueError, "缺少欄位"):
            prepare_institutional_net(pd.DataFrame({"date": ["2026-08-07"]}))


class MarginShortTest(unittest.TestCase):
    def test_balances_and_daily_change(self):
        raw = pd.DataFrame(
            {
                "date": ["2026-08-06", "2026-08-07"],
                "MarginPurchaseTodayBalance": [29949, 29657],
                "ShortSaleTodayBalance": [38, 33],
            }
        )
        result = prepare_margin_short(raw, display_days=20)
        self.assertAlmostEqual(result["margin_balance"], 29657)
        self.assertAlmostEqual(result["short_balance"], 33)
        self.assertAlmostEqual(result["margin_change"], -292)
        self.assertAlmostEqual(result["short_change"], -5)


class ForeignShareholdingTest(unittest.TestCase):
    def test_ratio_and_window_change(self):
        raw = pd.DataFrame(
            {
                "date": ["2026-06-01", "2026-07-01", "2026-08-07"],
                "ForeignInvestmentSharesRatio": [68.0, 68.5, 69.14],
            }
        )
        result = prepare_foreign_shareholding(raw, display_days=60)
        self.assertAlmostEqual(result["foreign_ratio"], 69.14)
        self.assertAlmostEqual(result["ratio_change"], 69.14 - 68.0)


if __name__ == "__main__":
    unittest.main()
