"""
Unit tests for ARC-LINK UDP Knock Client and Protocol.
"""

import json
import socket
import threading
import unittest

from arc_link.core.knock import KnockClient, KnockReply


class TestKnockProtocol(unittest.TestCase):
    def test_knock_reply_dataclass(self):
        data = {
            "device_name": "Pixel 7 Pro",
            "model": "GE2AE",
            "ip": "192.168.43.1",
            "adb_port": 39451,
            "adb_wifi_enabled": True,
            "hotspot": True,
            "battery": 88,
        }
        reply = KnockReply.from_dict(data, responder_ip="10.170.47.96")
        self.assertEqual(reply.device_name, "Pixel 7 Pro")
        self.assertEqual(reply.adb_port, 39451)
        self.assertTrue(reply.adb_wifi_enabled)
        self.assertEqual(reply.battery, 88)
        self.assertEqual(reply.responder_ip, "10.170.47.96")

    def test_mock_udp_knock_exchange(self):
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_sock.bind(("127.0.0.1", 0))
        port = server_sock.getsockname()[1]

        received_packets = []

        def server_loop():
            try:
                server_sock.settimeout(2.0)
                data, addr = server_sock.recvfrom(1024)
                received_packets.append(data.decode("utf-8"))
                response = {
                    "device_name": "MockPhone",
                    "model": "TEST-01",
                    "ip": "127.0.0.1",
                    "adb_port": 42424,
                    "adb_wifi_enabled": True,
                    "hotspot": True,
                    "battery": 95,
                }
                server_sock.sendto(json.dumps(response).encode("utf-8"), addr)
            except Exception:
                pass
            finally:
                server_sock.close()

        th = threading.Thread(target=server_loop)
        th.start()

        client = KnockClient(port=port, timeout=1.5)
        reply = client.knock("127.0.0.1", "test-secret")

        th.join()

        self.assertEqual(len(received_packets), 1)
        self.assertEqual(received_packets[0], "ARCX-KNOCK:test-secret")
        self.assertIsNotNone(reply)
        self.assertEqual(reply.device_name, "MockPhone")
        self.assertEqual(reply.adb_port, 42424)


if __name__ == "__main__":
    unittest.main()
