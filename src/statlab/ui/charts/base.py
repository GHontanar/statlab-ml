"""Base de los gráficos interactivos (pyqtgraph) con el tema de StatLab.

Ejes con coma decimal, colores de los tokens, sin menús ni zoom accidental:
los gráficos de la app son para leer y para elegir (clic, lazo), no para explorar.
"""
from __future__ import annotations

import pyqtgraph as pg
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from statlab.ui import theme
from statlab.ui.theme import tokens as tk

pg.setConfigOptions(antialias=True)


class SpanishAxis(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        return [s.replace(".", ",").replace("-", "−") for s in super().tickStrings(values, scale, spacing)]


def tokens() -> dict[str, str]:
    return tk.tokens(theme.is_dark())


class ThemedPlot(pg.PlotWidget):
    def __init__(self, x_label: str, y_label: str, parent=None, view_box: pg.ViewBox | None = None):
        extra = {"viewBox": view_box} if view_box is not None else {}
        super().__init__(parent, axisItems={"bottom": SpanishAxis("bottom"), "left": SpanishAxis("left")}, **extra)
        t = tokens()
        self.setBackground(t["panel"])
        self.setFixedHeight(230)
        item = self.getPlotItem()
        item.setMenuEnabled(False)
        item.hideButtons()
        item.showGrid(x=False, y=True, alpha=0.18)
        self.setMouseEnabled(x=False, y=False)
        self.getViewBox().setDefaultPadding(0.12)  # que los puntos y el anillo no toquen el borde
        font = QFont(QApplication.font())
        font.setPixelSize(11)
        for name, label in (("bottom", x_label), ("left", y_label)):
            axis = item.getAxis(name)
            axis.setPen(pg.mkPen(t["border_strong"]))
            axis.setTextPen(pg.mkPen(t["text_secondary"]))
            axis.setTickFont(font)
            axis.enableAutoSIPrefix(False)  # nada de «×0,001» en el eje
            axis.setLabel(label, color=t["text_secondary"], **{"font-size": "11px"})

    def set_integer_x(self, values: list[int]) -> None:
        self.getPlotItem().getAxis("bottom").setTicks([[(v, str(v)) for v in values]])
        self.setXRange(min(values) - 0.4, max(values) + 0.4, padding=0)
