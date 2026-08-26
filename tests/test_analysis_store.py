import os
import tempfile
import unittest

from agent.analysis_store import load_latest_analysis, save_latest_analysis


class AnalysisStoreTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "analysis.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_returns_none_before_first_analysis(self):
        self.assertIsNone(load_latest_analysis("2330.TW", self.db_path))

    def test_saves_and_loads_each_symbol_independently(self):
        save_latest_analysis(
            "2330.TW", "台積電", "第一次分析", 0.0123,
            analyzed_at="2026-08-26 16:00:00", db_path=self.db_path,
        )
        save_latest_analysis(
            "2454.TW", "聯發科", "另一檔分析", 0.0234,
            analyzed_at="2026-08-26 16:01:00", db_path=self.db_path,
        )

        tsmc = load_latest_analysis("2330.TW", self.db_path)
        mediatek = load_latest_analysis("2454.TW", self.db_path)
        self.assertEqual(tsmc["text"], "第一次分析")
        self.assertEqual(tsmc["at"], "2026-08-26 16:00:00")
        self.assertAlmostEqual(tsmc["cost"], 0.0123)
        self.assertEqual(mediatek["text"], "另一檔分析")

    def test_new_success_replaces_only_that_symbols_last_analysis(self):
        save_latest_analysis(
            "2330.TW", "台積電", "舊分析", 0.01,
            analyzed_at="2026-08-26 15:00:00", db_path=self.db_path,
        )
        save_latest_analysis(
            "2330.TW", "台積電", "新分析", 0.02,
            analyzed_at="2026-08-26 16:00:00", db_path=self.db_path,
        )

        result = load_latest_analysis("2330.TW", self.db_path)
        self.assertEqual(result["text"], "新分析")
        self.assertEqual(result["at"], "2026-08-26 16:00:00")


if __name__ == "__main__":
    unittest.main()
