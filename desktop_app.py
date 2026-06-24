from __future__ import annotations

import os
import base64
import socket
import sys
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path

from app_settings import load_settings, save_settings


APP_NAME = "\u53d1\u8d27\u770b\u677f"


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def find_available_port(preferred: int = 8765) -> int:
    for port in [preferred, *range(8766, 8866)]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def start_dashboard_server(port: int) -> ThreadingHTTPServer:
    root = app_root()
    settings = load_settings(root)
    os.environ.setdefault("SHIPMENT_APP_ROOT", str(root))
    if settings.get("dataDir"):
        os.environ["SHIPMENT_DATA_ROOT"] = settings["dataDir"]
    from app_server import DATA_DIR, REPORT_DIR, STATIC_DIR, UPLOAD_DIR, ShipmentDashboardHandler

    STATIC_DIR.mkdir(exist_ok=True)
    UPLOAD_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)

    server = ThreadingHTTPServer(("127.0.0.1", port), ShipmentDashboardHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


class DesktopApi:
    def __init__(self, root: Path):
        self.root = root

    def get_settings(self) -> dict:
        settings = load_settings(self.root)
        return {"dataDir": settings.get("dataDir") or str(self.root)}

    def choose_data_directory(self) -> dict:
        import webview
        from app_server import STORAGE_ROOT, configure_storage_root

        selected = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG, directory=str(STORAGE_ROOT))
        if not selected:
            return {"cancelled": True, "dataDir": str(STORAGE_ROOT)}
        folder = Path(selected[0]).resolve()
        settings = load_settings(self.root)
        settings["dataDir"] = str(folder)
        save_settings(self.root, settings)
        result = configure_storage_root(folder, migrate_from=STORAGE_ROOT)
        result["cancelled"] = False
        return result

    def save_export_file(self, filename: str, content: str, encoding: str = "text") -> dict:
        import webview
        from app_server import REPORT_DIR

        default_dir = REPORT_DIR / "exports"
        default_dir.mkdir(parents=True, exist_ok=True)
        selected = webview.windows[0].create_file_dialog(
            webview.SAVE_DIALOG,
            directory=str(default_dir),
            save_filename=Path(filename or "export.txt").name,
        )
        if not selected:
            return {"cancelled": True}
        target = Path(selected[0])
        target.parent.mkdir(parents=True, exist_ok=True)
        if encoding == "base64":
            target.write_bytes(base64.b64decode(content))
        else:
            target.write_text(content, encoding="utf-8-sig")
        return {"cancelled": False, "path": str(target), "directory": str(target.parent), "filename": target.name}


def wait_for_server(port: int, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"Dashboard server did not start on port {port}")


def main() -> int:
    port = find_available_port()
    server = start_dashboard_server(port)
    wait_for_server(port)
    url = f"http://127.0.0.1:{port}/"

    import webview

    try:
        webview.create_window(APP_NAME, url, width=1440, height=920, min_size=(1100, 720), js_api=DesktopApi(app_root()))
        webview.start()
    finally:
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
