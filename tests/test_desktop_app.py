import socket
import unittest

from desktop_app import find_available_port


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


if __name__ == "__main__":
    unittest.main()
