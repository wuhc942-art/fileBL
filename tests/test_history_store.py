import datetime as dt
import tempfile
import unittest
from pathlib import Path

from history_store import load_history_rows, save_history_rows


class HistoryStoreTest(unittest.TestCase):
    def test_save_history_rows_persists_dates_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "history.sqlite"
            row = {
                "\u9001\u8d27\u65e5\u671f": dt.date(2026, 6, 23),
                "\u6765\u6e90\u6587\u4ef6": "demo.xlsx",
                "\u5ba2\u6237": "\u5ba2\u6237A",
                "\u5185\u90e8\u7f16\u7801": "A001",
                "\u578b\u53f7/\u54c1\u540d": "\u578b\u53f7A",
                "\u89c4\u683c": "\u89c4\u683cA",
                "\u5355\u4f4d": "\u5377",
                "\u6570\u91cf": 2.0,
                "\u5355\u4ef7": 10.0,
                "\u91d1\u989d": 20.0,
                "\u9001\u8d27\u5355\u53f7": "D1",
                "\u8ba2\u5355\u53f7": "O1",
                "\u5907\u6ce8": "\u7b2c\u4e00\u6b21",
            }

            self.assertEqual(save_history_rows(db_path, [row]), 1)
            self.assertEqual(save_history_rows(db_path, [row]), 0)

            rows = load_history_rows(db_path)

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["\u9001\u8d27\u65e5\u671f"], dt.date(2026, 6, 23))
            self.assertEqual(rows[0]["\u5ba2\u6237"], "\u5ba2\u6237A")
            self.assertEqual(rows[0]["\u91d1\u989d"], 20.0)

    def test_load_history_rows_merges_existing_missing_delivery_no_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "history.sqlite"
            base = {
                "\u9001\u8d27\u65e5\u671f": dt.date(2026, 6, 23),
                "\u6765\u6e90\u6587\u4ef6": "demo.xlsx",
                "\u5ba2\u6237": "\u5ba2\u6237A",
                "\u5185\u90e8\u7f16\u7801": "A001",
                "\u578b\u53f7/\u54c1\u540d": "\u578b\u53f7A",
                "\u89c4\u683c": "\u89c4\u683cA",
                "\u5355\u4f4d": "\u5377",
                "\u6570\u91cf": 2.0,
                "\u5355\u4ef7": 10.0,
                "\u91d1\u989d": 20.0,
                "\u8ba2\u5355\u53f7": "O1",
                "\u5907\u6ce8": "",
            }
            missing_delivery = {**base, "\u9001\u8d27\u5355\u53f7": ""}
            with_delivery = {**base, "\u9001\u8d27\u5355\u53f7": "D1"}

            self.assertEqual(save_history_rows(db_path, [missing_delivery, with_delivery]), 1)

            rows = load_history_rows(db_path)

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["\u9001\u8d27\u5355\u53f7"], "D1")


if __name__ == "__main__":
    unittest.main()
