"""Gráficos del modelo final: PCA (clic y lazo), silueta por observación, Jaccard e histograma."""
from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QPainterPath, QPolygonF
from PySide6.QtWidgets import QGraphicsPathItem

from statlab import strings_es as S
from statlab.core import fmt
from statlab.ui import clusters as cl
from statlab.ui.charts.base import ThemedPlot, tokens


class LassoViewBox(pg.ViewBox):
    """Arrastrar con el botón izquierdo dibuja un lazo; al soltar, emite el polígono (coordenadas de datos)."""

    lasso_finished = Signal(object)  # QPolygonF

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._points: list[QPointF] = []
        self._path_item = QGraphicsPathItem()
        self._path_item.setPen(pg.mkPen(tokens()["accent"], width=1.5, style=Qt.PenStyle.DashLine))
        self._path_item.setBrush(pg.mkBrush(tokens()["accent"] + "22"))
        self._path_item.setZValue(1000)
        self.addItem(self._path_item, ignoreBounds=True)

    def mouseDragEvent(self, ev, axis=None) -> None:
        if ev.button() != Qt.MouseButton.LeftButton:
            ev.ignore()
            return
        ev.accept()
        point = self.mapSceneToView(ev.scenePos())
        if ev.isStart():
            self._points = [self.mapSceneToView(ev.buttonDownScenePos()), point]
        else:
            self._points.append(point)
        path = QPainterPath(self._points[0])
        for p in self._points[1:]:
            path.lineTo(p)
        path.closeSubpath()
        self._path_item.setPath(path)
        if ev.isFinish():
            polygon = QPolygonF(self._points)
            self._path_item.setPath(QPainterPath())
            self._points = []
            self.lasso_finished.emit(polygon)


class PCAChart(ThemedPlot):
    """Proyección PCA: color y símbolo por cluster, centroides como rombos con etiqueta.
    Clic en un punto o lazo → emite las filas (posiciones en la tabla) seleccionadas."""

    rows_selected = Signal(list)

    def __init__(self, r: dict, parent=None):
        var = r["pca"]["varianza"]
        self.box = LassoViewBox()
        super().__init__(f"CP1 ({fmt.pct(100 * var[0])})", f"CP2 ({fmt.pct(100 * var[1])})", parent, self.box)
        self.setFixedHeight(320)
        t = tokens()
        self.coords = np.asarray(r["pca"]["coords"], dtype=float)
        self.labels = np.asarray(r["etiquetas"], dtype=int)
        self.rows = np.asarray(r["filas"], dtype=int)
        self.getPlotItem().showGrid(x=True, y=True, alpha=0.12)
        for c in range(r["k"]):
            m = self.labels == c
            item = pg.ScatterPlotItem(
                self.coords[m, 0], self.coords[m, 1], data=self.rows[m], size=8, symbol=cl.pg_symbol(c),
                brush=pg.mkBrush(cl.color(c) + "CC"), pen=pg.mkPen(t["panel"], width=0.6),
                hoverable=True, tip=lambda x, y, data, c=c: S.TIP_PCA.format(cluster=cl.name(c), row=int(data) + 1),
            )
            item.sigClicked.connect(self._clicked)
            self.addItem(item)
        centros = np.asarray(r["pca"]["centros"], dtype=float)
        self.addItem(pg.ScatterPlotItem(
            centros[:, 0], centros[:, 1], size=18, symbol="d",
            brush=[pg.mkBrush(cl.color(c)) for c in range(r["k"])], pen=pg.mkPen(t["text"], width=1.6),
        ))
        for c, (x, y) in enumerate(centros):
            label = pg.TextItem(cl.name(c), color=t["text"], anchor=(-0.35, 1.1))
            label.setPos(x, y)
            self.addItem(label)
        self.highlight = pg.ScatterPlotItem(size=14, symbol="o", pen=pg.mkPen(t["text"], width=1.6), brush=None)
        self.addItem(self.highlight)
        self.box.lasso_finished.connect(self._lasso)

    def _clicked(self, _item, points, ev) -> None:
        if points:
            self.rows_selected.emit([int(points[0].data())])

    def _lasso(self, polygon: QPolygonF) -> None:
        inside = [i for i, (x, y) in enumerate(self.coords)
                  if polygon.containsPoint(QPointF(x, y), Qt.FillRule.OddEvenFill)]
        if inside:
            self.rows_selected.emit([int(self.rows[i]) for i in inside])

    def show_selected(self, rows: list[int]) -> None:
        idx = np.flatnonzero(np.isin(self.rows, rows))
        self.highlight.setData(self.coords[idx, 0], self.coords[idx, 1])


def _cluster_ticks(plot: ThemedPlot, positions: list[float], k: int) -> None:
    plot.getPlotItem().getAxis("bottom").setTicks([[(p, cl.name(c)) for c, p in enumerate(positions)]])


