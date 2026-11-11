"""
Unit tests for ARC-LINK Discovery Engine.
"""

import unittest
from unittest.mock import MagicMock, patch

from arc_link.core.config import ArcConfig
from arc_link.core.discovery import DiscoveredTarget, DiscoveryEngine


class TestDiscoveryEngine(unittest.TestCase):
    def setUp(self):
        self.logs = []
        self.engine = DiscoveryEngine(log_callback=lambda msg, lvl: self.logs.append((lvl, msg)))
        self.config = ArcConfig()
        self.config.auth.shared_secret = "test-secret"

    def test_discovered_target_endpoint(self):
        target = DiscoveredTarget(
            ip="192.168.43.1",
            port=38421,
            source="KNOCK",
            device_name="Pixel 7",
            model="Pixel",
        )
        self.assertEqual(target.endpoint, "192.168.43.1:38421")

    @patch("arc_link.core.discovery.subprocess.run")
    def test_mdns_discovery_parsing(self, mock_subproc):
        mock_output = (
            "List of discovered mdns services\n"
            "adb-192.168.43.1:41235-abcdef    _adb-tls-connect._tcp.    192.168.43.1:41235\n"
        )
        mock_subproc.return_value = MagicMock(stdout=mock_output, returncode=0)

        target = self.engine._discover_mdns("192.168.43.1")
        self.assertIsNotNone(target)
        self.assertEqual(target.ip, "192.168.43.1")
        self.assertEqual(target.port, 41235)
        self.assertEqual(target.source, "MDNS")

    @patch("arc_link.core.discovery.socket.socket")
    def test_tcp_port_check_open(self, mock_socket_cls):
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0
        mock_socket_cls.return_value = mock_sock

        is_open = self.engine._check_tcp_port("192.168.43.1", 5555)
        self.assertTrue(is_open)

    @patch("arc_link.core.discovery.socket.socket")
    def test_tcp_port_check_closed(self, mock_socket_cls):
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 111  # Connection refused
        mock_socket_cls.return_value = mock_sock

        is_open = self.engine._check_tcp_port("192.168.43.1", 5555)
        self.assertFalse(is_open)


if __name__ == "__main__":
    unittest.main()
