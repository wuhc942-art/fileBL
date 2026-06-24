import tempfile
import unittest
from pathlib import Path

from app_settings import load_settings, save_settings


class AppSettingsTest(unittest.TestCase):
    def test_load_and_save_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(load_settings(root), {})

            save_settings(root, {"dataDir": "D:/shipment-data"})

            self.assertEqual(load_settings(root)["dataDir"], "D:/shipment-data")


if __name__ == "__main__":
    unittest.main()
