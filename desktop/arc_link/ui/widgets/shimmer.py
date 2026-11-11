"""
ARC-LINK Skeleton Shimmer Effect Widget.
Displays an animated cyberpunk scanning sweep when loading device data.
"""

from __future__ import annotations

from PyQt6.QtCore import QRectF, QTimer, Qt
from PyQt6.QtGui import QBrush, QColor, QLinearGradient, QPainter
from PyQt6.QtWidgets import QWidget

from arc_link.ui.tokens import COLORS, GEOMETRY


class SkeletonShimmer(QWidget):
    """
    Shimmer skeleton loader widget.
    Renders a pulsating gradient highlight moving across the panel.
    """

    def __init__(self, parent: QWidget | None = None, radius: int = 8) -> None:
        super().__init__(parent)
        self._radius = radius
        self._offset: float = -1.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self._timer.setInterval(25)  # 40 FPS

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._timer.start()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._timer.stop()

    def _step(self) -> None:
        self._offset += 0.04
        if self._offset > 1.5:
            self._offset = -0.5
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        rect = QRectF(0, 0, w, h)

        # Base dark container
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(25, 33, 56, 120))
        painter.drawRoundedRect(rect, self._radius, self._radius)

        # Moving Shimmer sweep
        sweep_x = self._offset * w
        sweep_width = w * 0.6

        gradient = QLinearGradient(sweep_x, 0, sweep_x + sweep_width, 0)
        gradient.setColorAt(0.0, QColor(0, 229, 255, 0))
        gradient.setColorAt(0.5, QColor(0, 229, 255, 45))
        gradient.setColorAt(1.0, QColor(0, 229, 255, 0))

        painter.setBrush(QBrush(gradient))
        painter.drawRoundedRect(rect, self._radius, self._radius)
