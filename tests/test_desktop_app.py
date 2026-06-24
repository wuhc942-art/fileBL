import json
import socket
import tempfile
import unittest
import zipfile
from pathlib import Path

from desktop_app import create_data_backup, find_available_port, restore_data_backup


class DesktopAppTest(unittest.TestCase):
    def test_find_available_port_skips_used_port(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        used_port = sock.getsockname()[1]
        try:
            port = find_available_port(used_port)
            self.assertNotEqual(port, used_port)
            self.assertGreater(port, 0)
        finally:
            sock.close()

    def test_create_data_backup_includes_history_database_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "app"
            storage = Path(tmp) / "storage"
            target = Path(tmp) / "backup.zip"
            (storage / "data").mkdir(parents=True)
            (storage / "data" / "history.sqlite").write_bytes(b"history-db")
            root.mkdir()

            result = create_data_backup(root, storage, target)

            self.assertEqual(Path(result["path"]).resolve(), target.resolve())
            with zipfile.ZipFile(target) as archive:
                self.assertEqual(archive.read("data/history.sqlite"), b"history-db")
                metadata = json.loads(archive.read("backup-info.json").decode("utf-8"))
            self.assertEqual(metadata["app"], "shipment-dashboard")
            self.assertEqual(metadata["storageRoot"], str(storage.resolve()))

    def test_restore_data_backup_restores_history_database_to_current_storage(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_storage = Path(tmp) / "source-storage"
            restore_storage = Path(tmp) / "restore-storage"
            backup = Path(tmp) / "backup.zip"
            (source_storage / "data").mkdir(parents=True)
            (source_storage / "data" / "history.sqlite").write_bytes(b"backup-db")
            create_data_backup(Path(tmp) / "app", source_storage, backup)

            result = restore_data_backup(backup, restore_storage)

            self.assertEqual(result["historyDb"], str((restore_storage / "data" / "history.sqlite").resolve()))
            self.assertEqual((restore_storage / "data" / "history.sqlite").read_bytes(), b"backup-db")


if __name__ == "__main__":
    unittest.main()
