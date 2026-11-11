"""
Unit tests for ARC-LINK Configuration Manager.
"""

import tempfile
import unittest
from pathlib import Path

from arc_link.core.config import ArcConfig, load_config


class TestConfig(unittest.TestCase):
    def test_default_config(self):
        cfg = ArcConfig()
        self.assertEqual(cfg.network.knock_port, 9099)
        self.assertEqual(cfg.network.default_adb_port, 5555)
        self.assertTrue(cfg.behavior.auto_connect)
        self.assertTrue(cfg.behavior.auto_launch_scrcpy)

    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            conf_path = Path(tmpdir) / "test_config.toml"
            cfg = ArcConfig(config_path=conf_path)
            cfg.auth.shared_secret = "super-secret-key-123"
            cfg.network.knock_port = 9199
            cfg.network.ssid_filter = ["MyPhoneAP", "BackupAP"]
            cfg.save()

            loaded = load_config(conf_path)
            self.assertEqual(loaded.auth.shared_secret, "super-secret-key-123")
            self.assertEqual(loaded.network.knock_port, 9199)
            self.assertEqual(loaded.network.ssid_filter, ["MyPhoneAP", "BackupAP"])


if __name__ == "__main__":
    unittest.main()
