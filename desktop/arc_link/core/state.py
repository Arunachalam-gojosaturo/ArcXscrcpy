"""
Connection State Machine and Data Models for ARC-LINK.
Emits Qt signals on state transitions, logging events, and device stats updates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal


class ConnectionState(Enum):
    """Finite states of the ARC-LINK connection lifecycle."""
    DISCONNECTED = "DISCONNECTED"
    SEARCHING = "SEARCHING"
    KNOCKING = "KNOCKING"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    ERROR = "ERROR"


@dataclass
class DeviceInfo:
    """Live telemetry and system metadata for the target Android device."""
    device_name: str = "Android Device"
    model: str = "Unknown Model"
    manufacturer: str = "Generic"
    android_version: str = "Unknown"
    ip: str = "0.0.0.0"
    port: int = 5555
    battery_level: int = -1
    is_charging: bool = False
    storage_free: str = "N/A"
    uptime: str = "N/A"
    last_seen: float = 0.0

    @property
    def endpoint(self) -> str:
        return f"{self.ip}:{self.port}"


class StateManager(QObject):
    """
    Central state coordinator.
    Thread-safe publisher for UI components and background tasks.
    """
    # Signals
    state_changed = pyqtSignal(object, str)            # (ConnectionState, reason/step text)
    device_info_updated = pyqtSignal(object)           # (DeviceInfo)
    log_message = pyqtSignal(str, str)                 # (text, level: INFO|SUCCESS|WARN|ERROR|DEBUG)
    hotspot_changed = pyqtSignal(str, str, str, int)   # (iface, gateway, ssid, signal)
    scrcpy_state_changed = pyqtSignal(bool, str)       # (is_running, mode)
    sniffer_state_changed = pyqtSignal(bool)           # (is_running)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._current_state = ConnectionState.DISCONNECTED
        self._device_info = DeviceInfo()
        self._step_description = "Ready to connect"

    @property
    def current_state(self) -> ConnectionState:
        return self._current_state

    @property
    def state(self) -> ConnectionState:
        return self._current_state

    @property
    def device_info(self) -> DeviceInfo:
        return self._device_info

    @property
    def step_description(self) -> str:
        return self._step_description

    def set_state(self, new_state: ConnectionState, reason: str = "") -> None:
        """Transitions state and emits change notification."""
        old_state = self._current_state
        self._current_state = new_state
        self._step_description = reason or new_state.value
        self.state_changed.emit(new_state, self._step_description)

        level = "INFO"
        if new_state == ConnectionState.CONNECTED:
            level = "SUCCESS"
        elif new_state == ConnectionState.ERROR:
            level = "ERROR"
        elif new_state in (ConnectionState.SEARCHING, ConnectionState.KNOCKING):
            level = "DEBUG"

        msg = f"State transitioned: {old_state.value} -> {new_state.value}"
        if reason:
            msg += f" ({reason})"
        self.log(msg, level)

    def to_searching(self, msg: str = "Searching for phone...") -> None:
        self.set_state(ConnectionState.SEARCHING, msg)

    def to_knocking(self, msg: str = "Knocking...") -> None:
        self.set_state(ConnectionState.KNOCKING, msg)

    def to_connecting(self, msg: str = "Connecting...") -> None:
        self.set_state(ConnectionState.CONNECTING, msg)

    def to_connected(self, endpoint: str = "") -> None:
        self.set_state(ConnectionState.CONNECTED, f"Connected to {endpoint}" if endpoint else "Connected")

    def to_disconnected(self, msg: str = "Disconnected") -> None:
        self.set_state(ConnectionState.DISCONNECTED, msg)

    def to_error(self, msg: str = "Error") -> None:
        self.set_state(ConnectionState.ERROR, msg)

    def update_device_info(self, info: DeviceInfo) -> None:
        """Updates internal device info cache and emits signal."""
        self._device_info = info
        self.device_info_updated.emit(info)

    def log(self, text: str, level: str = "INFO") -> None:
        """Publishes a log entry to the UI console."""
        self.log_message.emit(text, level.upper())


# Alias for explicit naming
ConnectionStateMachine = StateManager
