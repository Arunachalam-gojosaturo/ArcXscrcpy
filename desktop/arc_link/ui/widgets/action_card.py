"""
ARC-LINK Action Card Widget.
Large glowing cards for Scrcpy, Scrcpy Screen-Off, and Scapy Sniffer actions.
Includes active running badges, hotkey badges, and inline stop controls.
"""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QIcon, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from arc_link.ui.tokens import COLORS, GEOMETRY


class ActionCard(QWidget):
    """
    Cyber-HUD action card with glassmorphism surface, glowing highlight,
    hotkey tag, active badge, and stop button.
    """

    action_triggered = pyqtSignal()
    stop_requested = pyqtSignal()

    def __init__(
        self,
        title: str,
        subtitle: str,
        hotkey: str,
        accent_color: str = COLORS.CYAN_PRIMARY,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.title = title
        self.subtitle = subtitle
        self.hotkey = hotkey
        self.accent_color = accent_color

        self._is_active = False
        self._is_enabled = False
        self._is_hovered = False

        self.setFixedHeight(96)
        self.setMinimumWidth(210)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Layout for controls inside card
        self._main_layout = QHBoxLayout(self)
        self._main_layout.setContentsMargins(18, 12, 16, 12)
        self._main_layout.setSpacing(12)

        # Left: text info
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Title row with Hotkey badge
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.lbl_title = QLabel(self.title, self)
        font_title = QFont("Orbitron", 11, QFont.Weight.Bold)
        self.lbl_title.setFont(font_title)
        self.lbl_title.setStyleSheet(f"color: {COLORS.TEXT_PRIMARY}; background: transparent;")
        top_row.addWidget(self.lbl_title)

        self.lbl_hotkey = QLabel(f" {self.hotkey} ", self)
        font_hk = QFont("JetBrains Mono", 8, QFont.Weight.DemiBold)
        self.lbl_hotkey.setFont(font_hk)
        self.lbl_hotkey.setStyleSheet(
            f"color: {COLORS.TEXT_MUTED}; background: rgba(255,255,255,0.06); "
            f"border: 1px solid rgba(255,255,255,0.12); border-radius: 4px;"
        )
        top_row.addWidget(self.lbl_hotkey)
        top_row.addStretch()
        text_layout.addLayout(top_row)

        self.lbl_sub = QLabel(self.subtitle, self)
        font_sub = QFont("Inter", 8)
        self.lbl_sub.setFont(font_sub)
        self.lbl_sub.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; background: transparent;")
        text_layout.addWidget(self.lbl_sub)

        self._main_layout.addLayout(text_layout)
        self._main_layout.addStretch()

        # Right: Active badge / Stop button
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_status = QLabel("OFFLINE", self)
        font_stat = QFont("JetBrains Mono", 8, QFont.Weight.Bold)
        self.lbl_status.setFont(font_stat)
        self.lbl_status.setStyleSheet(
            f"color: {COLORS.TEXT_MUTED}; background: transparent;"
        )
        right_layout.addWidget(self.lbl_status)

        self.btn_stop = QPushButton("STOP", self)
        self.btn_stop.setFixedSize(54, 26)
        font_btn = QFont("JetBrains Mono", 8, QFont.Weight.Bold)
        self.btn_stop.setFont(font_btn)
        self.btn_stop.setStyleSheet(
            f"QPushButton {{ background: rgba(255, 59, 92, 0.15); color: {COLORS.RED_ERROR}; "
            f"border: 1px solid {COLORS.RED_ERROR}; border-radius: 6px; }} "
            f"QPushButton:hover {{ background: rgba(255, 59, 92, 0.35); }}"
        )
        self.btn_stop.clicked.connect(self.stop_requested.emit)
        self.btn_stop.hide()
        right_layout.addWidget(self.btn_stop)

        self._main_layout.addLayout(right_layout)

    def set_card_enabled(self, enabled: bool) -> None:
        self._is_enabled = enabled
        if not enabled:
            self._is_active = False
            self.lbl_status.setText("DISABLED")
            self.lbl_status.setStyleSheet(f"color: {COLORS.TEXT_MUTED}; background: transparent;")
            self.btn_stop.hide()
            self.setCursor(Qt.CursorShape.ForbiddenCursor)
        else:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            if not self._is_active:
                self.lbl_status.setText("READY")
                self.lbl_status.setStyleSheet(f"color: {self.accent_color}; background: transparent;")
        self.update()

    def set_active(self, active: bool) -> None:
        self._is_active = active
        if active:
            self.lbl_status.setText("RUNNING")
            self.lbl_status.setStyleSheet(
                f"color: {COLORS.GREEN_CONNECTED}; background: rgba(57, 255, 136, 0.12); "
                f"border-radius: 4px; padding: 2px 4px;"
            )
            self.btn_stop.show()
        else:
            self.btn_stop.hide()
            if self._is_enabled:
                self.lbl_status.setText("READY")
                self.lbl_status.setStyleSheet(f"color: {self.accent_color}; background: transparent;")
        self.update()

    def is_active(self) -> bool:
        return self._is_active

    def mousePressEvent(self, event) -> None:
        if self._is_enabled and event.button() == Qt.MouseButton.LeftButton:
            # If clicking stop button, that will be handled by btn_stop itself
            if not self.btn_stop.geometry().contains(event.pos()) or not self.btn_stop.isVisible():
                self.action_triggered.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event) -> None:
        self._is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._is_hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        rect = QRectF(1.5, 1.5, w - 3, h - 3)
        radius = float(GEOMETRY.RADIUS_MD)

        # Base gradient
        gradient = QLinearGradient(0, 0, w, h)
        if self._is_active:
            gradient.setColorAt(0.0, QColor(14, 26, 42, 230))
            gradient.setColorAt(1.0, QColor(8, 14, 26, 240))
        elif self._is_hovered and self._is_enabled:
            gradient.setColorAt(0.0, QColor(18, 25, 48, 220))
            gradient.setColorAt(1.0, QColor(10, 16, 32, 230))
        else:
            gradient.setColorAt(0.0, QColor(13, 18, 36, 180))
            gradient.setColorAt(1.0, QColor(7, 10, 18, 210))

        painter.setBrush(QBrush(gradient))

        # Border
        if self._is_active:
            pen = QPen(QColor(COLORS.GREEN_CONNECTED), 1.5)
        elif self._is_hovered and self._is_enabled:
            pen = QPen(QColor(self.accent_color), 1.5)
        else:
            pen = QPen(QColor(255, 255, 255, 28 if self._is_enabled else 14), 1.0)

        painter.setPen(pen)
        painter.drawRoundedRect(rect, radius, radius)

        # Left accent stripe
        if self._is_enabled:
            stripe_color = QColor(COLORS.GREEN_CONNECTED if self._is_active else self.accent_color)
            stripe_rect = QRectF(rect.x(), rect.y() + 10, 3.5, rect.height() - 20)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(stripe_color)
            painter.drawRoundedRect(stripe_rect, 1.5, 1.5)
