"""
ARC-LINK Application Entry Point.
Implements single-instance lock via QLocalServer, command line arguments,
QSS stylesheet loading, and window lifecycle.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from PyQt6.QtCore import QIODevice, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication

from arc_link.core.config import load_config
from arc_link.ui.main_window import MainWindow

APP_NAME = "arc-link"
APP_VERSION = "1.0.0"
SOCKET_NAME = "arc-link-single-instance-sock"


class SingleInstanceApp:
    """Manages QLocalServer single instance lock."""

    def __init__(self, app_name: str = SOCKET_NAME) -> None:
        self.socket_name = app_name
        self.server: QLocalServer | None = None

    def is_already_running(self) -> bool:
        socket = QLocalSocket()
        socket.connectToServer(self.socket_name)
        if socket.waitForConnected(500):
            # Another instance is listening; send trigger to bring it to front
            socket.write(b"SHOW\n")
            socket.waitForBytesWritten(1000)
            socket.disconnectFromServer()
            return True

        # Clean up stale socket file if server crashed
        QLocalServer.removeServer(self.socket_name)
        return False

    def setup_listener(self, window: MainWindow) -> None:
        self.server = QLocalServer()
        self.server.listen(self.socket_name)
        self.server.newConnection.connect(lambda: self._handle_client(window))

    def _handle_client(self, window: MainWindow) -> None:
        if not self.server:
            return
        client = self.server.nextPendingConnection()
        if not client:
            return
        client.waitForReadyRead(500)
        data = bytes(client.readAll()).decode("utf-8", errors="ignore").strip()
        if "SHOW" in data:
            window.show()
            window.raise_()
            window.activateWindow()
        client.disconnectFromServer()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="arc-link",
        description="Autonomous Wireless ADB Screen Recovery Bridge for Broken Displays",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {APP_VERSION}")
    parser.add_argument("--minimized", action="store_true", help="Start application minimized to system tray")
    parser.add_argument("--config", type=str, default=None, help="Custom configuration TOML path")
    return parser.parse_args()


def load_stylesheet(app: QApplication) -> None:
    """Loads ui/theme.qss stylesheet."""
    theme_path = Path(__file__).parent / "ui" / "theme.qss"
    if theme_path.exists():
        try:
            with open(theme_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to load stylesheet: {e}\n")


def main() -> None:
    args = parse_arguments()

    # Qt Environment setup
    os.environ["QT_QPA_PLATFORMTHEME"] = "qt6ct"
    app = QApplication(sys.argv)
    app.setApplicationName("ARC-LINK")
    app.setApplicationDisplayName("ARC-LINK — Autonomous Screen Recovery")
    app.setApplicationVersion(APP_VERSION)
    app.setDesktopFileName("arc-link.desktop")

    # Set Application Icon if available
    icon_svg = Path(__file__).parent.parent / "resources" / "icons" / "arc-link.svg"
    if icon_svg.exists():
        app.setWindowIcon(QIcon(str(icon_svg)))

    # Single instance verification
    single_inst = SingleInstanceApp()
    if single_inst.is_already_running():
        print("ARC-LINK is already running. Activated existing window.")
        sys.exit(0)

    # Apply Cyber-HUD QSS theme
    load_stylesheet(app)

    # Load configuration
    cfg = load_config(Path(args.config) if args.config else None)

    # Initialize main window
    window = MainWindow(config=cfg)
    single_inst.setup_listener(window)

    if args.minimized or cfg.behavior.autostart_minimized:
        window.hide()
    else:
        window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
