"""
Scrcpy Process Lifecycle Controller for ARC-LINK.
Manages screen mirroring sessions, screen-off toggles, and performance presets.
"""

from __future__ import annotations

import os
import signal
import subprocess
from typing import List, Optional

from PyQt6.QtCore import QObject, QProcess, pyqtSignal


class ScrcpyPreset:
    """Pre-configured scrcpy argument combinations."""
    STANDARD = ["--stay-awake"]
    LOW_LATENCY = ["--no-audio", "--max-size", "1024", "-b", "4M", "--max-fps", "60"]
    HIGH_QUALITY = ["--max-size", "1920", "-b", "16M", "--max-fps", "60"]
    AUDIO_ONLY = ["--no-video"]


class ScrcpyRunner(QObject):
    """
    Supervises the scrcpy background process.
    Provides graceful termination and state broadcasting.
    """
    # Signals expected by main_window.py
    process_started = pyqtSignal()
    process_finished = pyqtSignal(int)
    error_occurred = pyqtSignal(str)

    # Legacy / alias signals
    started = pyqtSignal(str)   # mode name
    stopped = pyqtSignal()
    error = pyqtSignal(str)     # error message

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._process: Optional[QProcess] = None
        self._active_mode: str = ""
        self._active_endpoint: str = ""

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning

    @property
    def active_mode(self) -> str:
        return self._active_mode

    def launch(
        self,
        endpoint: str,
        flags: Optional[List[str]] = None,
        turn_screen_off: bool = False,
    ) -> bool:
        """
        Launches scrcpy targeting endpoint with custom flags and screen-off toggle.
        """
        if self.is_running:
            self.stop()

        self._active_endpoint = endpoint
        self._active_mode = "SCREEN_OFF" if turn_screen_off else "NORMAL"

        args = ["-s", endpoint]

        if flags:
            for flag in flags:
                if flag not in args:
                    args.append(flag)

        if turn_screen_off:
            for opt in ["--turn-screen-off", "--stay-awake", "--power-off-on-close"]:
                if opt not in args:
                    args.append(opt)

        self._process = QProcess(self)
        self._process.setProgram("scrcpy")
        self._process.setArguments(args)

        self._process.started.connect(self._on_started)
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_error)

        self._process.start()
        return True

    def start(
        self,
        endpoint: str,
        screen_off: bool = False,
        preset: str = "standard",
        custom_flags: Optional[List[str]] = None,
    ) -> bool:
        """
        Spawns scrcpy for the target endpoint using presets.
        """
        flags: List[str] = []
        if preset == "low_latency":
            flags.extend(ScrcpyPreset.LOW_LATENCY)
        elif preset == "high_quality":
            flags.extend(ScrcpyPreset.HIGH_QUALITY)
        elif preset == "audio_only":
            flags.extend(ScrcpyPreset.AUDIO_ONLY)
        else:
            flags.extend(ScrcpyPreset.STANDARD)

        if custom_flags:
            for flag in custom_flags:
                if flag not in flags:
                    flags.append(flag)

        return self.launch(endpoint, flags=flags, turn_screen_off=screen_off)

    def stop(self) -> None:
        """Kills the active scrcpy instance cleanly."""
        if not self.is_running or not self._process:
            return

        pid = self._process.processId()
        self._process.terminate()

        # Wait up to 1.5 seconds for clean exit, otherwise kill forcefully
        if not self._process.waitForFinished(1500):
            if pid > 0:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            self._process.kill()

        self._process = None
        self._active_mode = ""

    def _on_started(self) -> None:
        self.started.emit(self._active_mode)
        self.process_started.emit()

    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        self._process = None
        self._active_mode = ""
        self.stopped.emit()
        self.process_finished.emit(exit_code)

    def _on_error(self, err: QProcess.ProcessError) -> None:
        err_msg = f"scrcpy process error ({err})"
        if self._process:
            stderr = bytes(self._process.readAllStandardError()).decode("utf-8", errors="replace")
            if stderr:
                err_msg += f": {stderr.strip()}"
        self.error.emit(err_msg)
        self.error_occurred.emit(err_msg)
