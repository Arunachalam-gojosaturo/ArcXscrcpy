"""
ARC-LINK Device Card Widget.
Displays real-time hardware telemetry from the connected device.
Features glassmorphism background, data grid, and skeleton shimmer loader.
"""

from __future__ import annotations

from typing import Any, Dict

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from arc_link.ui.tokens import COLORS, GEOMETRY
from arc_link.ui.widgets.shimmer import SkeletonShimmer


class StatItem(QWidget):
    """Single metric cell with label and value."""

    def __init__(self, label: str, value: str = "—", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        self.lbl_title = QLabel(label.upper(), self)
        font_lbl = QFont("Inter", 8, QFont.Weight.Medium)
        self.lbl_title.setFont(font_lbl)
        self.lbl_title.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; background: transparent;")
        layout.addWidget(self.lbl_title)

        self.lbl_val = QLabel(value, self)
        font_val = QFont("JetBrains Mono", 10, QFont.Weight.Bold)
        self.lbl_val.setFont(font_val)
        self.lbl_val.setStyleSheet(f"color: {COLORS.TEXT_PRIMARY}; background: transparent;")
        layout.addWidget(self.lbl_val)

    def set_value(self, val: str, color: str | None = None) -> None:
        self.lbl_val.setText(val)
        c = color or COLORS.TEXT_PRIMARY
        self.lbl_val.setStyleSheet(f"color: {c}; background: transparent;")


class DeviceCard(QWidget):
    """
    Glass panel showing Android Device Name, Manufacturer, Android Version,
    IP:PORT, Battery, Charging status, Storage, and Uptime.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(140)

        self._stack = QStackedLayout(self)
        self._stack.setStackingMode(QStackedLayout.StackingMode.StackOne)

        # 1. Shimmer Skeleton Widget (Index 0)
        self._shimmer = SkeletonShimmer(self, radius=GEOMETRY.RADIUS_MD)
        self._stack.addWidget(self._shimmer)

        # 2. Real Content Widget (Index 1)
        self._content_widget = QWidget(self)
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(18, 12, 18, 12)
        self._content_layout.setSpacing(8)

        # Header of device card: Device Name & Manufacturer
        top_row = QHBoxLayout()
        self.lbl_device_name = QLabel("NO DEVICE CONNECTED", self._content_widget)
        font_dn = QFont("Orbitron", 12, QFont.Weight.Bold)
        self.lbl_device_name.setFont(font_dn)
        self.lbl_device_name.setStyleSheet(f"color: {COLORS.CYAN_PRIMARY}; background: transparent;")
        top_row.addWidget(self.lbl_device_name)

        self.lbl_model = QLabel("", self._content_widget)
        font_mod = QFont("Inter", 9)
        self.lbl_model.setFont(font_mod)
        self.lbl_model.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; background: transparent;")
        top_row.addWidget(self.lbl_model)
        top_row.addStretch()

        self._content_layout.addLayout(top_row)

        # Grid of stats (2 rows x 4 columns)
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(4)

        self.stat_endpoint = StatItem("Endpoint", "—", self._content_widget)
        self.stat_android = StatItem("Android Ver", "—", self._content_widget)
        self.stat_battery = StatItem("Battery", "—", self._content_widget)
        self.stat_charging = StatItem("Power", "—", self._content_widget)

        self.stat_storage = StatItem("Storage", "—", self._content_widget)
        self.stat_uptime = StatItem("Uptime", "—", self._content_widget)
        self.stat_serial = StatItem("Serial / ID", "—", self._content_widget)
        self.stat_mode = StatItem("Auth Mode", "—", self._content_widget)

        grid.addWidget(self.stat_endpoint, 0, 0)
        grid.addWidget(self.stat_android, 0, 1)
        grid.addWidget(self.stat_battery, 0, 2)
        grid.addWidget(self.stat_charging, 0, 3)

        grid.addWidget(self.stat_storage, 1, 0)
        grid.addWidget(self.stat_uptime, 1, 1)
        grid.addWidget(self.stat_serial, 1, 2)
        grid.addWidget(self.stat_mode, 1, 3)

        self._content_layout.addLayout(grid)
        self._stack.addWidget(self._content_widget)

        # Initial state: content widget shown with placeholders
        self.set_disconnected()

    def set_loading(self) -> None:
        """Switch to skeleton shimmer during discovery / connection."""
        self._stack.setCurrentWidget(self._shimmer)

    def set_disconnected(self) -> None:
        """Reset fields to disconnected placeholder."""
        self._stack.setCurrentWidget(self._content_widget)
        self.lbl_device_name.setText("OFFLINE / STANDBY")
        self.lbl_device_name.setStyleSheet(f"color: {COLORS.TEXT_MUTED}; background: transparent;")
        self.lbl_model.setText("Awaiting Hotspot Connection")
        self.stat_endpoint.set_value("—", COLORS.TEXT_MUTED)
        self.stat_android.set_value("—", COLORS.TEXT_MUTED)
        self.stat_battery.set_value("—", COLORS.TEXT_MUTED)
        self.stat_charging.set_value("—", COLORS.TEXT_MUTED)
        self.stat_storage.set_value("—", COLORS.TEXT_MUTED)
        self.stat_uptime.set_value("—", COLORS.TEXT_MUTED)
        self.stat_serial.set_value("—", COLORS.TEXT_MUTED)
        self.stat_mode.set_value("Wireless ADB", COLORS.TEXT_MUTED)

    def update_device_info(self, info: Dict[str, Any]) -> None:
        """Populate fields with live device data."""
        self._stack.setCurrentWidget(self._content_widget)

        name = info.get("device_name") or info.get("model") or "Android Device"
        manufacturer = info.get("manufacturer", "")
        model = info.get("model", "")
        self.lbl_device_name.setText(name.upper())
        self.lbl_device_name.setStyleSheet(f"color: {COLORS.CYAN_PRIMARY}; background: transparent;")

        model_desc = f"{manufacturer} {model}".strip()
        self.lbl_model.setText(f"• {model_desc}" if model_desc else "")

        endpoint = info.get("endpoint") or f"{info.get('ip', '—')}:{info.get('port', '')}"
        self.stat_endpoint.set_value(endpoint, COLORS.GREEN_CONNECTED)

        release = info.get("android_version", "—")
        sdk = info.get("sdk_version", "")
        self.stat_android.set_value(f"{release} (API {sdk})" if sdk else str(release))

        battery_level = info.get("battery_level")
        batt_str = f"{battery_level}%" if battery_level is not None else "—"
        batt_color = COLORS.GREEN_CONNECTED if (battery_level or 0) > 20 else COLORS.RED_ERROR
        self.stat_battery.set_value(batt_str, batt_color)

        is_charging = info.get("is_charging")
        charging_str = "AC / USB Charging" if is_charging else "Discharging"
        self.stat_charging.set_value(charging_str, COLORS.CYAN_PRIMARY if is_charging else COLORS.TEXT_SECONDARY)

        storage = info.get("storage_free", "—")
        self.stat_storage.set_value(str(storage))

        uptime = info.get("uptime", "—")
        self.stat_uptime.set_value(str(uptime))

        serial = info.get("serial") or info.get("ip", "—")
        self.stat_serial.set_value(str(serial))
        self.stat_mode.set_value("TCP/IP 9099", COLORS.CYAN_PRIMARY)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        rect = QRectF(1.0, 1.0, w - 2, h - 2)
        radius = float(GEOMETRY.RADIUS_MD)

        # Glass panel gradient
        gradient = QLinearGradient(0, 0, w, h)
        gradient.setColorAt(0.0, QColor(17, 24, 39, 180))
        gradient.setColorAt(1.0, QColor(9, 14, 26, 210))
        painter.setBrush(gradient)

        # 1px border
        pen = QPen(QColor(255, 255, 255, 28), 1.0)
        painter.setPen(pen)
        painter.drawRoundedRect(rect, radius, radius)
