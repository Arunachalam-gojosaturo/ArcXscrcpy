"""
ARC-LINK ADB Pairing Dialog.
Provides a guided GUI dialog to perform one-time ADB Wi-Fi pairing (`adb pair <ip>:<port> <code>`).
"""

from __future__ import annotations

import subprocess
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from arc_link.ui.tokens import COLORS


class PairingDialog(QDialog):
    """
    Dialog for initial wireless ADB pairing.
    """

    paired_successfully = pyqtSignal(str)

    def __init__(self, default_ip: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("ARC-LINK — Wireless ADB Pairing")
        self.setFixedSize(480, 360)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        lbl_title = QLabel("Pair Android Device", self)
        lbl_title.setFont(QFont("Orbitron", 13, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {COLORS.CYAN_PRIMARY};")
        layout.addWidget(lbl_title)

        # Instructions
        lbl_info = QLabel(
            "While your phone screen is still functional:\n"
            "1. Open Settings -> Developer Options -> Wireless Debugging\n"
            "2. Tap 'Pair device with pairing code'\n"
            "3. Enter the IP, pairing port, and 6-digit code shown on the phone below:",
            self,
        )
        lbl_info.setFont(QFont("Inter", 9))
        lbl_info.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY};")
        lbl_info.setWordWrap(True)
        layout.addWidget(lbl_info)

        # Form fields
        form = QVBoxLayout()
        form.setSpacing(10)

        lbl_endpoint = QLabel("PAIRING ENDPOINT (IP:PORT)", self)
        lbl_endpoint.setFont(QFont("JetBrains Mono", 8, QFont.Weight.Bold))
        lbl_endpoint.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY};")
        form.addWidget(lbl_endpoint)

        self.input_endpoint = QLineEdit(self)
        self.input_endpoint.setPlaceholderText("192.168.43.1:37125")
        if default_ip:
            self.input_endpoint.setText(f"{default_ip}:")
        form.addWidget(self.input_endpoint)

        lbl_code = QLabel("6-DIGIT PAIRING CODE", self)
        lbl_code.setFont(QFont("JetBrains Mono", 8, QFont.Weight.Bold))
        lbl_code.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY};")
        form.addWidget(lbl_code)

        self.input_code = QLineEdit(self)
        self.input_code.setPlaceholderText("123456")
        self.input_code.setMaxLength(6)
        form.addWidget(self.input_code)

        layout.addLayout(form)

        # Status text
        self.lbl_status = QLabel("", self)
        self.lbl_status.setFont(QFont("JetBrains Mono", 9))
        self.lbl_status.setStyleSheet(f"color: {COLORS.AMBER_SEARCHING};")
        layout.addWidget(self.lbl_status)

        layout.addStretch()

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        self.btn_cancel = QPushButton("Cancel", self)
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        self.btn_pair = QPushButton("Pair Device", self)
        self.btn_pair.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS.CYAN_PRIMARY}; color: #070A12; font-weight: bold; }} "
            f"QPushButton:hover {{ background-color: #33EBFF; }}"
        )
        self.btn_pair.clicked.connect(self._execute_pairing)
        btn_box.addWidget(self.btn_pair)

        layout.addLayout(btn_box)

    def _execute_pairing(self) -> None:
        endpoint = self.input_endpoint.text().strip()
        code = self.input_code.text().strip()

        if not endpoint or ":" not in endpoint:
            QMessageBox.warning(self, "Invalid Input", "Please provide a valid IP:PORT pairing endpoint.")
            return

        if not code or len(code) != 6 or not code.isdigit():
            QMessageBox.warning(self, "Invalid Input", "Please provide a valid 6-digit numeric pairing code.")
            return

        self.lbl_status.setText("Initiating TLS handshake...")
        self.btn_pair.setEnabled(False)

        try:
            cmd = ["adb", "pair", endpoint, code]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
            out = result.stdout + result.stderr
            if "Successfully paired to" in out or result.returncode == 0:
                self.lbl_status.setText("Pairing successful!")
                self.paired_successfully.emit(endpoint)
                QMessageBox.information(
                    self,
                    "Pairing Successful",
                    f"Successfully paired ADB with {endpoint}!\nKeys are now trusted on your Arch Linux system.",
                )
                self.accept()
            else:
                self.lbl_status.setText(f"Pairing failed: {out.strip()[:80]}")
                QMessageBox.critical(self, "Pairing Failed", f"ADB output:\n{out}")
                self.btn_pair.setEnabled(True)
        except Exception as e:
            self.lbl_status.setText(f"Error: {e}")
            QMessageBox.critical(self, "Execution Error", str(e))
            self.btn_pair.setEnabled(True)
