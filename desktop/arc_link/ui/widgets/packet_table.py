"""
ARC-LINK Scapy Packet Table Widget.
Displays live captured frames on the Wi-Fi hotspot interface with
filtering, auto-scroll controls, and protocol color coding.
"""

from __future__ import annotations

from typing import Dict, List

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from arc_link.ui.tokens import COLORS


class PacketTable(QWidget):
    """
    Real-time packet table fed by SnifferWorker.
    """

    MAX_ROWS = 2000

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._auto_scroll = True
        self._all_records: List[Dict[str, str]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)

        # Top control row
        controls = QHBoxLayout()
        controls.setSpacing(8)

        self.filter_input = QLineEdit(self)
        self.filter_input.setPlaceholderText("Filter packets (IP, protocol, port, or summary)...")
        self.filter_input.setStyleSheet(
            f"QLineEdit {{ background: rgba(13, 18, 36, 0.85); color: {COLORS.TEXT_PRIMARY}; "
            f"border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 6px; padding: 6px 12px; }} "
            f"QLineEdit:focus {{ border-color: {COLORS.CYAN_PRIMARY}; }}"
        )
        self.filter_input.textChanged.connect(self._apply_filter)
        controls.addWidget(self.filter_input, 1)

        self.btn_autoscroll = QPushButton("Auto-Scroll: ON", self)
        self.btn_autoscroll.setStyleSheet(
            f"QPushButton {{ background: rgba(0, 229, 255, 0.12); color: {COLORS.CYAN_PRIMARY}; "
            f"border: 1px solid {COLORS.CYAN_PRIMARY}; border-radius: 6px; padding: 6px 12px; font-weight: bold; }}"
        )
        self.btn_autoscroll.clicked.connect(self._toggle_autoscroll)
        controls.addWidget(self.btn_autoscroll)

        self.btn_clear = QPushButton("Clear", self)
        self.btn_clear.setStyleSheet(
            f"QPushButton {{ background: rgba(255, 255, 255, 0.06); color: {COLORS.TEXT_SECONDARY}; "
            f"border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 6px; padding: 6px 12px; }} "
            f"QPushButton:hover {{ background: rgba(255, 59, 92, 0.2); color: {COLORS.RED_ERROR}; }}"
        )
        self.btn_clear.clicked.connect(self.clear_packets)
        controls.addWidget(self.btn_clear)

        self.lbl_count = QLabel("0 packets", self)
        self.lbl_count.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-family: 'JetBrains Mono';")
        controls.addWidget(self.lbl_count)

        layout.addLayout(controls)

        # Table Widget
        self.table = QTableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["TIME", "SOURCE", "DESTINATION", "PROTO", "LEN", "SUMMARY"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.table)

    def _toggle_autoscroll(self) -> None:
        self._auto_scroll = not self._auto_scroll
        txt = "Auto-Scroll: ON" if self._auto_scroll else "Auto-Scroll: OFF"
        color = COLORS.CYAN_PRIMARY if self._auto_scroll else COLORS.TEXT_MUTED
        self.btn_autoscroll.setText(txt)
        self.btn_autoscroll.setStyleSheet(
            f"QPushButton {{ background: rgba(255, 255, 255, 0.05); color: {color}; "
            f"border: 1px solid {color}; border-radius: 6px; padding: 6px 12px; font-weight: bold; }}"
        )

    def add_packet(self, record: Dict[str, str]) -> None:
        """Appends a packet record to the table."""
        self._all_records.append(record)
        if len(self._all_records) > self.MAX_ROWS:
            self._all_records.pop(0)

        query = self.filter_input.text().strip().lower()
        if query and not self._matches_filter(record, query):
            return

        self._insert_table_row(record)
        self.lbl_count.setText(f"{len(self._all_records)} packets")

    def _matches_filter(self, rec: Dict[str, str], query: str) -> bool:
        return any(query in str(v).lower() for v in rec.values())

    def _insert_table_row(self, rec: Dict[str, str]) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)

        proto = rec.get("proto", "OTHER")
        proto_color = {
            "TCP": COLORS.CYAN_PRIMARY,
            "UDP": COLORS.MAGENTA_ACCENT,
            "ICMP": COLORS.AMBER_SEARCHING,
        }.get(proto, COLORS.TEXT_SECONDARY)

        items = [
            QTableWidgetItem(rec.get("time", "")),
            QTableWidgetItem(rec.get("src", "")),
            QTableWidgetItem(rec.get("dst", "")),
            QTableWidgetItem(proto),
            QTableWidgetItem(str(rec.get("length", ""))),
            QTableWidgetItem(rec.get("summary", "")),
        ]

        mono_font = QFont("JetBrains Mono", 8)
        for idx, item in enumerate(items):
            item.setFont(mono_font)
            if idx == 3:  # Protocol column
                item.setForeground(QColor(proto_color))
            else:
                item.setForeground(QColor(COLORS.TEXT_PRIMARY))
            self.table.setItem(row, idx, item)

        if self._auto_scroll:
            self.table.scrollToBottom()

    def _apply_filter(self) -> None:
        query = self.filter_input.text().strip().lower()
        self.table.setRowCount(0)
        for rec in self._all_records:
            if not query or self._matches_filter(rec, query):
                self._insert_table_row(rec)

    def clear_packets(self) -> None:
        self._all_records.clear()
        self.table.setRowCount(0)
        self.lbl_count.setText("0 packets")
