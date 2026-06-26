import tempfile
import unittest
from pathlib import Path

from material_catalog import classify_material, load_material_catalog
from tests.test_summarize_shipments import _write_xlsx_named_sheets


class MaterialCatalogTest(unittest.TestCase):
    def test_load_material_catalog_detects_product_and_category_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            workbook = Path(tmp) / "catalog.xlsx"
            _write_xlsx_named_sheets(
                workbook,
                {
                    "库存": [
                        ["序号", "产品名称", "材料类型", "库存"],
                        [1, "AU-25KA", "覆盖膜", 10],
                        [2, "FR4补强板", "补强", 5],
                        [3, "PI基材12.5", "基材", 8],
                    ]
                },
            )

            catalog = load_material_catalog(workbook)

            self.assertEqual(catalog["AU-25KA"], "覆盖膜")
            self.assertEqual(catalog["FR4补强板"], "补强")
            self.assertEqual(catalog["PI基材12.5"], "基材")

    def test_classify_material_prefers_catalog_over_keywords(self):
        catalog = {"AU-25KA": "覆盖膜"}
        rules = [{"name": "基材", "keywords": ["AU"]}]

        self.assertEqual(classify_material("AU-25KA", "", catalog, rules), "覆盖膜")


if __name__ == "__main__":
    unittest.main()
