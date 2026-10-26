"""Interruptor encendido/apagado con su texto al lado."""
from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QAbstractButton, QWidget

from statlab.ui import theme
from statlab.ui.theme import tokens as tk

W, H = 32, 18


class Toggle(QAbstractButton):
    def __init__(self, text: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setText(text)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def sizeHint(self) -> QSize:
        fm = self.fontMetrics()
        return QSize(W + 8 + fm.horizontalAdvance(self.text()), max(H, fm.height()) + 4)

    def hasHeightForWidth(self) -> bool:
        return False

    def paintEvent(self, event) -> None:
        t = tk.tokens(theme.is_dark())
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        y = (self.height() - H) / 2
        on = self.isChecked()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(t["accent"] if on else t["border_strong"]))
        p.drawRoundedRect(QRectF(0, y, W, H), H / 2, H / 2)
        p.setBrush(QColor("#FFFFFF"))
        knob = H - 4
        p.drawEllipse(QRectF(W - knob - 2 if on else 2, y + 2, knob, knob))
        if self.hasFocus():
            p.setPen(QColor(t["accent"]))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(-1, y - 1, W + 2, H + 2), H / 2 + 1, H / 2 + 1)
        p.setPen(QColor(t["text"] if self.isEnabled() else t["text_muted"]))
        p.drawText(QRectF(W + 8, 0, self.width() - W - 8, self.height()),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap, self.text())
