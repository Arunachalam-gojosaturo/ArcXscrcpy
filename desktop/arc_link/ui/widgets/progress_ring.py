"""
ARC-LINK Circular Progress Ring Widget.
Cyber-styled spinner with smooth rotational glow.
"""

from __future__ import annotations

from PyQt6.QtCore import QRectF, QTimer, Qt
from PyQt6.QtGui import QColor, QConicalGradient, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from arc_link.ui.tokens import COLORS


class ProgressRing(QWidget):
    """
    Indeterminate neon circular progress spinner.
    """

    def __init__(self, parent: QWidget | None = None, size: int = 24) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._angle = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.setInterval(20)  # 50 FPS

    def start(self) -> None:
        if not self._timer.isActive():
            self._timer.start()
        self.show()

    def stop(self) -> None:
        if self._timer.isActive():
            self._timer.stop()
        self.hide()

    def _rotate(self) -> None:
        self._angle = (self._angle + 6.0) % 360.0
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        margin = 3.0
        rect = QRectF(margin, margin, w - margin * 2, h - margin * 2)

        # Track background
        track_pen = QPen(QColor(0, 229, 255, 30), 2.5)
        painter.setPen(track_pen)
        painter.drawEllipse(rect)

        # Rotating gradient arc
        center = rect.center()
        gradient = QConicalGradient(center, self._angle)
        gradient.setColorAt(0.0, QColor(COLORS.CYAN_PRIMARY))
        gradient.setColorAt(0.3, QColor(0, 229, 255, 120))
        gradient.setColorAt(0.7, QColor(0, 229, 255, 0))
        gradient.setColorAt(1.0, QColor(0, 229, 255, 0))

        arc_pen = QPen(gradient, 2.5)
        arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(arc_pen)

        # Draw a 270 degree sweep
        span_angle = int(270 * 16)
        start_angle = int(-self._angle * 16)
        painter.drawArc(rect, start_angle, span_angle)
