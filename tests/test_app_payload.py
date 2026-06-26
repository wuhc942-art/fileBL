import datetime as dt
import unittest

from app_server import (
    _build_import_checks,
    _build_import_summary,
    _build_payload_from_rows,
    build_dashboard_payload,
    configure_material_catalog,
    configure_storage_root,
    is_write_allowed,
    save_export_file,
)
from summarize_shipments import DETAIL_SHEET, HISTORY_SHEET, SummaryResult, excel_serial
from tests.test_summarize_shipments import _write_xlsx_named_sheets


class DashboardPayloadTest(unittest.TestCase):
    def _result(self, date, rows, by_customer=None, sources=None):
        if by_customer is None:
            customer_map = {}
            for row in rows:
                key = row["客户"]
                item = customer_map.setdefault(key, {"客户": key, "发货笔数": 0, "数量": 0.0, "金额": 0.0})
                item["发货笔数"] += 1
                item["数量"] += row["数量"]
                item["金额"] += row["金额"]
            by_customer = sorted(customer_map.values(), key=lambda item: item["金额"], reverse=True)
        return SummaryResult(
            date=date,
            sources=sources or sorted({row["来源文件"] for row in rows}),
            rows=rows,
            by_customer=by_customer,
            total_rows=len(rows),
            total_amount=sum(row["金额"] for row in rows),
            total_quantity=sum(row["数量"] for row in rows),
            customer_count=len({row["客户"] for row in rows}),
        )

    def test_build_dashboard_payload_groups_models_and_sources(self):
        result = SummaryResult(
            date=dt.date(2026, 6, 23),
            sources=["a.xlsx", "b.xlsx"],
            rows=[
                {
                    "来源文件": "a.xlsx",
                    "客户": "客户A",
                    "型号/品名": "型号1",
                    "规格": "规格1",
                    "单位": "㎡",
                    "数量": 2.0,
                    "单价": 50.0,
                    "金额": 100.0,
                    "送货单号": "D1",
                    "订单号": "O1",
                },
                {
                    "来源文件": "b.xlsx",
                    "客户": "客户B",
                    "型号/品名": "型号1",
                    "规格": "规格2",
                    "单位": "㎡",
                    "数量": 3.0,
                    "单价": 50.0,
                    "金额": 150.0,
                    "送货单号": "D2",
                    "订单号": "O2",
                },
                {
                    "来源文件": "b.xlsx",
                    "客户": "客户B",
                    "型号/品名": "型号2",
                    "规格": "规格3",
                    "单位": "张",
                    "数量": 4.0,
                    "单价": 20.0,
                    "金额": 80.0,
                    "送货单号": "D3",
                    "订单号": "O3",
                },
                {
                    "来源文件": "b.xlsx",
                    "客户": "客户C",
                    "型号/品名": "型号3",
                    "规格": "规格4",
                    "单位": "㎡",
                    "数量": -1.0,
                    "单价": 0.0,
                    "金额": 0.0,
                    "送货单号": "",
                    "订单号": "O4",
                },
            ],
            by_customer=[
                {"客户": "客户B", "发货笔数": 2, "数量": 7.0, "金额": 230.0},
                {"客户": "客户A", "发货笔数": 1, "数量": 2.0, "金额": 100.0},
            ],
            total_rows=4,
            total_amount=330.0,
            total_quantity=8.0,
            customer_count=3,
        )

        payload = build_dashboard_payload(result)

        self.assertEqual(payload["kpis"]["rows"], 4)
        self.assertEqual(payload["kpis"]["customers"], 3)
        self.assertEqual(payload["charts"]["models"][0]["name"], "型号1")
        self.assertEqual(payload["charts"]["models"][0]["amount"], 250.0)
        self.assertEqual(payload["charts"]["sources"][0]["name"], "b.xlsx")
        self.assertEqual(payload["charts"]["sources"][0]["amount"], 230.0)
        self.assertEqual(payload["rows"][0]["customer"], "客户A")
        self.assertEqual(payload["anomalies"]["total"], 4)
        self.assertEqual(payload["anomalies"]["counts"]["zeroAmount"], 1)
        self.assertEqual(payload["anomalies"]["counts"]["negativeQuantity"], 1)
        self.assertEqual(payload["anomalies"]["counts"]["missingDeliveryNo"], 1)
        self.assertEqual(payload["anomalies"]["counts"]["missingPrice"], 1)
        self.assertEqual(payload["customerDetails"]["客户B"][0]["model"], "型号1")
        self.assertIsNone(payload["fileCheck"]["expected"])
        self.assertEqual(payload["fileCheck"]["actual"], 2)
        self.assertEqual(payload["fileCheck"]["status"], "ready")
        self.assertTrue(any("客户B" in insight for insight in payload["insights"]))
        self.assertTrue(any("型号1" in insight for insight in payload["insights"]))

    def test_build_dashboard_payload_classifies_customer_material_categories(self):
        result = SummaryResult(
            date=dt.date(2026, 6, 23),
            sources=["a.xlsx"],
            rows=[
                {
                    "来源文件": "a.xlsx",
                    "客户": "客户A",
                    "型号/品名": "补强板",
                    "规格": "FR4",
                    "单位": "张",
                    "数量": 2.0,
                    "单价": 50.0,
                    "金额": 100.0,
                    "送货单号": "D1",
                    "订单号": "O1",
                },
                {
                    "来源文件": "a.xlsx",
                    "客户": "客户A",
                    "型号/品名": "覆盖膜 / AU-25KA",
                    "规格": "W500",
                    "单位": "卷",
                    "数量": 1.0,
                    "单价": 200.0,
                    "金额": 200.0,
                    "送货单号": "D2",
                    "订单号": "O2",
                },
                {
                    "来源文件": "a.xlsx",
                    "客户": "客户B",
                    "型号/品名": "PI基材",
                    "规格": "12.5um",
                    "单位": "卷",
                    "数量": 1.0,
                    "单价": 300.0,
                    "金额": 300.0,
                    "送货单号": "D3",
                    "订单号": "O3",
                },
            ],
            by_customer=[
                {"客户": "客户B", "发货笔数": 1, "数量": 1.0, "金额": 300.0},
                {"客户": "客户A", "发货笔数": 2, "数量": 3.0, "金额": 300.0},
            ],
            total_rows=3,
            total_amount=600.0,
            total_quantity=4.0,
            customer_count=2,
        )

        payload = build_dashboard_payload(result)

        self.assertEqual(payload["rows"][0]["materialCategory"], "补强")
        self.assertEqual(payload["rows"][1]["materialCategory"], "覆盖膜")
        self.assertEqual(payload["rows"][2]["materialCategory"], "基材")
        customer_a = next(row for row in payload["customers"] if row["customer"] == "客户A")
        self.assertEqual(customer_a["primaryMaterialCategory"], "覆盖膜")
        self.assertEqual(customer_a["materialCategories"][0]["name"], "覆盖膜")
        self.assertEqual(payload["charts"]["materialCategories"][0]["name"], "基材")

    def test_material_catalog_overrides_keyword_classification(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            workbook = Path(tmp) / "catalog.xlsx"
            _write_xlsx_named_sheets(
                workbook,
                {"库存": [["产品名称", "材料类型"], ["AU-25KA", "覆盖膜"]]},
            )
            try:
                configure_material_catalog(workbook)
                result = SummaryResult(
                    date=dt.date(2026, 6, 23),
                    sources=["a.xlsx"],
                    rows=[
                        {
                            "来源文件": "a.xlsx",
                            "客户": "客户A",
                            "型号/品名": "AU-25KA",
                            "规格": "",
                            "单位": "卷",
                            "数量": 1.0,
                            "单价": 10.0,
                            "金额": 10.0,
                            "送货单号": "D1",
                            "订单号": "O1",
                        }
                    ],
                    by_customer=[{"客户": "客户A", "发货笔数": 1, "数量": 1.0, "金额": 10.0}],
                    total_rows=1,
                    total_amount=10.0,
                    total_quantity=1.0,
                    customer_count=1,
                )

                payload = build_dashboard_payload(result)

                self.assertEqual(payload["rows"][0]["materialCategory"], "覆盖膜")
            finally:
                configure_material_catalog(None)

    def test_payload_customer_history_details_include_rows_before_target_date(self):
        target_date = dt.date(2026, 6, 23)
        rows = [
            {
                "来源文件": "history.xlsx",
                "送货日期": target_date - dt.timedelta(days=10),
                "客户": "固定客户",
                "型号/品名": "纯胶膜",
                "规格": "AE15P-25KA",
                "单位": "㎡",
                "数量": 10.0,
                "单价": 30.0,
                "金额": 300.0,
                "送货单号": "H1",
                "订单号": "O1",
            },
            {
                "来源文件": "today.xlsx",
                "送货日期": target_date,
                "客户": "固定客户",
                "型号/品名": "补强板",
                "规格": "FR4",
                "单位": "张",
                "数量": 1.0,
                "单价": 10.0,
                "金额": 10.0,
                "送货单号": "D1",
                "订单号": "O2",
            },
        ]

        payload = _build_payload_from_rows(rows, target_date, ["history.xlsx"])

        history_profile = payload["customerHistoryProfiles"]["固定客户"]
        self.assertEqual(history_profile["total"]["rows"], 2)
        self.assertEqual(history_profile["primaryCategory"]["name"], "纯胶")
        self.assertEqual(history_profile["categories"][0]["amount"], 300.0)
        self.assertEqual(history_profile["categories"][1]["name"], "补强")
        self.assertEqual(payload["customerHistoryDetails"], {})
        self.assertEqual(payload["customerDetails"]["固定客户"][0]["materialCategory"], "补强")


    def test_build_dashboard_payload_includes_business_speed_metrics(self):
        today = self._result(
            dt.date(2026, 6, 23),
            [
                {
                    "来源文件": "奥科泰2026年6月发货统计表（含税）.xlsx",
                    "客户": "大客户A",
                    "型号/品名": "型号A",
                    "规格": "",
                    "单位": "卷",
                    "数量": 10.0,
                    "单价": 20000.0,
                    "金额": 200000.0,
                    "送货单号": "D1",
                    "订单号": "O1",
                },
                {
                    "来源文件": "科泰顺2026年6月发货统计表(现金).xlsx",
                    "客户": "新客户B",
                    "型号/品名": "型号A",
                    "规格": "",
                    "单位": "卷",
                    "数量": 4.0,
                    "单价": 10000.0,
                    "金额": 40000.0,
                    "送货单号": "D2",
                    "订单号": "O2",
                },
            ],
        )
        yesterday = self._result(
            dt.date(2026, 6, 22),
            [
                {
                    "来源文件": "奥科泰2026年6月发货统计表（含税）.xlsx",
                    "客户": "老客户C",
                    "型号/品名": "型号C",
                    "规格": "",
                    "单位": "卷",
                    "数量": 7.0,
                    "单价": 10000.0,
                    "金额": 70000.0,
                    "送货单号": "D3",
                    "订单号": "O3",
                }
            ],
        )
        last_week = self._result(dt.date(2026, 6, 16), [])

        payload = build_dashboard_payload(today, {"yesterday": yesterday, "lastWeek": last_week})

        self.assertEqual(payload["comparisons"]["yesterday"]["amount"]["delta"], 170000.0)
        self.assertEqual(payload["comparisons"]["yesterday"]["quantity"]["delta"], 7.0)
        self.assertEqual(payload["comparisons"]["yesterday"]["customers"]["delta"], 1)
        self.assertTrue(payload["comparisons"]["lastWeek"]["amount"]["hasBaseline"])
        self.assertEqual(payload["comparisons"]["lastWeek"]["amount"]["delta"], 240000.0)
        self.assertEqual(payload["modelDetails"]["型号A"][0]["customer"], "大客户A")
        self.assertEqual(payload["modelDetails"]["型号A"][1]["customer"], "新客户B")
        self.assertEqual(payload["amountStructure"]["taxType"][0]["name"], "含税")
        self.assertEqual(payload["amountStructure"]["taxType"][0]["amount"], 200000.0)
        self.assertEqual(payload["amountStructure"]["company"][0]["name"], "奥科泰")
        self.assertEqual(payload["businessAlerts"]["highValueCustomers"][0]["customer"], "大客户A")
        self.assertIn("新客户B", payload["businessAlerts"]["newCustomers"])
        self.assertIn("老客户C", payload["businessAlerts"]["silentCustomers"])

    def test_comparisons_include_recent_average_when_prior_days_have_data(self):
        today_date = dt.date(2026, 6, 23)
        current = self._result(
            today_date,
            [
                {
                    "来源文件": "today.xlsx",
                    "客户": "客户A",
                    "型号/品名": "型号A",
                    "规格": "",
                    "单位": "卷",
                    "数量": 10.0,
                    "单价": 100.0,
                    "金额": 1000.0,
                    "送货单号": "D1",
                    "订单号": "O1",
                }
            ],
        )
        last_7_average = SummaryResult(
            date=today_date - dt.timedelta(days=7),
            sources=["history.sqlite"],
            rows=[],
            by_customer=[],
            total_rows=3 / 7,
            total_amount=700 / 7,
            total_quantity=14 / 7,
            customer_count=2 / 7,
        )

        payload = build_dashboard_payload(current, {"last7Average": last_7_average})

        self.assertTrue(payload["comparisons"]["last7Average"]["amount"]["hasBaseline"])
        self.assertEqual(payload["comparisons"]["last7Average"]["amount"]["baseline"], 100.0)
        self.assertEqual(payload["comparisons"]["last7Average"]["amount"]["delta"], 900.0)

    def test_payload_from_history_rows_builds_recent_average_comparisons(self):
        today_date = dt.date(2026, 6, 23)
        rows = [
            {
                "送货日期": today_date,
                "来源文件": "history.xlsx",
                "客户": "客户A",
                "型号/品名": "型号A",
                "规格": "",
                "单位": "卷",
                "数量": 10.0,
                "单价": 100.0,
                "金额": 1000.0,
                "送货单号": "D1",
                "订单号": "O1",
            },
            {
                "送货日期": today_date - dt.timedelta(days=1),
                "来源文件": "history.xlsx",
                "客户": "客户B",
                "型号/品名": "型号B",
                "规格": "",
                "单位": "卷",
                "数量": 4.0,
                "单价": 100.0,
                "金额": 400.0,
                "送货单号": "D2",
                "订单号": "O2",
            },
            {
                "送货日期": today_date - dt.timedelta(days=7),
                "来源文件": "history.xlsx",
                "客户": "客户C",
                "型号/品名": "型号C",
                "规格": "",
                "单位": "卷",
                "数量": 3.0,
                "单价": 100.0,
                "金额": 300.0,
                "送货单号": "D3",
                "订单号": "O3",
            },
        ]

        payload = _build_payload_from_rows(rows, today_date, ["history.sqlite"])

        self.assertTrue(payload["comparisons"]["last7Average"]["amount"]["hasBaseline"])
        self.assertEqual(payload["comparisons"]["last7Average"]["amount"]["baseline"], 100.0)
        self.assertTrue(payload["comparisons"]["last30Average"]["amount"]["hasBaseline"])
        self.assertEqual(payload["comparisons"]["last30Average"]["amount"]["baseline"], 23.33)


    def test_business_alerts_use_full_history_context_when_available(self):
        today = self._result(
            dt.date(2026, 6, 23),
            [
                {
                    "\u6765\u6e90\u6587\u4ef6": "today.xlsx",
                    "\u5ba2\u6237": "\u65b0\u5ba2\u6237",
                    "\u578b\u53f7/\u54c1\u540d": "\u578b\u53f7A",
                    "\u89c4\u683c": "",
                    "\u5355\u4f4d": "\u5377",
                    "\u6570\u91cf": 1.0,
                    "\u5355\u4ef7": 100.0,
                    "\u91d1\u989d": 100.0,
                    "\u9001\u8d27\u5355\u53f7": "D1",
                    "\u8ba2\u5355\u53f7": "O1",
                },
                {
                    "\u6765\u6e90\u6587\u4ef6": "today.xlsx",
                    "\u5ba2\u6237": "\u56de\u6d41\u5ba2\u6237",
                    "\u578b\u53f7/\u54c1\u540d": "\u578b\u53f7B",
                    "\u89c4\u683c": "",
                    "\u5355\u4f4d": "\u5377",
                    "\u6570\u91cf": 1.0,
                    "\u5355\u4ef7": 200.0,
                    "\u91d1\u989d": 200.0,
                    "\u9001\u8d27\u5355\u53f7": "D2",
                    "\u8ba2\u5355\u53f7": "O2",
                },
            ],
        )
        history_context = {
            "knownCustomersBefore": ["老客户", "沉默客户", "回流客户"],
            "activeCustomersBefore": ["沉默客户"],
            "returningCustomers": ["回流客户"],
            "atRiskCustomers": ["沉默客户"],
        }

        payload = build_dashboard_payload(today, history_context=history_context)

        self.assertEqual(payload["businessAlerts"]["newCustomers"], ["新客户"])
        self.assertEqual(payload["businessAlerts"]["silentCustomers"], ["沉默客户"])
        self.assertEqual(payload["businessAlerts"]["returningCustomers"], ["回流客户"])
        self.assertEqual(payload["businessAlerts"]["atRiskCustomers"], ["沉默客户"])

    def test_write_access_requires_admin_token_in_readonly_mode(self):
        self.assertTrue(is_write_allowed(readonly=False, admin_token="", headers={}, query={}))
        self.assertFalse(is_write_allowed(readonly=True, admin_token="secret", headers={}, query={}))
        self.assertTrue(is_write_allowed(readonly=True, admin_token="secret", headers={"X-Admin-Token": "secret"}, query={}))
        self.assertTrue(is_write_allowed(readonly=True, admin_token="secret", headers={}, query={"adminToken": ["secret"]}))

    def test_save_export_file_writes_under_exports_directory(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            result = save_export_file(Path(tmp), "daily.csv", "a,b\n1,2", "text")

            self.assertTrue(Path(result["path"]).exists())
            self.assertEqual(Path(result["path"]).parent.name, "exports")
            self.assertEqual(Path(result["path"]).read_text(encoding="utf-8-sig"), "a,b\n1,2")

    def test_configure_storage_root_moves_runtime_directories(self):
        import tempfile
        import app_server
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            configure_storage_root(root)

            self.assertEqual(app_server.DATA_DIR.resolve(), (root / "data").resolve())
            self.assertEqual(app_server.REPORT_DIR.resolve(), (root / "reports").resolve())
            self.assertEqual(app_server.UPLOAD_DIR.resolve(), (root / "uploads").resolve())
            self.assertTrue(app_server.DATA_DIR.exists())

    def test_import_checks_report_history_and_detail_sheets(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            workbook = Path(tmp) / "demo.xlsx"
            today = dt.date(2026, 6, 23)
            header = ["客户简称", "内部编码", "型号", "规   格", "单位", "数量", "单价", "金额", "送货日期", "送货单\n号码", "订单号码", "备注"]
            _write_xlsx_named_sheets(
                workbook,
                {
                    HISTORY_SHEET: [header, ["历史客户", "H001", "型号H", "规格H", "卷", 1, 10, 10, excel_serial(today), "H1", "O1", ""]],
                    DETAIL_SHEET: [header, ["今日客户", "D001", "型号D", "规格D", "卷", 2, 20, 40, excel_serial(today), "D1", "O2", ""]],
                },
            )

            checks = _build_import_checks([str(workbook)], today)

            self.assertEqual(checks["status"], "ready")
            self.assertTrue(checks["files"][0]["sheets"][HISTORY_SHEET]["hasSheet"])
            self.assertTrue(checks["files"][0]["sheets"][DETAIL_SHEET]["hasSheet"])
            self.assertTrue(checks["files"][0]["sheets"][HISTORY_SHEET]["hasDateColumn"])
            self.assertTrue(checks["files"][0]["sheets"][DETAIL_SHEET]["hasDateColumn"])

    def test_import_summary_counts_inserted_duplicates_and_errors(self):
        summary = _build_import_summary(
            read_rows=10,
            inserted_rows=7,
            errors=[{"file": "bad.xlsx", "error": "缺少发货明细"}],
        )

        self.assertEqual(summary["readRows"], 10)
        self.assertEqual(summary["insertedRows"], 7)
        self.assertEqual(summary["skippedDuplicateRows"], 3)
        self.assertEqual(summary["errorRows"], 1)
        self.assertIn("读取 10 条", summary["message"])


if __name__ == "__main__":
    unittest.main()
