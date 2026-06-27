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

    def test_load_monthly_inventory_catalog_derives_category_from_product_spec(self):
        with tempfile.TemporaryDirectory() as tmp:
            workbook = Path(tmp) / "inventory.xlsx"
            _write_xlsx_named_sheets(
                workbook,
                {
                    "进出存月报表": [
                        ["标题"],
                        ["原产品名称", "原规格", "新产品名称", "新规格", "产品编码", "产品名称", "产品规格", "单位"],
                        ["", "", "", "", "F2A012", "纯胶膜", "AE15P-25KA（W250）", "㎡"],
                        ["", "", "", "", "CS3513", "KEF-EHFAM2035S1", "单面基材EHF252035+KTS-AH0800X3-131", "㎡"],
                        ["", "", "", "", "ASJ2001", "KTS-PI2025SIH1-2", "SKC补强，PI=2mil,AD=25um,W250mm", "㎡"],
                    ]
                },
            )

            catalog = load_material_catalog(workbook)

            self.assertEqual(catalog["F2A012"], "纯胶")
            self.assertEqual(catalog["纯胶膜"], "纯胶")
            self.assertEqual(catalog["AE15P-25KA（W250）"], "纯胶")
            self.assertEqual(catalog["CS3513"], "基材")
            self.assertEqual(catalog["KEF-EHFAM2035S1"], "基材")
            self.assertEqual(catalog["ASJ2001"], "补强")
            self.assertEqual(catalog["KTS-PI2025SIH1-2"], "补强")

    def test_classify_material_prefers_catalog_over_keywords(self):
        catalog = {"AU-25KA": "覆盖膜"}
        rules = [{"name": "基材", "keywords": ["AU"]}]

        self.assertEqual(classify_material("AU-25KA", "", catalog, rules), "覆盖膜")

    def test_classify_material_uses_spec_keywords_for_pure_glue_and_base_material(self):
        rules = []

        self.assertEqual(classify_material("纯胶膜", "AE15P-25KA（W250）", {}, rules), "纯胶")
        self.assertEqual(classify_material("KEF-EHFAM2035S1", "单面基材EHF252035", {}, rules), "基材")

    def test_classify_material_ignores_generic_catalog_tokens_and_uses_model_family(self):
        catalog = {
            "0": "纯胶",
            "PI=8mil,AD=25um": "纯胶",
            "PI=5mil,AD=25um": "纯胶",
            "PI=12mil,AD=25um": "纯胶",
            "25um": "纯胶",
            "KTS-PI9000SXX1-222": "补强",
            "OKT-PI3025(U)": "补强",
            "OKT-PI8025(U)": "补强",
            "OKT-PI8000(A)": "补强",
            "OKT-PI5025(U)": "补强",
            "OKT-PI12025(U)-6": "补强",
        }

        self.assertEqual(classify_material("KTS-PI9000(U)", "PI=9mil", catalog, []), "补强")
        self.assertEqual(classify_material("KTS-9000(U)", "PI=9mil", catalog, []), "补强")
        self.assertEqual(classify_material("OKT-PI3025(U)", "PI=3mil,AD=25um", catalog, []), "补强")
        self.assertEqual(classify_material("OKT-PI8025(S)", "PI=8mil,AD=25um", catalog, []), "补强")
        self.assertEqual(classify_material("OKT-PI8000(S)", "PI=8mil", catalog, []), "补强")
        self.assertEqual(classify_material("OKT-PI5025(S)", "PI=5mil,AD=25um", catalog, []), "补强")
        self.assertEqual(classify_material("OKT-PI12025(S) W500", "PI=12mil,AD=25um", catalog, []), "补强")

    def test_classify_material_handles_known_legacy_coverlay_model(self):
        catalog = {"0": "纯胶"}

        self.assertEqual(classify_material("OKT-PI2045(F) W250*200M", "PI=2mil,AD=45um", catalog, []), "覆盖膜")

    def test_classify_material_treats_okt_fwm_roll_models_as_coverlay(self):
        catalog = {
            "OKT-PI2050(F)方舟PI-补强胶-黄纸-未电晕 W250": "补强",
            "OKT-PI1045(W)": "补强",
            "OKT-PI2025(U)": "补强",
        }

        self.assertEqual(classify_material("OKT-PI2050(F) W250*200M", "PI=2mil,AD=50um", catalog, []), "覆盖膜")
        self.assertEqual(classify_material("OKT-PI1045(W) W250*200M", "PI=1mil,AD=45um", catalog, []), "覆盖膜")
        self.assertEqual(classify_material("OKT-PI2025(M) W250*200M", "PI=2mil,AD=25um", catalog, []), "覆盖膜")
        self.assertEqual(classify_material("OKT-PI8025(S)", "PI=8mil,AD=25um", catalog, []), "补强")

    def test_classify_material_handles_common_real_world_model_families(self):
        self.assertEqual(classify_material("PFEKE 1025PT", "PI=25um AD=25um", {}, []), "覆盖膜")
        self.assertEqual(classify_material("生产耗材 薄膜 27.5μm PFEKE 0515PT 100 m 250 mm", "", {}, []), "覆盖膜")
        self.assertEqual(classify_material("PFGKE 0515PT", "PI=12.5um AD=15um", {}, []), "覆盖膜")
        self.assertEqual(classify_material("PFEKN 0506PT", "PI=12.5um AD=6um", {}, []), "覆盖膜")
        self.assertEqual(classify_material("代工PET环氧盖膜", "PET=50um,Ad=30um", {}, []), "覆盖膜")
        self.assertEqual(classify_material("CJAW1025/25KA", "500mm*100m", {}, []), "覆盖膜")
        self.assertEqual(classify_material("AU-25KA   1.02.01.0045", "250mm*200M", {}, []), "纯胶")
        self.assertEqual(classify_material("OKT-PI4000(U)", "PI=4mil", {}, []), "补强")
        self.assertEqual(classify_material("FNUT8025", "PI=8mil", {}, []), "补强")
        self.assertEqual(classify_material("UPILEX-125S W514", "PI=5mil", {}, []), "补强")
        self.assertEqual(classify_material("GF300", "W514", {}, []), "补强")
        self.assertEqual(classify_material("GD100A", "PI=1mil", {}, []), "补强")
        self.assertEqual(classify_material("IK70 25um", "W514", {}, []), "补强")
        self.assertEqual(classify_material("软性覆铜板", "IF-2LD2512CR1", {}, []), "基材")
        self.assertEqual(classify_material("KEF-SHJ131218D1", "半对半黑化电解铜", {}, []), "基材")
        self.assertEqual(classify_material("RTA M25PE", "W256*110M", {}, []), "基材")


if __name__ == "__main__":
    unittest.main()
