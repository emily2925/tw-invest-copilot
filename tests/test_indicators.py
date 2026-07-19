"""技術指標的決定性單元測試。"""
import unittest

import pandas as pd

from market_data.indicators import moving_average_cross_signals


def _prices(values: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"Close": values})


class MovingAverageCrossSignalsTest(unittest.TestCase):
    def test_closed_session_crosses_below(self):
        signals = moving_average_cross_signals(_prices([10, 10, 10, 10, 10, 12, 8]), 8, [5])
        self.assertEqual(signals[0]["direction"], "down")
        self.assertFalse(signals[0]["is_live"])
        self.assertAlmostEqual(signals[0]["ma_value"], 10)

    def test_closed_session_crosses_above(self):
        signals = moving_average_cross_signals(_prices([10, 10, 10, 10, 10, 8, 12]), 12, [5])
        self.assertEqual(signals[0]["direction"], "up")
        self.assertFalse(signals[0]["is_live"])
        self.assertAlmostEqual(signals[0]["ma_value"], 10)

    def test_live_price_uses_provisional_average(self):
        signals = moving_average_cross_signals(_prices([10, 10, 10, 10, 12]), 8, [5])
        self.assertEqual(signals[0]["direction"], "down")
        self.assertTrue(signals[0]["is_live"])
        self.assertAlmostEqual(signals[0]["ma_value"], 10)

    def test_does_not_repeat_when_price_stays_below(self):
        signals = moving_average_cross_signals(_prices([10, 10, 10, 10, 10, 8, 7]), 7, [5])
        self.assertEqual(signals, [])


if __name__ == "__main__":
    unittest.main()
