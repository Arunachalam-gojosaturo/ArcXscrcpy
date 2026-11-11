"""
Unit tests for ARC-LINK Connection State Machine.
"""

import sys
import unittest

from PyQt6.QtCore import QCoreApplication

from arc_link.core.state import ConnectionState, ConnectionStateMachine, DeviceInfo


class TestConnectionStateMachine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # QCoreApplication instance is required for Qt signals/slots
        cls.app = QCoreApplication.instance() or QCoreApplication(sys.argv)

    def test_initial_state(self):
        sm = ConnectionStateMachine()
        self.assertEqual(sm.state, ConnectionState.DISCONNECTED)
        self.assertEqual(sm.current_state, ConnectionState.DISCONNECTED)

    def test_transitions(self):
        sm = ConnectionStateMachine()
        transitions = []

        sm.state_changed.connect(lambda s, desc: transitions.append((s, desc)))

        sm.to_searching("Scanning Wi-Fi gateway")
        self.assertEqual(sm.state, ConnectionState.SEARCHING)

        sm.to_knocking("Sending UDP datagram")
        self.assertEqual(sm.state, ConnectionState.KNOCKING)

        sm.to_connecting("Running adb connect")
        self.assertEqual(sm.state, ConnectionState.CONNECTING)

        sm.to_connected("192.168.43.1:39451")
        self.assertEqual(sm.state, ConnectionState.CONNECTED)

        sm.to_disconnected("Session terminated")
        self.assertEqual(sm.state, ConnectionState.DISCONNECTED)

        self.assertEqual(len(transitions), 5)
        self.assertEqual(transitions[0][0], ConnectionState.SEARCHING)
        self.assertEqual(transitions[3][0], ConnectionState.CONNECTED)
        self.assertEqual(transitions[4][0], ConnectionState.DISCONNECTED)

    def test_device_info_update(self):
        sm = ConnectionStateMachine()
        received = []
        sm.device_info_updated.connect(lambda info: received.append(info))

        dev = DeviceInfo(device_name="Pixel Test", battery_level=90)
        sm.update_device_info(dev)

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].device_name, "Pixel Test")
        self.assertEqual(received[0].battery_level, 90)


if __name__ == "__main__":
    unittest.main()
