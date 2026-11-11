"""
ARC-LINK Log Console Widget.
Displays real-time application and ADB log events with cyber syntax coloring,
search filtering, copy to clipboard, and file export.
"""

from __future__ import annotations

import html
from datetime import datetime
from typing import List

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from arc_link.ui.tokens import COLORS


class LogConsole(QWidget):
    """
    Searchable and exportable colored log console widget.
    """

    MAX_LINES = 3000

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._raw_lines: List[str] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)

        # Control Toolbar
        controls = QHBoxLayout()
        controls.setSpacing(8)

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search logs...")
        self.search_input.setStyleSheet(
            f"QLineEdit {{ background: rgba(13, 18, 36, 0.85); color: {COLORS.TEXT_PRIMARY}; "
            f"border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 6px; padding: 6px 12px; }} "
            f"QLineEdit:focus {{ border-color: {COLORS.CYAN_PRIMARY}; }}"
        )
        self.search_input.textChanged.connect(self._filter_logs)
        controls.addWidget(self.search_input, 1)

        self.btn_copy = QPushButton("Copy All", self)
        self.btn_copy.setStyleSheet(
            f"QPushButton {{ background: rgba(255, 255, 255, 0.06); color: {COLORS.TEXT_SECONDARY}; "
            f"border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 6px; padding: 6px 12px; }} "
            f"QPushButton:hover {{ background: rgba(0, 229, 255, 0.12); color: {COLORS.CYAN_PRIMARY}; }}"
        )
        self.btn_copy.clicked.connect(self._copy_all)
        controls.addWidget(self.btn_copy)

        self.btn_export = QPushButton("Export", self)
        self.btn_export.setStyleSheet(
            f"QPushButton {{ background: rgba(255, 255, 255, 0.06); color: {COLORS.TEXT_SECONDARY}; "
            f"border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 6px; padding: 6px 12px; }} "
            f"QPushButton:hover {{ background: rgba(0, 229, 255, 0.12); color: {COLORS.CYAN_PRIMARY}; }}"
        )
        self.btn_export.clicked.connect(self._export_logs)
        controls.addWidget(self.btn_export)

        self.btn_clear = QPushButton("Clear", self)
        self.btn_clear.setStyleSheet(
            f"QPushButton {{ background: rgba(255, 255, 255, 0.06); color: {COLORS.TEXT_SECONDARY}; "
            f"border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 6px; padding: 6px 12px; }} "
            f"QPushButton:hover {{ background: rgba(255, 59, 92, 0.2); color: {COLORS.RED_ERROR}; }}"
        )
        self.btn_clear.clicked.connect(self.clear_logs)
        controls.addWidget(self.btn_clear)

        layout.addLayout(controls)

        # Output text view
        self.text_view = QTextEdit(self)
        self.text_view.setReadOnly(True)
        self.text_view.setFont(QFont("JetBrains Mono", 9))
        self.text_view.setStyleSheet(
            f"QTextEdit {{ background: #070A12; color: {COLORS.TEXT_PRIMARY}; "
            f"border: 1px solid rgba(255, 255, 255, 0.10); border-radius: 8px; padding: 8px; }}"
        )
        layout.addWidget(self.text_view)

    def log(self, level: str, message: str) -> None:
        """Logs a message with level: INFO, SUCCESS, WARN, ERROR, DEBUG."""
        now = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        clean_msg = message.strip()
        raw_entry = f"[{now}] [{level.upper()}] {clean_msg}"
        self._raw_lines.append(raw_entry)
        if len(self._raw_lines) > self.MAX_LINES:
            self._raw_lines.pop(0)

        query = self.search_input.text().strip().lower()
        if not query or query in raw_entry.lower():
            self._append_html_entry(now, level.upper(), clean_msg)

    def _append_html_entry(self, now: str, level: str, msg: str) -> None:
        color = {
            "INFO": COLORS.CYAN_PRIMARY,
            "SUCCESS": COLORS.GREEN_CONNECTED,
            "WARN": COLORS.AMBER_SEARCHING,
            "ERROR": COLORS.RED_ERROR,
            "DEBUG": COLORS.TEXT_MUTED,
        }.get(level, COLORS.TEXT_PRIMARY)

        safe_msg = html.escape(msg)
        html_line = (
            f"<span style='color: {COLORS.TEXT_MUTED};'>[{now}]</span> "
            f"<span style='color: {color}; font-weight: bold;'>[{level}]</span> "
            f"<span style='color: {COLORS.TEXT_PRIMARY};'>{safe_msg}</span><br>"
        )

        cursor = self.text_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(html_line)
        self.text_view.setTextCursor(cursor)
        self.text_view.ensureCursorVisible()

    def _filter_logs(self) -> None:
        query = self.search_input.text().strip().lower()
        self.text_view.clear()
        for raw in self._raw_lines:
            if not query or query in raw.lower():
                # Parse raw
                try:
                    parts = raw.split("] [", 1)
                    now = parts[0].strip("[")
                    rest = parts[1].split("] ", 1)
                    lvl = rest[0]
                    msg = rest[1]
                    self._append_html_entry(now, lvl, msg)
                except Exception:
                    self.text_view.append(raw)

    def _copy_all(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText("\n".join(self._raw_lines))

    def _export_logs(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export ARC-LINK Logs", "arc-link.log", "Log Files (*.log *.txt)"
        )
        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write("\n".join(self._raw_lines) + "\n")
            except Exception as e:
                self.log("ERROR", f"Failed to export log file: {e}")

    def clear_logs(self) -> None:
        self._raw_lines.clear()
        self.text_view.clear()
