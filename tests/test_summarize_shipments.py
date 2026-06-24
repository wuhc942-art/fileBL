import datetime as dt
import unittest
import zipfile
from pathlib import Path

from summarize_shipments import extract_all_shipments, summarize_sources, excel_serial


NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def _cell_ref(col, row):
    letters = ""
    while col:
        col, rem = divmod(col - 1, 26)
        letters = chr(65 + rem) + letters
    return f"{letters}{row}"


def _sheet_xml(rows):
    out = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        f'<worksheet xmlns="{NS}"><sheetData>',
    ]
    for r_idx, row in enumerate(rows, 1):
        out.append(f'<row r="{r_idx}">')
        for c_idx, value in enumerate(row, 1):
            ref = _cell_ref(c_idx, r_idx)
            if value is None:
                continue
            if isinstance(value, (int, float)):
                out.append(f'<c r="{ref}"><v>{value}</v></c>')
            else:
                escaped = (
                    str(value)
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                out.append(f'<c r="{ref}" t="inlineStr"><is><t>{escaped}</t></is></c>')
        out.append("</row>")
    out.append("</sheetData></worksheet>")
    return "".join(out)


def _write_xlsx(path: Path, rows):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""",
        )
        z.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        )
        z.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="发货明细" sheetId="1" r:id="rId1"/></sheets>
</workbook>""",
        )
        z.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""",
        )
        z.writestr("xl/worksheets/sheet1.xml", _sheet_xml(rows))


def _write_xlsx_named_sheets(path: Path, sheets: dict[str, list[list]]):
    sheet_items = list(sheets.items())
    overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for i in range(1, len(sheet_items) + 1)
    )
    sheet_nodes = "".join(
        f'<sheet name="{name}" sheetId="{i}" r:id="rId{i}"/>'
        for i, (name, _) in enumerate(sheet_items, 1)
    )
    rel_nodes = "".join(
        f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
        for i in range(1, len(sheet_items) + 1)
    )
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(
            "[Content_Types].xml",
            f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
{overrides}
</Types>""",
        )
        z.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        )
        z.writestr(
            "xl/workbook.xml",
            f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets>{sheet_nodes}</sheets>
</workbook>""",
        )
        z.writestr(
            "xl/_rels/workbook.xml.rels",
            f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
{rel_nodes}
</Relationships>""",
        )
        for i, (_, rows) in enumerate(sheet_items, 1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", _sheet_xml(rows))


class SummarizeShipmentsTest(unittest.TestCase):
    def test_summarize_sources_filters_today_and_totals(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            workbook = Path(tmp) / "demo.xlsx"
            today = dt.date(2026, 6, 23)
            _write_xlsx(
                workbook,
                [
                    ["6月份", "销售录入"],
                    [""],
                    ["客户简称", "内部编码", "品  名", "规   格", "单位", "数量", "单价", "金额", "送货日期", "送货单\n号码", "订单号码", "备注"],
                    ["客户A", "A001", "型号A", "规格A", "㎡", 2, 10, 20, excel_serial(today), "D1", "O1", "今天"],
                    ["客户B", "B001", "型号B", "规格B", "㎡", 3, 20, 60, excel_serial(today + dt.timedelta(days=1)), "D2", "O2", "明天"],
                    ["客户A", "A002", "型号C", "规格C", "张", 5, 6, 30, excel_serial(today), "D3", "O3", "今天"],
                ],
            )

            result = summarize_sources([workbook], today)

            self.assertEqual(result.total_rows, 2)
            self.assertEqual(result.total_amount, 50)
            self.assertEqual(result.customer_count, 1)
            self.assertEqual([row["客户"] for row in result.rows], ["客户A", "客户A"])
            self.assertEqual(result.by_customer[0]["客户"], "客户A")
            self.assertEqual(result.by_customer[0]["金额"], 50)
            self.assertEqual(result.by_customer[0]["数量"], 7)

    def test_extract_all_shipments_reads_history_dates_from_detail_sheet(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            workbook = Path(tmp) / "history.xlsx"
            today = dt.date(2026, 6, 23)
            _write_xlsx(
                workbook,
                [
                    ["6月份", "销售录入"],
                    [""],
                    ["客户简称", "内部编码", "品  名", "规   格", "单位", "数量", "单价", "金额", "送货日期", "送货单\n号码", "订单号码", "备注"],
                    ["客户A", "A001", "型号A", "规格A", "卷", 2, 10, 20, excel_serial(today), "D1", "O1", "今天"],
                    ["客户B", "B001", "型号B", "规格B", "卷", 3, 20, 60, excel_serial(today - dt.timedelta(days=8)), "D2", "O2", "历史"],
                    ["", "", "", "", "", "", "", "", "", "", "", ""],
                ],
            )

            rows = extract_all_shipments(workbook)
            result = summarize_sources([workbook], today)

            self.assertEqual(len(rows), 2)
            self.assertEqual({row["送货日期"] for row in rows}, {today, today - dt.timedelta(days=8)})
            self.assertEqual(result.total_rows, 1)
            self.assertEqual(result.total_amount, 20)

    def test_extract_all_shipments_reads_history_record_sheet_and_deduplicates(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            workbook = Path(tmp) / "history-sheet.xlsx"
            today = dt.date(2026, 6, 23)
            older = today - dt.timedelta(days=30)
            header = ["客户简称", "送货单\n号码", "订单号码", "内部编码", "型号", "规   格", "单位", "数量", "单价", "金额", "送货日期", "备注"]
            duplicate = ["客户A", "D1", "O1", "A001", "型号A", "规格A", "卷", 2, 10, 20, excel_serial(today), "重复"]
            _write_xlsx_named_sheets(
                workbook,
                {
                    "发货历史记录": [
                        header,
                        ["客户历史", "D0", "O0", "H001", "型号H", "规格H", "卷", 3, 20, 60, excel_serial(older), "历史"],
                        duplicate,
                    ],
                    "发货明细": [
                        ["6月份"],
                        [""],
                        header,
                        duplicate,
                    ],
                },
            )

            rows = extract_all_shipments(workbook)
            today_result = summarize_sources([workbook], today)
            older_result = summarize_sources([workbook], older)

            self.assertEqual(len(rows), 2)
            self.assertEqual(today_result.total_rows, 1)
            self.assertEqual(today_result.total_amount, 20)
            self.assertEqual(older_result.total_rows, 1)
            self.assertEqual(older_result.rows[0]["客户"], "客户历史")

    def test_pure_adhesive_film_uses_spec_as_product_name(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            workbook = Path(tmp) / "demo.xlsx"
            today = dt.date(2026, 6, 23)
            _write_xlsx(
                workbook,
                [
                    ["6月份", "销售录入"],
                    [""],
                    ["客户简称", "内部编码", "品  名", "规   格", "单位", "数量", "单价", "金额", "送货日期", "送货单\n号码", "订单号码", "备注"],
                    ["客户A", "F001", "纯胶膜", "AU-15KA（W248）", "㎡", 2, 10, 20, excel_serial(today), "D1", "O1", ""],
                    ["客户A", "F002", "纯胶膜", "AU-25KA (W500)", "㎡", 3, 20, 60, excel_serial(today), "D2", "O2", ""],
                ],
            )

            result = summarize_sources([workbook], today)

            self.assertEqual(result.rows[0]["型号/品名"], "纯胶膜 / AU-15KA（W248）")
            self.assertEqual(result.rows[1]["型号/品名"], "纯胶膜 / AU-25KA (W500)")


if __name__ == "__main__":
    unittest.main()
