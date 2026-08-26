import unittest

from views.stock_selection import selected_symbols_from_rows, watchlist_items_to_load


class StockSelectionTest(unittest.TestCase):
    def setUp(self):
        self.watchlist = [
            {"symbol": "A", "name": "甲", "category": "一"},
            {"symbol": "B", "name": "乙", "category": "一"},
            {"symbol": "C", "name": "丙", "category": "二"},
        ]

    def test_multiple_rows_keep_table_order_and_ignore_invalid_rows(self):
        symbols = selected_symbols_from_rows(self.watchlist, [0, 2, 2, 99, -1])
        self.assertEqual(symbols, ["A", "C"])

    def test_loading_keeps_filter_candidates_and_previous_confirmed_symbols(self):
        result = watchlist_items_to_load(
            filtered_watchlist=self.watchlist[2:],
            full_watchlist=self.watchlist,
            confirmed_symbols=["A", "C"],
        )
        self.assertEqual([item["symbol"] for item in result], ["C", "A"])


if __name__ == "__main__":
    unittest.main()
