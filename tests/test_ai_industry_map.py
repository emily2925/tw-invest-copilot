import unittest

import pandas as pd

from views.ai_industry_map import calculate_period_returns


class CalculatePeriodReturnsTest(unittest.TestCase):
    def test_uses_trading_day_windows(self):
        close = pd.Series(range(100, 401), dtype=float)

        result = calculate_period_returns(close)

        self.assertAlmostEqual(result["1個月"], (400 / 379 - 1) * 100)
        self.assertAlmostEqual(result["3個月"], (400 / 337 - 1) * 100)
        self.assertAlmostEqual(result["6個月"], (400 / 274 - 1) * 100)
        self.assertAlmostEqual(result["12個月"], (400 / 148 - 1) * 100)

    def test_marks_insufficient_history(self):
        result = calculate_period_returns(pd.Series([100.0, 110.0]))

        self.assertTrue(all(value is None for value in result.values()))


if __name__ == "__main__":
    unittest.main()