class SilhouetteBars(ThemedPlot):
    """Silueta de cada observación, ordenada dentro de cada cluster, con línea en la media."""

    def __init__(self, r: dict, parent=None):
        super().__init__(S.AXIS_OBS, S.AXIS_SIL_OBS, parent)
        self.setFixedHeight(300)
        t = tokens()
        sil = np.asarray(r["silueta_obs"], dtype=float)
        labels = np.asarray(r["etiquetas"], dtype=int)
        x0, xs, hs, brushes, centers = 0, [], [], [], []
        gap = max(3, len(sil) // 60)
        for c in range(r["k"]):
            vals = np.sort(sil[labels == c])[::-1]
            pos = np.arange(x0, x0 + len(vals))
            xs.append(pos)
            hs.append(vals)
            brushes += [pg.mkBrush(cl.color(c))] * len(vals)
            centers.append(x0 + len(vals) / 2)
            x0 += len(vals) + gap
        self.addItem(pg.BarGraphItem(x=np.concatenate(xs), height=np.concatenate(hs), width=1.0,
                                     brushes=brushes, pen=None))
        self.addItem(pg.InfiniteLine(pos=float(np.mean(sil)), angle=0,
                                     pen=pg.mkPen(t["text"], width=1.2, style=Qt.PenStyle.DashLine)))
        self.addItem(pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen(t["border_strong"], width=1)))
        _cluster_ticks(self, centers, r["k"])


class JaccardChart(ThemedPlot):
    """Jaccard medio por cluster con su IC95 %, y referencias en 0,75 y 0,60 (Hennig, 2007)."""

    def __init__(self, r: dict, parent=None):
        super().__init__(S.AXIS_CLUSTER, S.AXIS_JACCARD, parent)
        t = tokens()
        k = r["k"]
        x = np.arange(1, k + 1, dtype=float)
        jm = np.asarray(r["boot"]["jaccard_media"], dtype=float)
        ci = np.asarray(r["boot"]["jaccard_ic"], dtype=float)
        for value, style in ((0.75, Qt.PenStyle.DashLine), (0.60, Qt.PenStyle.DotLine)):
            line = pg.InfiniteLine(pos=value, angle=0, pen=pg.mkPen(t["text_muted"], width=1, style=style),
                                   label=fmt.num(value), labelOpts={"position": 0.97, "color": t["text_muted"]})
            self.addItem(line)
        self.addItem(pg.ErrorBarItem(x=x, y=jm, top=np.clip(ci[:, 1] - jm, 0, None),
                                     bottom=np.clip(jm - ci[:, 0], 0, None), beam=0.15,
                                     pen=pg.mkPen(t["text_secondary"], width=1.2)))
        for c in range(k):
            self.addItem(pg.ScatterPlotItem([x[c]], [jm[c]], size=12, symbol=cl.pg_symbol(c),
                                            brush=pg.mkBrush(cl.color(c)), pen=pg.mkPen(t["panel"], width=1)))
        self.setYRange(0, 1.08, padding=0)
        self.setXRange(0.4, k + 0.6, padding=0)
        _cluster_ticks(self, list(x), k)


class BootHistogram(ThemedPlot):
    """Distribución bootstrap de la silueta media, con la silueta del modelo final."""

    def __init__(self, r: dict, parent=None):
        super().__init__(S.AXIS_SIL, S.AXIS_FREQ, parent)
        t = tokens()
        sil = np.asarray([v for v in r["boot"]["silueta"] if v is not None], dtype=float)
        bins = min(25, max(5, len(sil) // 8))
        lo, hi = float(sil.min()), float(sil.max())
        if hi - lo < 0.01:  # casi constante: numpy usaría ±0,5 y la barra no significaría nada
            mid = (lo + hi) / 2
            lo, hi = mid - 0.005, mid + 0.005
        counts, edges = np.histogram(sil, bins=bins, range=(lo, hi))
        self.addItem(pg.BarGraphItem(x0=edges[:-1], x1=edges[1:], height=counts,
                                     brush=pg.mkBrush(t["accent"] + "99"), pen=pg.mkPen(t["panel"], width=0.5)))
        self.addItem(pg.InfiniteLine(pos=r["silueta_media"], angle=90,
                                     pen=pg.mkPen(t["text"], width=1.4, style=Qt.PenStyle.DashLine)))
        # Una distribución casi constante no debe verse ampliada hasta la cuarta cifra.
        lo, hi = min(edges[0], r["silueta_media"]), max(edges[-1], r["silueta_media"])
        if hi - lo < 0.05:
            mid = (lo + hi) / 2
            self.setXRange(mid - 0.025, mid + 0.025, padding=0)


class ProbHistogram(ThemedPlot):
    """GMM: distribución de la probabilidad de pertenencia al cluster asignado, con el umbral de frontera."""

    def __init__(self, p: dict, parent=None):
        super().__init__(S.AXIS_PROB, S.AXIS_PATIENTS, parent)
        t = tokens()
        valores = np.asarray(p["p_max"], dtype=float)
        counts, edges = np.histogram(valores, bins=20, range=(0.0, 1.0))
        colores = [t["stale"] if e < p["umbral"] else t["accent"] for e in edges[:-1]]
        brushes = [pg.mkBrush(c + "B0") for c in colores]
        self.addItem(pg.BarGraphItem(x0=edges[:-1], x1=edges[1:], height=counts, brushes=brushes,
                                     pen=pg.mkPen(t["panel"], width=0.5)))
        self.addItem(pg.InfiniteLine(pos=p["umbral"], angle=90,
                                     pen=pg.mkPen(t["text"], width=1.4, style=Qt.PenStyle.DashLine)))
        self.setXRange(0, 1, padding=0.02)
