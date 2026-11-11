"""
ARC-LINK Status Glow Pill Widget.
Displays the current connection state with pulsing glow animation and cyber accents.
"""

from __future__ import annotations

from PyQt6.QtCore import QPropertyAnimation, QRectF, QTimer, Qt, pyqtProperty
from PyQt6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

from arc_link.core.state import ConnectionState
from arc_link.ui.tokens import COLORS, GEOMETRY


class GlowPill(QWidget):
    """
    Animated Cyber-HUD status indicator pill.
    Emits a pulsing outer glow when searching, connecting, or knocking.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(34)
        self.setMinimumWidth(150)

        self._state = ConnectionState.DISCONNECTED
        self._glow_intensity: float = 0.4
        self._pulse_direction = 1

        # Pulse timer for searching / knocking / connecting states
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._animate_pulse)
        self._pulse_timer.setInterval(40)  # ~25 FPS

        self.setToolTip("Connection State Indicator")

    def _animate_pulse(self) -> None:
        delta = 0.03 * self._pulse_direction
        self._glow_intensity += delta
        if self._glow_intensity >= 0.95:
            self._glow_intensity = 0.95
            self._pulse_direction = -1
        elif self._glow_intensity <= 0.25:
            self._glow_intensity = 0.25
            self._pulse_direction = 1
        self.update()

    def set_state(self, state: ConnectionState) -> None:
        self._state = state
        if state in (ConnectionState.SEARCHING, ConnectionState.KNOCKING, ConnectionState.CONNECTING):
            if not self._pulse_timer.isActive():
                self._pulse_timer.start()
        else:
            if self._pulse_timer.isActive():
                self._pulse_timer.stop()
            self._glow_intensity = 0.8 if state == ConnectionState.CONNECTED else 0.4
        self.update()

    def _get_state_color(self) -> QColor:
        match self._state:
            case ConnectionState.CONNECTED:
                return QColor(COLORS.GREEN_CONNECTED)
            case ConnectionState.SEARCHING | ConnectionState.KNOCKING | ConnectionState.CONNECTING:
                return QColor(COLORS.AMBER_SEARCHING)
            case ConnectionState.ERROR:
                return QColor(COLORS.RED_ERROR)
            case _:
                return QColor(COLORS.TEXT_MUTED)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        rect = QRectF(2, 2, w - 4, h - 4)
        radius = h / 2.0

        accent = self._get_state_color()

        # 1. Outer Glow Layer
        glow_color = QColor(accent)
        glow_color.setAlphaF(min(1.0, max(0.0, self._glow_intensity * 0.4)))
        painter.setPen(QPen(glow_color, 4))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)

        # 2. Pill Background (Semi-translucent dark glass)
        bg_gradient = QLinearGradient(0, 0, w, h)
        bg_gradient.setColorAt(0.0, QColor(20, 26, 46, 230))
        bg_gradient.setColorAt(1.0, QColor(10, 14, 28, 240))
        painter.setBrush(QBrush(bg_gradient))

        # 3. Pill Border (Subtle 1px border with accent touch)
        border_color = QColor(accent)
        border_color.setAlphaF(0.7 if self._state == ConnectionState.CONNECTED else 0.3)
        painter.setPen(QPen(border_color, 1.2))
        painter.drawRoundedRect(rect, radius, radius)

        # 4. Status Dot
        dot_radius = 4.5
        dot_x = 16.0
        dot_y = h / 2.0

        # Dot outer ring
        dot_halo = QColor(accent)
        dot_halo.setAlphaF(self._glow_intensity * 0.6)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(dot_halo))
        painter.drawEllipse(QRectF(dot_x - dot_radius - 2, dot_y - dot_radius - 2, (dot_radius + 2) * 2, (dot_radius + 2) * 2))

        # Dot core
        painter.setBrush(QBrush(accent))
        painter.drawEllipse(QRectF(dot_x - dot_radius, dot_y - dot_radius, dot_radius * 2, dot_radius * 2))

        # 5. Text Label
        text = self._state.value.upper()
        painter.setPen(QColor(COLORS.TEXT_PRIMARY))
        font = QFont("JetBrains Mono", 9, QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
        painter.setFont(font)

        text_rect = QRectF(dot_x + dot_radius + 8, 0, w - dot_x - dot_radius - 16, h)
        painter.drawText(text_rect, int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), text)
