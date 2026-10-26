"""Gráficos del barrido de k: codo y silueta por k (con IC bootstrap). Clic en un punto = elegir k."""
from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Signal

from statlab import strings_es as S
from statlab.core import fmt
from statlab.ui.charts.base import ThemedPlot, tokens


class KChart(ThemedPlot):
    """Línea con puntos clicables y un anillo en el k elegido."""

    k_clicked = Signal(int)

    def __init__(self, ks: list[int], values: list[float], y_label: str, tip, parent=None):
        super().__init__(S.AXIS_K, y_label, parent)
        t = tokens()
        self.ks = list(ks)
        self.values = np.asarray(values, dtype=float)
        self.addItem(pg.PlotDataItem(self.ks, self.values, pen=pg.mkPen(t["accent"], width=2)))
        self.points = pg.ScatterPlotItem(
            self.ks, self.values, data=self.ks, size=10, symbol="o",
            pen=pg.mkPen(t["panel"], width=1.5), brush=pg.mkBrush(t["accent"]),
            hoverable=True, hoverSize=13, tip=tip,
        )
        self.points.sigClicked.connect(lambda _item, pts, _ev: pts and self.k_clicked.emit(int(pts[0].data())))
        self.addItem(self.points)
        self.ring = pg.ScatterPlotItem(size=22, symbol="o", pen=pg.mkPen(t["accent"], width=2), brush=None)
        self.addItem(self.ring)
        self.set_integer_x(self.ks)

    def set_selected(self, k: int | None) -> None:
        if k is None or k not in self.ks:
            self.ring.setData([], [])
            return
        self.ring.setData([k], [self.values[self.ks.index(k)]])


def elbow_chart(r: dict) -> KChart:
    def tip(x, y, data):
        return S.TIP_ELBOW.format(k=int(data), v=fmt.num(y, 1))

    return KChart(r["ks"], r["inercia"], S.AXIS_INERTIA, tip)


def silhouette_chart(r: dict) -> KChart:
    boot = r.get("boot")

    def tip(x, y, data):
        ic = ""
        if boot:
            i = r["ks"].index(int(data))
            ic = S.TIP_IC.format(lo=fmt.num(boot["ic_inf"][i], 3), hi=fmt.num(boot["ic_sup"][i], 3))
        return S.TIP_SIL.format(k=int(data), v=fmt.num(y, 3), ic=ic)

    chart = KChart(r["ks"], r["silueta"], S.AXIS_SIL, tip)
    if boot:
        y = np.asarray(r["silueta"], dtype=float)
        lo, hi = np.asarray(boot["ic_inf"]), np.asarray(boot["ic_sup"])
        bars = pg.ErrorBarItem(
            x=np.asarray(r["ks"], dtype=float), y=y, top=np.clip(hi - y, 0, None), bottom=np.clip(y - lo, 0, None),
            beam=0.18, pen=pg.mkPen(tokens()["text_muted"], width=1.2),
        )
        chart.addItem(bars)
        bars.setZValue(-1)
    return chart
