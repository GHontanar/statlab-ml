"""Botón «?» con una explicación breve en lenguaje clínico."""
from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QToolButton, QToolTip, QWidget


class HelpButton(QToolButton):
    def __init__(self, text: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("HelpButton")
        self.setText("?")
        self.help_text = text
        self.setToolTip(text)
        self.setFixedSize(18, 18)
        self.setCursor(Qt.CursorShape.WhatsThisCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setAccessibleName(text)
        self.clicked.connect(self._show)

    def _show(self) -> None:
        QToolTip.showText(self.mapToGlobal(QPoint(0, self.height() + 4)), self.help_text, self)
