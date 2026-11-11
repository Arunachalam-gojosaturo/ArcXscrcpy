"""
Scapy Packet Sniffer Controller for ARC-LINK.
Manages the privileged sniffer helper via pkexec and streams packet metrics
into the desktop UI table.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional

from PyQt6.QtCore import QThread, pyqtSignal


class SnifferWorker(QThread):
    """
    Spawns pkexec arc-link-sniffer and emits packet_captured for each parsed frame.
    """
    packet_captured = pyqtSignal(dict)   # {time, src, dst, proto, length, summary}
    sniffer_started = pyqtSignal()
    sniffer_stopped = pyqtSignal(str)    # reason / message

    def __init__(
        self,
        interface: str,
        target_ip: str = "",
        parent: Optional[QThread] = None,
    ) -> None:
        super().__init__(parent)
        self.interface = interface
        self.target_ip = target_ip
        self._process: Optional[subprocess.Popen] = None
        self._running = True

    def stop(self) -> None:
        """Stops the sniffer subprocess gracefully."""
        self._running = False
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=1.0)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None
        self.wait(2000)

    def run(self) -> None:
        # Determine helper script location
        helper_path = "/usr/lib/arc-link/arc-link-sniffer"
        if not os.path.exists(helper_path):
            # Development fallback: use local sniffer_helper.py directly
            local_helper = Path(__file__).parent / "sniffer_helper.py"
            if local_helper.exists():
                helper_path = str(local_helper.resolve())
            else:
                self.sniffer_stopped.emit(f"Sniffer helper executable not found at {helper_path}")
                return

        # Prepare execution command
        if shutil.which("pkexec"):
            cmd = ["pkexec", sys.executable, helper_path, self.interface]
        else:
            cmd = [sys.executable, helper_path, self.interface]

        if self.target_ip:
            cmd.append(self.target_ip)

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            self.sniffer_started.emit()

            while self._running and self._process and self._process.stdout:
                line = self._process.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    self.packet_captured.emit(record)
                except json.JSONDecodeError:
                    continue

        except Exception as e:
            self.sniffer_stopped.emit(f"Sniffer execution error: {e}")
            return
        finally:
            if self._process:
                try:
                    self._process.terminate()
                except Exception:
                    pass
            self.sniffer_stopped.emit("Sniffer stopped")
