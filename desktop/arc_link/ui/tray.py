"""
ARC-LINK System Tray Controller.
Provides system tray presence, status color changes, context menu, and desktop notifications.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

from arc_link.core.state import ConnectionState
from arc_link.ui.tokens import COLORS


class ArcTrayIcon(QSystemTrayIcon):
    """
    Tray icon representing ARC-LINK status.
    """

    show_window_requested = pyqtSignal()
    connect_requested = pyqtSignal()
    disconnect_requested = pyqtSignal()
    scrcpy_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._state = ConnectionState.DISCONNECTED
        self._create_icon()
        self._build_menu()

        self.activated.connect(self._on_activated)

    def _create_icon(self) -> None:
        """Draws a crisp cyber tray badge pixmap reflecting the state color."""
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = {
            ConnectionState.CONNECTED: QColor(COLORS.GREEN_CONNECTED),
            ConnectionState.SEARCHING: QColor(COLORS.AMBER_SEARCHING),
            ConnectionState.KNOCKING: QColor(COLORS.AMBER_SEARCHING),
            ConnectionState.CONNECTING: QColor(COLORS.AMBER_SEARCHING),
            ConnectionState.ERROR: QColor(COLORS.RED_ERROR),
        }.get(self._state, QColor(COLORS.TEXT_MUTED))

        # Outer ring
        painter.setPen(color)
        painter.setBrush(QColor(13, 18, 36, 220))
        painter.drawRoundedRect(2, 2, 28, 28, 8, 8)

        # Center dot
        painter.setBrush(color)
        painter.drawEllipse(10, 10, 12, 12)
        painter.end()

        self.setIcon(QIcon(pixmap))

    def _build_menu(self) -> None:
        menu = QMenu()

        act_show = QAction("Open ARC-LINK", menu)
        act_show.triggered.connect(self.show_window_requested.emit)
        menu.addAction(act_show)

        menu.addSeparator()

        self.act_connect = QAction("Connect", menu)
        self.act_connect.triggered.connect(self.connect_requested.emit)
        menu.addAction(self.act_connect)

        self.act_disconnect = QAction("Disconnect", menu)
        self.act_disconnect.triggered.connect(self.disconnect_requested.emit)
        menu.addAction(self.act_disconnect)

        self.act_scrcpy = QAction("Launch Scrcpy", menu)
        self.act_scrcpy.triggered.connect(self.scrcpy_requested.emit)
        menu.addAction(self.act_scrcpy)

        menu.addSeparator()

        act_quit = QAction("Quit ARC-LINK", menu)
        act_quit.triggered.connect(self.quit_requested.emit)
        menu.addAction(act_quit)

        self.setContextMenu(menu)

    def update_state(self, state: ConnectionState) -> None:
        self._state = state
        self._create_icon()
        self.setToolTip(f"ARC-LINK: {state.value.upper()}")

        is_connected = state == ConnectionState.CONNECTED
        self.act_connect.setEnabled(state in (ConnectionState.DISCONNECTED, ConnectionState.ERROR))
        self.act_disconnect.setEnabled(is_connected or state in (ConnectionState.SEARCHING, ConnectionState.KNOCKING, ConnectionState.CONNECTING))
        self.act_scrcpy.setEnabled(is_connected)

    def notify(self, title: str, message: str) -> None:
        """Sends desktop notification via QSystemTrayIcon or notify-send."""
        if self.isVisible():
            self.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 4000)
        elif shutil.which("notify-send"):
            try:
                subprocess.Popen(["notify-send", "-a", "ARC-LINK", title, message])
            except Exception:
                pass

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_window_requested.emit()
