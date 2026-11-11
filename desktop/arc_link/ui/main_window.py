"""
ARC-LINK Desktop Main Window.
Coordinates Cyber-HUD interface, connection state machine, ADB telemetry,
scrcpy streaming, and Scapy packet capture.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from PyQt6.QtCore import QKeyCombination, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QCloseEvent, QFont, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedLayout,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from arc_link.core.adb_manager import AdbDeviceManager
from arc_link.core.config import ArcConfig, load_config
from arc_link.core.discovery import DeviceDiscoveryWorker
from arc_link.core.hotspot_watcher import HotspotWatcher
from arc_link.core.scrcpy_runner import ScrcpyRunner
from arc_link.core.sniffer import SnifferWorker
from arc_link.core.state import ConnectionState, ConnectionStateMachine
from arc_link.ui.pairing_dialog import PairingDialog
from arc_link.ui.settings_dialog import SettingsDialog
from arc_link.ui.tokens import COLORS, GEOMETRY
from arc_link.ui.tray import ArcTrayIcon
from arc_link.ui.widgets.action_card import ActionCard
from arc_link.ui.widgets.device_card import DeviceCard
from arc_link.ui.widgets.glow_pill import GlowPill
from arc_link.ui.widgets.log_console import LogConsole
from arc_link.ui.widgets.packet_table import PacketTable
from arc_link.ui.widgets.preset_selector import PresetSelector
from arc_link.ui.widgets.progress_ring import ProgressRing


class MainWindow(QMainWindow):
    """
    ARC-LINK Primary User Interface.
    """

    def __init__(self, config: Optional[ArcConfig] = None) -> None:
        super().__init__()
        self.config = config or load_config()

        self.setWindowTitle("ARC-LINK — Autonomous Screen Recovery")
        self.resize(1020, 820)
        self.setMinimumSize(900, 700)

        # Startup time for footer uptime counter
        self._start_time = time.time()
        self._active_endpoint: str = ""

        # Core subsystem instances
        self.state_machine = ConnectionStateMachine()
        self.adb_manager = AdbDeviceManager()
        self.scrcpy_runner = ScrcpyRunner()
        self.discovery_worker: Optional[DeviceDiscoveryWorker] = None
        self.sniffer_worker: Optional[SnifferWorker] = None

        # Watcher for hotspot network interface
        self.hotspot_watcher = HotspotWatcher(
            interface_override=self.config.network.interface_override,
            ssid_filter=self.config.network.ssid_filter,
        )

        # Telemetry refresh timer (5 seconds)
        self._telemetry_timer = QTimer(self)
        self._telemetry_timer.setInterval(5000)
        self._telemetry_timer.timeout.connect(self._refresh_telemetry)

        # Uptime tick timer (1 second)
        self._uptime_timer = QTimer(self)
        self._uptime_timer.setInterval(1000)
        self._uptime_timer.timeout.connect(self._update_footer_uptime)
        self._uptime_timer.start()

        # Build UI layout
        self._setup_ui()
        self._setup_shortcuts()
        self._setup_tray()
        self._bind_signals()

        # Start Hotspot Watcher
        self.hotspot_watcher.start()

        self.console.log("INFO", "ARC-LINK Desktop Initialized.")
        self.console.log("INFO", f"Config loaded. Shared secret armed (UDP port {self.config.network.knock_port}).")

        # Initial autoconnect check
        if self.config.behavior.auto_connect and self.hotspot_watcher.is_connected:
            self.console.log("INFO", f"Hotspot {self.hotspot_watcher.current_ssid} detected on start. Auto-connecting...")
            self.start_connection_flow()

    def _setup_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(24, 20, 24, 16)
        root_layout.setSpacing(16)

        # ==========================================
        # 1. HEADER ROW
        # ==========================================
        header_layout = QHBoxLayout()
        header_layout.setSpacing(14)

        # Logo & App Title
        logo_box = QVBoxLayout()
        logo_box.setSpacing(2)

        lbl_logo = QLabel("ARC-LINK", self)
        lbl_logo.setFont(QFont("Orbitron", 16, QFont.Weight.ExtraBold))
        lbl_logo.setStyleSheet(f"color: {COLORS.CYAN_PRIMARY}; letter-spacing: 2px;")
        logo_box.addWidget(lbl_logo)

        lbl_sub = QLabel("Autonomous Wireless ADB / scrcpy Bridge", self)
        lbl_sub.setFont(QFont("Inter", 9))
        lbl_sub.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY};")
        logo_box.addWidget(lbl_sub)

        header_layout.addLayout(logo_box)
        header_layout.addStretch()

        # Hotspot Info Pill
        self.lbl_hotspot_info = QLabel("Wi-Fi: Disconnected", self)
        self.lbl_hotspot_info.setFont(QFont("JetBrains Mono", 9, QFont.Weight.Bold))
        self.lbl_hotspot_info.setStyleSheet(
            f"background: rgba(255, 255, 255, 0.05); color: {COLORS.TEXT_SECONDARY}; "
            f"border: 1px solid rgba(255, 255, 255, 0.10); border-radius: 17px; padding: 6px 14px;"
        )
        header_layout.addWidget(self.lbl_hotspot_info)

        # Connection State Glow Pill
        self.pill_state = GlowPill(self)
        header_layout.addWidget(self.pill_state)

        root_layout.addLayout(header_layout)

        # ==========================================
        # 2. DEVICE TELEMETRY CARD (Glassmorphism)
        # ==========================================
        self.device_card = DeviceCard(self)
        root_layout.addWidget(self.device_card)

        # ==========================================
        # 3. PRIMARY CONTROL ROW (Big Connect/Disconnect + Step text)
        # ==========================================
        control_card = QFrame(self)
        control_card.setObjectName("control_card")
        control_card.setStyleSheet(
            f"#control_card {{ background: rgba(13, 18, 36, 0.60); border: 1px solid rgba(255, 255, 255, 0.10); "
            f"border-radius: 14px; padding: 10px; }}"
        )
        ctrl_layout = QHBoxLayout(control_card)
        ctrl_layout.setContentsMargins(14, 10, 14, 10)
        ctrl_layout.setSpacing(14)

        self.btn_connect = QPushButton("CONNECT PHONE", self)
        self.btn_connect.setObjectName("btn_connect")
        self.btn_connect.setMinimumHeight(44)
        self.btn_connect.clicked.connect(self.start_connection_flow)
        ctrl_layout.addWidget(self.btn_connect)

        self.btn_disconnect = QPushButton("DISCONNECT", self)
        self.btn_disconnect.setObjectName("btn_disconnect")
        self.btn_disconnect.setMinimumHeight(44)
        self.btn_disconnect.setEnabled(False)
        self.btn_disconnect.clicked.connect(self.disconnect_flow)
        ctrl_layout.addWidget(self.btn_disconnect)

        # Progress Ring & Step Message
        self.spinner = ProgressRing(self, size=24)
        self.spinner.hide()
        ctrl_layout.addWidget(self.spinner)

        self.lbl_step_status = QLabel("Ready to connect.", self)
        self.lbl_step_status.setFont(QFont("JetBrains Mono", 9))
        self.lbl_step_status.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY};")
        ctrl_layout.addWidget(self.lbl_step_status)

        ctrl_layout.addStretch()

        # Pairing and Settings buttons
        self.btn_pair = QPushButton("Pairing...", self)
        self.btn_pair.setToolTip("One-time ADB wireless pairing (Ctrl+P)")
        self.btn_pair.clicked.connect(self._open_pairing_dialog)
        ctrl_layout.addWidget(self.btn_pair)

        self.btn_settings = QPushButton("⚙ Settings", self)
        self.btn_settings.setToolTip("Preferences and Secrets (Ctrl+,)")
        self.btn_settings.clicked.connect(self._open_settings_dialog)
        ctrl_layout.addWidget(self.btn_settings)

        root_layout.addWidget(control_card)

        # ==========================================
        # 4. ACTION CARDS ROW (Scrcpy, Screen-Off, Sniffer)
        # ==========================================
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(14)

        self.card_scrcpy = ActionCard(
            title="SCRCPY",
            subtitle="Mirror Screen & Audio",
            hotkey="F1",
            accent_color=COLORS.CYAN_PRIMARY,
            parent=self,
        )
        self.card_scrcpy.action_triggered.connect(self._launch_scrcpy_normal)
        self.card_scrcpy.stop_requested.connect(self._stop_scrcpy)
        actions_layout.addWidget(self.card_scrcpy)

        self.card_screenoff = ActionCard(
            title="SCREEN OFF",
            subtitle="Mirror with Display Off",
            hotkey="F2",
            accent_color=COLORS.MAGENTA_ACCENT,
            parent=self,
        )
        self.card_screenoff.action_triggered.connect(self._launch_scrcpy_screenoff)
        self.card_screenoff.stop_requested.connect(self._stop_scrcpy)
        actions_layout.addWidget(self.card_screenoff)

        self.card_sniffer = ActionCard(
            title="SNIFFER",
            subtitle="Live Hotspot Capture",
            hotkey="F3",
            accent_color=COLORS.AMBER_SEARCHING,
            parent=self,
        )
        self.card_sniffer.action_triggered.connect(self._start_sniffer)
        self.card_sniffer.stop_requested.connect(self._stop_sniffer)
        actions_layout.addWidget(self.card_sniffer)

        root_layout.addLayout(actions_layout)

        # ==========================================
        # 5. TABS ROW (Log Console, Packet Table, Presets)
        # ==========================================
        self.tabs = QTabWidget(self)

        # Tab 1: Log Console
        self.console = LogConsole(self)
        self.tabs.addTab(self.console, "LOG CONSOLE")

        # Tab 2: Packet Table
        self.packet_table = PacketTable(self)
        self.tabs.addTab(self.packet_table, "PACKET SNIFFER")

        # Tab 3: Quick Presets
        self.preset_selector = PresetSelector(self.config.scrcpy.default_args, self)
        self.preset_selector.preset_changed.connect(self._on_preset_changed)
        self.tabs.addTab(self.preset_selector, "SCRCPY PRESETS")

        root_layout.addWidget(self.tabs, 1)

        # ==========================================
        # 6. FOOTER ROW
        # ==========================================
        footer = QHBoxLayout()
        footer.setSpacing(16)

        self.lbl_uptime = QLabel("Uptime: 00:00:00", self)
        self.lbl_uptime.setStyleSheet(f"color: {COLORS.TEXT_MUTED}; font-family: 'JetBrains Mono'; font-size: 11px;")
        footer.addWidget(self.lbl_uptime)

        # System versions
        adb_path = shutil.which("adb") or "not found"
        scrcpy_path = shutil.which("scrcpy") or "not found"
        self.lbl_versions = QLabel(f"adb: {os.path.basename(adb_path)} • scrcpy: {os.path.basename(scrcpy_path)}", self)
        self.lbl_versions.setStyleSheet(f"color: {COLORS.TEXT_MUTED}; font-family: 'JetBrains Mono'; font-size: 11px;")
        footer.addWidget(self.lbl_versions)

        footer.addStretch()

        lbl_signature = QLabel("ARC-LINK v1.0.0 [Arch Linux]", self)
        lbl_signature.setStyleSheet(f"color: {COLORS.TEXT_MUTED}; font-family: 'Orbitron'; font-size: 10px;")
        footer.addWidget(lbl_signature)

        root_layout.addLayout(footer)

    def _setup_shortcuts(self) -> None:
        """Configures keyboard shortcuts."""
        shortcut_f1 = QShortcut(QKeySequence(Qt.Key.Key_F1), self)
        shortcut_f1.activated.connect(self._launch_scrcpy_normal)

        shortcut_f2 = QShortcut(QKeySequence(Qt.Key.Key_F2), self)
        shortcut_f2.activated.connect(self._launch_scrcpy_screenoff)

        shortcut_f3 = QShortcut(QKeySequence(Qt.Key.Key_F3), self)
        shortcut_f3.activated.connect(self._toggle_sniffer)

        shortcut_settings = QShortcut(QKeySequence("Ctrl+,"), self)
        shortcut_settings.activated.connect(self._open_settings_dialog)

        shortcut_pairing = QShortcut(QKeySequence("Ctrl+P"), self)
        shortcut_pairing.activated.connect(self._open_pairing_dialog)

    def _setup_tray(self) -> None:
        self.tray = ArcTrayIcon(self)
        self.tray.show_window_requested.connect(self._show_and_activate)
        self.tray.connect_requested.connect(self.start_connection_flow)
        self.tray.disconnect_requested.connect(self.disconnect_flow)
        self.tray.scrcpy_requested.connect(self._launch_scrcpy_normal)
        self.tray.quit_requested.connect(self._quit_application)
        self.tray.show()

    def _bind_signals(self) -> None:
        # State machine
        self.state_machine.state_changed.connect(self._on_state_changed)

        # Hotspot watcher
        self.hotspot_watcher.hotspot_connected.connect(self._on_hotspot_joined)
        self.hotspot_watcher.hotspot_disconnected.connect(self._on_hotspot_lost)

        # Scrcpy runner
        self.scrcpy_runner.process_started.connect(self._on_scrcpy_started)
        self.scrcpy_runner.process_finished.connect(self._on_scrcpy_finished)
        self.scrcpy_runner.error_occurred.connect(self._on_scrcpy_error)

    # =========================================================================
    # State Machine and Connection Management
    # =========================================================================

    def _on_state_changed(self, new_state: ConnectionState, message: str) -> None:
        self.pill_state.set_state(new_state)
        self.tray.update_state(new_state)
        self.lbl_step_status.setText(message)

        # Enable/Disable Buttons
        is_connected = new_state == ConnectionState.CONNECTED
        is_connecting = new_state in (ConnectionState.SEARCHING, ConnectionState.KNOCKING, ConnectionState.CONNECTING)

        self.btn_connect.setEnabled(not is_connected and not is_connecting)
        self.btn_disconnect.setEnabled(is_connected or is_connecting)

        if is_connecting:
            self.spinner.start()
        else:
            self.spinner.stop()

        # Action cards availability
        self.card_scrcpy.set_card_enabled(is_connected)
        self.card_screenoff.set_card_enabled(is_connected)
        self.card_sniffer.set_card_enabled(is_connected)

        if is_connected:
            self.console.log("SUCCESS", f"State: CONNECTED to {self._active_endpoint}")
            self._telemetry_timer.start()
            self._refresh_telemetry()
            if self.config.behavior.show_notifications:
                self.tray.notify("ARC-LINK Connected", f"Connected to {self._active_endpoint}")

            if self.config.behavior.auto_launch_scrcpy and not self.scrcpy_runner.is_running:
                self.console.log("INFO", "Auto-launching scrcpy session...")
                self._launch_scrcpy_normal()

        elif new_state in (ConnectionState.DISCONNECTED, ConnectionState.ERROR):
            self._telemetry_timer.stop()
            self.device_card.set_disconnected()
            if self.scrcpy_runner.is_running:
                self.scrcpy_runner.stop()
            if self.sniffer_worker:
                self._stop_sniffer()

    def start_connection_flow(self) -> None:
        """Starts the multi-step phone discovery and knock sequence."""
        if self.state_machine.state in (ConnectionState.CONNECTED, ConnectionState.CONNECTING, ConnectionState.KNOCKING):
            return

        gateway = self.hotspot_watcher.current_gateway
        self.console.log("INFO", f"Initiating phone discovery (Gateway: {gateway or 'auto-detect'})...")
        self.state_machine.to_searching()
        self.device_card.set_loading()

        self.discovery_worker = DeviceDiscoveryWorker(
            shared_secret=self.config.auth.shared_secret,
            gateway_ip=gateway,
            knock_port=self.config.network.knock_port,
            default_adb_port=self.config.network.default_adb_port,
        )
        self.discovery_worker.step_progress.connect(self._on_discovery_progress)
        self.discovery_worker.endpoint_found.connect(self._on_endpoint_discovered)
        self.discovery_worker.discovery_failed.connect(self._on_discovery_failed)
        self.discovery_worker.start()

    def _on_discovery_progress(self, msg: str) -> None:
        self.console.log("INFO", msg)
        self.lbl_step_status.setText(msg)
        if "Knocking" in msg:
            self.state_machine.to_knocking(msg)
        elif "Connecting" in msg or "Handshaking" in msg:
            self.state_machine.to_connecting(msg)

    def _on_endpoint_discovered(self, endpoint: str, details: Dict[str, Any]) -> None:
        self._active_endpoint = endpoint
        self.console.log("SUCCESS", f"Endpoint handshake established: {endpoint}")
        self.state_machine.to_connected(endpoint)
        if details:
            self.device_card.update_device_info(details)

    def _on_discovery_failed(self, reason: str) -> None:
        self.console.log("ERROR", f"Discovery sequence failed: {reason}")
        self.state_machine.to_error(reason)
        if self.config.behavior.show_notifications:
            self.tray.notify("Connection Failed", reason)

    def disconnect_flow(self) -> None:
        """Disconnects ADB and resets state."""
        self.console.log("INFO", "Disconnecting session...")
        if self.discovery_worker and self.discovery_worker.isRunning():
            self.discovery_worker.stop()

        if self._active_endpoint:
            self.adb_manager.disconnect(self._active_endpoint)
            self._active_endpoint = ""

        self.scrcpy_runner.stop()
        self._stop_sniffer()
        self.state_machine.to_disconnected("Disconnected by user")

    # =========================================================================
    # Hotspot Watcher Events
    # =========================================================================

    def _on_hotspot_joined(self, iface: str, ssid: str, gateway: str) -> None:
        self.lbl_hotspot_info.setText(f"SSID: {ssid} [{iface}]")
        self.lbl_hotspot_info.setStyleSheet(
            f"background: rgba(57, 255, 136, 0.12); color: {COLORS.GREEN_CONNECTED}; "
            f"border: 1px solid {COLORS.GREEN_CONNECTED}; border-radius: 17px; padding: 6px 14px;"
        )
        self.console.log("SUCCESS", f"Joined hotspot '{ssid}' on {iface} (Gateway: {gateway})")

        if self.config.behavior.auto_connect and self.state_machine.state == ConnectionState.DISCONNECTED:
            self.console.log("INFO", "Auto-connect triggered by hotspot join.")
            self.start_connection_flow()

    def _on_hotspot_lost(self, iface: str) -> None:
        self.lbl_hotspot_info.setText("Wi-Fi: Disconnected")
        self.lbl_hotspot_info.setStyleSheet(
            f"background: rgba(255, 255, 255, 0.05); color: {COLORS.TEXT_SECONDARY}; "
            f"border: 1px solid rgba(255, 255, 255, 0.10); border-radius: 17px; padding: 6px 14px;"
        )
        self.console.log("WARN", f"Hotspot lost on interface {iface}")

        if self.config.behavior.auto_disconnect_on_loss:
            self.disconnect_flow()

    # =========================================================================
    # Scrcpy & Sniffer Actions
    # =========================================================================

    def _launch_scrcpy_normal(self) -> None:
        if not self._active_endpoint:
            QMessageBox.warning(self, "Not Connected", "Please connect to the phone before launching scrcpy.")
            return

        flags = self.preset_selector.get_flags()
        self.console.log("INFO", f"Starting scrcpy on {self._active_endpoint} with flags: {' '.join(flags)}")
        success = self.scrcpy_runner.launch(self._active_endpoint, flags, turn_screen_off=False)
        if success:
            self.card_scrcpy.set_active(True)
            self.card_screenoff.set_active(False)

    def _launch_scrcpy_screenoff(self) -> None:
        if not self._active_endpoint:
            QMessageBox.warning(self, "Not Connected", "Please connect to the phone before launching scrcpy.")
            return

        flags = self.preset_selector.get_flags()
        self.console.log("INFO", f"Starting scrcpy (Screen-Off) on {self._active_endpoint}...")
        success = self.scrcpy_runner.launch(self._active_endpoint, flags, turn_screen_off=True)
        if success:
            self.card_screenoff.set_active(True)
            self.card_scrcpy.set_active(False)

    def _stop_scrcpy(self) -> None:
        self.scrcpy_runner.stop()
        self.card_scrcpy.set_active(False)
        self.card_screenoff.set_active(False)

    def _on_scrcpy_started(self) -> None:
        self.console.log("SUCCESS", "Scrcpy mirror window active.")

    def _on_scrcpy_finished(self, exit_code: int) -> None:
        self.console.log("INFO", f"Scrcpy session closed (code {exit_code}).")
        self.card_scrcpy.set_active(False)
        self.card_screenoff.set_active(False)

    def _on_scrcpy_error(self, err_msg: str) -> None:
        self.console.log("ERROR", f"Scrcpy error: {err_msg}")
        self.card_scrcpy.set_active(False)
        self.card_screenoff.set_active(False)

    def _start_sniffer(self) -> None:
        if self.sniffer_worker and self.sniffer_worker.isRunning():
            return

        iface = self.hotspot_watcher.current_interface or "wlan0"
        target_ip = self._active_endpoint.split(":")[0] if self._active_endpoint else ""

        self.console.log("INFO", f"Starting Scapy sniffer on interface '{iface}' (Target IP: {target_ip or 'all'})...")
        self.sniffer_worker = SnifferWorker(interface=iface, target_ip=target_ip)
        self.sniffer_worker.packet_captured.connect(self.packet_table.add_packet)
        self.sniffer_worker.sniffer_started.connect(lambda: self.card_sniffer.set_active(True))
        self.sniffer_worker.sniffer_stopped.connect(self._on_sniffer_stopped)
        self.sniffer_worker.start()
        self.tabs.setCurrentWidget(self.packet_table)

    def _stop_sniffer(self) -> None:
        if self.sniffer_worker:
            self.sniffer_worker.stop()
            self.sniffer_worker = None
        self.card_sniffer.set_active(False)

    def _toggle_sniffer(self) -> None:
        if self.card_sniffer.is_active():
            self._stop_sniffer()
        elif self.state_machine.state == ConnectionState.CONNECTED:
            self._start_sniffer()

    def _on_sniffer_stopped(self, msg: str) -> None:
        self.console.log("INFO", f"Sniffer: {msg}")
        self.card_sniffer.set_active(False)

    def _on_preset_changed(self, flags: list) -> None:
        self.config.scrcpy.default_args = flags
        self.console.log("INFO", f"Scrcpy preset applied: {' '.join(flags)}")

    # =========================================================================
    # Telemetry and Polling
    # =========================================================================

    def _refresh_telemetry(self) -> None:
        if self.state_machine.state != ConnectionState.CONNECTED or not self._active_endpoint:
            return

        # Query state to ensure device hasn't gone offline
        state_str = self.adb_manager.get_device_state(self._active_endpoint)
        if state_str != "device":
            self.console.log("WARN", f"Device state changed to '{state_str}'. Checking connection...")
            if state_str in ("offline", "unauthorized", "none"):
                self.state_machine.to_error(f"Device reported state: {state_str}")
                return

        # Fetch detailed metrics
        details = self.adb_manager.get_device_telemetry(self._active_endpoint)
        self.device_card.update_device_info(details)

    def _update_footer_uptime(self) -> None:
        elapsed = int(time.time() - self._start_time)
        hrs = elapsed // 3600
        mins = (elapsed % 3600) // 60
        secs = elapsed % 60
        self.lbl_uptime.setText(f"Uptime: {hrs:02d}:{mins:02d}:{secs:02d}")

    # =========================================================================
    # Dialogs & App Lifecycle
    # =========================================================================

    def _open_settings_dialog(self) -> None:
        dlg = SettingsDialog(self.config, self)
        dlg.config_saved.connect(self._on_settings_saved)
        dlg.exec()

    def _on_settings_saved(self, new_cfg: ArcConfig) -> None:
        self.config = new_cfg
        self.console.log("SUCCESS", "Settings saved successfully.")

    def _open_pairing_dialog(self) -> None:
        ip = self._active_endpoint.split(":")[0] if self._active_endpoint else (self.hotspot_watcher.current_gateway or "")
        dlg = PairingDialog(default_ip=ip, parent=self)
        dlg.paired_successfully.connect(lambda ep: self.console.log("SUCCESS", f"Paired with {ep}"))
        dlg.exec()

    def _show_and_activate(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def _quit_application(self) -> None:
        self.disconnect_flow()
        self.hotspot_watcher.stop()
        self.tray.hide()
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Minimizes to system tray instead of closing."""
        if self.tray.isVisible():
            self.hide()
            self.tray.notify("ARC-LINK Minimized", "ARC-LINK is running in the background system tray.")
            event.ignore()
        else:
            self._quit_application()
            event.accept()
