"""
ARC-LINK Scrcpy Preset Selector Widget.
Quick selection for scrcpy configurations: Low-Latency, High Quality, and Audio-Only.
"""

from __future__ import annotations

from typing import List

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from arc_link.ui.tokens import COLORS


class PresetSelector(QWidget):
    """
    Scrcpy preset configurator with one-click profiles.
    """

    preset_changed = pyqtSignal(list)  # list of scrcpy CLI flags

    PRESETS = {
        "LOW_LATENCY": {
            "name": "⚡ Low Latency",
            "flags": ["--no-audio", "--max-size", "1024", "-b", "4M", "--max-fps", "60"],
            "desc": "1024px, 4 Mbps, no audio overhead — best for touch responsiveness",
        },
        "HIGH_QUALITY": {
            "name": "💎 High Quality",
            "flags": ["--max-size", "1920", "-b", "16M", "--max-fps", "60"],
            "desc": "1080p, 16 Mbps crystal clear video + synced stereo audio",
        },
        "AUDIO_ONLY": {
            "name": "🎵 Audio Only",
            "flags": ["--no-video", "--audio-codec=opus"],
            "desc": "Headless audio streaming without video render overhead",
        },
    }

    def __init__(self, current_flags: List[str] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(12)

        # Profile buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._btn_group = QButtonGroup(self)
        self._preset_buttons = {}

        for key, pdata in self.PRESETS.items():
            btn = QPushButton(pdata["name"], self)
            btn.setCheckable(True)
            btn.setFixedHeight(36)
            btn.setStyleSheet(
                f"QPushButton {{ background: rgba(255, 255, 255, 0.05); color: {COLORS.TEXT_PRIMARY}; "
                f"border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 8px; font-weight: bold; padding: 0 16px; }} "
                f"QPushButton:hover {{ background: rgba(0, 229, 255, 0.10); border-color: {COLORS.CYAN_PRIMARY}; }} "
                f"QPushButton:checked {{ background: rgba(0, 229, 255, 0.20); border-color: {COLORS.CYAN_PRIMARY}; color: {COLORS.CYAN_PRIMARY}; }}"
            )
            self._btn_group.addButton(btn)
            btn_row.addWidget(btn)
            self._preset_buttons[key] = btn
            btn.clicked.connect(lambda checked, k=key: self._select_preset(k))

        layout.addLayout(btn_row)

        self.lbl_desc = QLabel(self.PRESETS["LOW_LATENCY"]["desc"], self)
        self.lbl_desc.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-style: italic; font-size: 11px;")
        layout.addWidget(self.lbl_desc)

        # Custom arguments editor
        custom_layout = QHBoxLayout()
        custom_lbl = QLabel("Active Scrcpy Flags:", self)
        custom_lbl.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-family: 'JetBrains Mono';")
        custom_layout.addWidget(custom_lbl)

        self.custom_input = QLineEdit(self)
        default_str = " ".join(current_flags or self.PRESETS["LOW_LATENCY"]["flags"])
        self.custom_input.setText(default_str)
        self.custom_input.setStyleSheet(
            f"QLineEdit {{ background: rgba(13, 18, 36, 0.85); color: {COLORS.CYAN_PRIMARY}; "
            f"border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 6px; padding: 6px 12px; font-family: 'JetBrains Mono'; }} "
            f"QLineEdit:focus {{ border-color: {COLORS.CYAN_PRIMARY}; }}"
        )
        self.custom_input.textChanged.connect(self._custom_flags_edited)
        custom_layout.addWidget(self.custom_input, 1)

        layout.addLayout(custom_layout)
        layout.addStretch()

        # Initial check
        self._preset_buttons["LOW_LATENCY"].setChecked(True)

    def _select_preset(self, key: str) -> None:
        pdata = self.PRESETS[key]
        self.lbl_desc.setText(pdata["desc"])
        flags = pdata["flags"]
        self.custom_input.setText(" ".join(flags))
        self.preset_changed.emit(flags)

    def _custom_flags_edited(self, text: str) -> None:
        flags = text.strip().split()
        self.preset_changed.emit(flags)

    def get_flags(self) -> List[str]:
        return self.custom_input.text().strip().split()
