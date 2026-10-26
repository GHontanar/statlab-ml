"""Slider de rango con dos tiradores (enteros). Se arrastra con el ratón o con las flechas."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from statlab.ui import theme
from statlab.ui.theme import tokens as tk

HANDLE = 16
TRACK = 4


class RangeSlider(QWidget):
    range_changed = Signal(int, int)

    def __init__(self, minimum: int, maximum: int, parent: QWidget | None = None):
        super().__init__(parent)
        self.minimum, self.maximum = minimum, maximum
        self._lo, self._hi = minimum, maximum
        self._drag: str | None = None
        self._focus = "lo"
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(120)

    def sizeHint(self) -> QSize:
        return QSize(200, HANDLE + 18)

    # --- Valores ---------------------------------------------------------
    def values(self) -> tuple[int, int]:
        return self._lo, self._hi

    def set_values(self, lo: int, hi: int, emit: bool = True) -> None:
        lo = max(self.minimum, min(int(lo), self.maximum - 1))
        hi = min(self.maximum, max(int(hi), lo + 1))  # al menos dos valores de k
        if (lo, hi) == (self._lo, self._hi):
            return
        self._lo, self._hi = lo, hi
        self.update()
        if emit:
            self.range_changed.emit(lo, hi)

    # --- Geometría -------------------------------------------------------
    def _x(self, value: int) -> float:
        span = self.width() - HANDLE
        return HANDLE / 2 + span * (value - self.minimum) / (self.maximum - self.minimum)

    def _value_at(self, x: float) -> int:
        span = self.width() - HANDLE
        frac = (x - HANDLE / 2) / span if span else 0
        return round(self.minimum + frac * (self.maximum - self.minimum))

    def paintEvent(self, event) -> None:
        t = tk.tokens(theme.is_dark())
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cy = HANDLE / 2 + 1
        left, right = self._x(self.minimum), self._x(self.maximum)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(t["border"]))
        p.drawRoundedRect(QRectF(left, cy - TRACK / 2, right - left, TRACK), 2, 2)
        p.setBrush(QColor(t["accent"]))
        p.drawRoundedRect(QRectF(self._x(self._lo), cy - TRACK / 2, self._x(self._hi) - self._x(self._lo), TRACK), 2, 2)
        # Marcas de cada entero, con su número debajo
        font = p.font()
        font.setPixelSize(11)
        p.setFont(font)
        for v in range(self.minimum, self.maximum + 1):
            x = self._x(v)
            p.setPen(QColor(t["text_secondary"] if self._lo <= v <= self._hi else t["text_muted"]))
            p.drawText(QRectF(x - 10, HANDLE + 2, 20, 14), Qt.AlignmentFlag.AlignCenter, str(v))
        for name, v in (("lo", self._lo), ("hi", self._hi)):
            focused = self.hasFocus() and self._focus == name
            p.setPen(QPen(QColor(t["accent"]), 3 if focused else 2))
            p.setBrush(QColor(t["panel"]))
            p.drawEllipse(QPointF(self._x(v), cy), HANDLE / 2 - 1, HANDLE / 2 - 1)

    # --- Interacción -----------------------------------------------------
    def mousePressEvent(self, event) -> None:
        x = event.position().x()
        d_lo, d_hi = abs(x - self._x(self._lo)), abs(x - self._x(self._hi))
        self._drag = "lo" if d_lo < d_hi or (d_lo == d_hi and x < self._x(self._lo)) else "hi"
        self._focus = self._drag
        self._move_to(x)

    def mouseMoveEvent(self, event) -> None:
        if self._drag:
            self._move_to(event.position().x())

    def mouseReleaseEvent(self, event) -> None:
        self._drag = None

    def _move_to(self, x: float) -> None:
        v = self._value_at(x)
        if self._drag == "lo":
            self.set_values(min(v, self._hi - 1), self._hi)
        else:
            self.set_values(self._lo, max(v, self._lo + 1))

    def focusNextPrevChild(self, next: bool) -> bool:  # noqa: A002 - nombre de Qt
        # Tab pasa del tirador izquierdo al derecho antes de salir del control.
        if next and self._focus == "lo":
            self._focus = "hi"
        elif not next and self._focus == "hi":
            self._focus = "lo"
        else:
            return super().focusNextPrevChild(next)
        self.update()
        return True

    def focusInEvent(self, event) -> None:
        self._focus = "hi" if event.reason() == Qt.FocusReason.BacktabFocusReason else "lo"
        super().focusInEvent(event)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        step = {Qt.Key.Key_Left: -1, Qt.Key.Key_Down: -1, Qt.Key.Key_Right: 1, Qt.Key.Key_Up: 1}.get(key)
        if step is None:
            super().keyPressEvent(event)
            return
        if self._focus == "lo":
            self.set_values(min(self._lo + step, self._hi - 1), self._hi)
        else:
            self.set_values(self._lo, max(self._hi + step, self._lo + 1))
