"""
ARC-LINK Settings Dialog.
Allows configuration of shared secret, hotspot SSID filter, autostart,
scrcpy arguments, and auto-connection preferences.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from arc_link.core.config import ArcConfig
from arc_link.ui.tokens import COLORS


class SettingsDialog(QDialog):
    """
    Settings preferences dialog.
    """

    config_saved = pyqtSignal(ArcConfig)

    def __init__(self, config: ArcConfig, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("ARC-LINK — Settings")
        self.setFixedSize(540, 520)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        lbl_title = QLabel("System Configuration", self)
        lbl_title.setFont(QFont("Orbitron", 13, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {COLORS.CYAN_PRIMARY};")
        layout.addWidget(lbl_title)

        form = QFormLayout()
        form.setSpacing(12)

        # 1. Shared Knock Secret
        self.input_secret = QLineEdit(self)
        self.input_secret.setText(self._config.auth.shared_secret)
        self.input_secret.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.input_secret.setPlaceholderText("Shared passphrase with Android app")
        form.addRow("UDP Knock Secret:", self.input_secret)

        # 2. Hotspot SSID Filter
        self.input_ssids = QLineEdit(self)
        self.input_ssids.setText(", ".join(self._config.network.ssid_filter))
        self.input_ssids.setPlaceholderText("e.g. Pixel_AP, MyHotspot (comma separated, empty for any)")
        form.addRow("SSID Filter:", self.input_ssids)

        # 3. Knock Port
        self.spin_port = QSpinBox(self)
        self.spin_port.setRange(1024, 65535)
        self.spin_port.setValue(self._config.network.knock_port)
        form.addRow("Knock UDP Port:", self.spin_port)

        # 4. Scrcpy default arguments
        self.input_scrcpy_args = QLineEdit(self)
        self.input_scrcpy_args.setText(" ".join(self._config.scrcpy.default_args))
        self.input_scrcpy_args.setPlaceholderText("e.g. --no-audio --max-size 1024 -b 4M")
        form.addRow("Scrcpy Arguments:", self.input_scrcpy_args)

        # 5. Fallback ADB Port
        self.spin_fallback_adb = QSpinBox(self)
        self.spin_fallback_adb.setRange(1, 65535)
        self.spin_fallback_adb.setValue(self._config.network.default_adb_port)
        form.addRow("Default ADB Port:", self.spin_fallback_adb)

        # 6. Checkboxes for automated behaviors
        self.chk_autoconnect = QCheckBox("Auto-connect immediately when phone hotspot joins", self)
        self.chk_autoconnect.setChecked(self._config.behavior.auto_connect)
        form.addRow("", self.chk_autoconnect)

        self.chk_autoscrcpy = QCheckBox("Auto-launch scrcpy screen mirror upon connection", self)
        self.chk_autoscrcpy.setChecked(self._config.behavior.auto_launch_scrcpy)
        form.addRow("", self.chk_autoscrcpy)

        self.chk_autodisconnect = QCheckBox("Auto-disconnect & terminate scrcpy when hotspot lost", self)
        self.chk_autodisconnect.setChecked(self._config.behavior.auto_disconnect_on_loss)
        form.addRow("", self.chk_autodisconnect)

        self.chk_autostart = QCheckBox("Launch minimized to tray on Linux user login", self)
        self.chk_autostart.setChecked(self._config.behavior.autostart_minimized)
        form.addRow("", self.chk_autostart)

        self.chk_notifications = QCheckBox("Show desktop notifications on state transitions", self)
        self.chk_notifications.setChecked(self._config.behavior.show_notifications)
        form.addRow("", self.chk_notifications)

        layout.addLayout(form)
        layout.addStretch()

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancel = QPushButton("Cancel", self)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_save = QPushButton("Save Settings", self)
        btn_save.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS.CYAN_PRIMARY}; color: #070A12; font-weight: bold; }} "
            f"QPushButton:hover {{ background-color: #33EBFF; }}"
        )
        btn_save.clicked.connect(self._save_settings)
        btn_box.addWidget(btn_save)

        layout.addLayout(btn_box)

    def _save_settings(self) -> None:
        secret = self.input_secret.text().strip()
        if not secret:
            QMessageBox.warning(self, "Invalid Secret", "Shared secret cannot be empty.")
            return

        # Update config model
        self._config.auth.shared_secret = secret

        ssids = [s.strip() for s in self.input_ssids.text().split(",") if s.strip()]
        self._config.network.ssid_filter = ssids
        self._config.network.knock_port = self.spin_port.value()
        self._config.network.default_adb_port = self.spin_fallback_adb.value()

        args = self.input_scrcpy_args.text().strip().split()
        self._config.scrcpy.default_args = args

        self._config.behavior.auto_connect = self.chk_autoconnect.isChecked()
        self._config.behavior.auto_launch_scrcpy = self.chk_autoscrcpy.isChecked()
        self._config.behavior.auto_disconnect_on_loss = self.chk_autodisconnect.isChecked()
        self._config.behavior.autostart_minimized = self.chk_autostart.isChecked()
        self._config.behavior.show_notifications = self.chk_notifications.isChecked()

        try:
            self._config.save()
            self.config_saved.emit(self._config)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", f"Could not save config to file: {e}")
