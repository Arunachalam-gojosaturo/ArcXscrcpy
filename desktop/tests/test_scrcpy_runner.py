"""
Unit tests for ScrcpyRunner.
"""

import sys
import unittest

from PyQt6.QtCore import QCoreApplication

from arc_link.core.scrcpy_runner import ScrcpyRunner


class TestScrcpyRunner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication(sys.argv)

    def test_signals_and_attributes_exist(self):
        runner = ScrcpyRunner()
        self.assertTrue(hasattr(runner, "process_started"))
        self.assertTrue(hasattr(runner, "process_finished"))
        self.assertTrue(hasattr(runner, "error_occurred"))
        self.assertTrue(hasattr(runner, "started"))
        self.assertTrue(hasattr(runner, "stopped"))
        self.assertTrue(hasattr(runner, "error"))
        self.assertTrue(hasattr(runner, "launch"))
        self.assertTrue(hasattr(runner, "start"))
        self.assertTrue(hasattr(runner, "stop"))
        self.assertFalse(runner.is_running)


if __name__ == "__main__":
    unittest.main()
