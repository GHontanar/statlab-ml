"""Mapa de calor de perfiles (medias en z por cluster), escala divergente azul–gris–rojo.

Cada celda lleva su valor; el texto es blanco cuando |z| > 1,1. Clic en una fila
emite su cluster (para mostrar la media (DE) en unidades originales).
"""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from statlab.core import fmt
from statlab.ui import clusters as cl
from statlab.ui import theme
from statlab.ui.theme import tokens as tk

Z_LIMIT = 2.0  # |z| ≥ 2 usa el color extremo
ROW_H = 34
HEADER_H = 26
LABEL_W = 56


def diverging(z: float) -> QColor:
    stops = [QColor(c) for c in tk.DIVERGING]
    t = (np.clip(z, -Z_LIMIT, Z_LIMIT) + Z_LIMIT) / (2 * Z_LIMIT) * (len(stops) - 1)
    i = min(int(t), len(stops) - 2)
    f = t - i
    a, b = stops[i], stops[i + 1]
    return QColor(round(a.red() + f * (b.red() - a.red())), round(a.green() + f * (b.green() - a.green())),
                  round(a.blue() + f * (b.blue() - a.blue())))


class Heatmap(QWidget):
    row_clicked = Signal(int)

    def __init__(self, z: list[list[float]], columns: list[str], parent: QWidget | None = None):
        super().__init__(parent)
        self.z = np.asarray(z, dtype=float)
        self.columns = columns
        self.selected: int | None = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(HEADER_H + ROW_H * len(self.z) + 4)
        self.setMinimumWidth(LABEL_W + 48 * len(columns))
        self.setMouseTracking(True)

    def sizeHint(self) -> QSize:
        return QSize(LABEL_W + 80 * len(self.columns), self.height())

    def _cell_w(self) -> float:
        return (self.width() - LABEL_W) / max(len(self.columns), 1)

    def paintEvent(self, event) -> None:
        t = tk.tokens(theme.is_dark())
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        base = QFont(self.font())
        base.setPixelSize(12)
        small = QFont(base)
        small.setPixelSize(11)
        bold = QFont(base)
        bold.setWeight(QFont.Weight.DemiBold)
        w = self._cell_w()
        # Cabecera: nombres de las variables (recortados si no caben)
        p.setFont(small)
        p.setPen(QColor(t["text_secondary"]))
        fm = QFontMetrics(small)
        for j, name in enumerate(self.columns):
            rect = QRectF(LABEL_W + j * w, 0, w, HEADER_H)
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, fm.elidedText(name, Qt.TextElideMode.ElideRight, int(w) - 4))
        for i, row in enumerate(self.z):
            y = HEADER_H + i * ROW_H
            p.setFont(bold)
            p.setPen(QColor(cl.color(i)))
            p.drawText(QRectF(4, y, 18, ROW_H), Qt.AlignmentFlag.AlignVCenter, cl.glyph(i))
            p.setPen(QColor(t["text"]))
            p.drawText(QRectF(22, y, LABEL_W - 24, ROW_H), Qt.AlignmentFlag.AlignVCenter, cl.name(i))
            p.setFont(base)
            for j, value in enumerate(row):
                rect = QRectF(LABEL_W + j * w + 1, y + 1, w - 2, ROW_H - 2)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(diverging(value))
                p.drawRoundedRect(rect, 3, 3)
                white = abs(value) > tk.DIVERGING_WHITE_TEXT_ABS_Z
                p.setPen(QColor("#FFFFFF" if white else "#1C1C1A"))
                p.drawText(rect, Qt.AlignmentFlag.AlignCenter, fmt.num(value, 2))
            if self.selected == i:
                p.setPen(QPen(QColor(t["text"]), 2))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRoundedRect(QRectF(1, y + 1, self.width() - 2, ROW_H - 2), 4, 4)

    def mousePressEvent(self, event) -> None:
        i = int((event.position().y() - HEADER_H) // ROW_H)
        if 0 <= i < len(self.z) and event.position().y() >= HEADER_H:
            self.selected = i
            self.update()
            self.row_clicked.emit(i)
