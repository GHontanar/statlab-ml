"""Pestaña «Comparar soluciones»: ARI entre dos soluciones, Sankey, tabla cruzada y discordantes.

Las soluciones son los modelos finales de los análisis de la sesión y las importadas
(de otra sesión .statlab o de un CSV `id;cluster`), que se guardan como copias congeladas.
"""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from statlab import strings_es as S
from statlab.core import comparacion as cmp
from statlab.core import fmt
from statlab.core.errors import ErrorUsuario
from statlab.ui import clusters as cl
from statlab.ui import theme
from statlab.ui.theme import tokens as tk
from statlab.ui.widgets.kpi import KpiCard


def _label(texto: str, name: str = "", wrap: bool = True) -> QLabel:
    lab = QLabel(texto)
    if name:
        lab.setObjectName(name)
    lab.setWordWrap(wrap)
    return lab


class Sankey(QWidget):
    """Flujo de pacientes de los clusters de A (izquierda) a los de B (derecha). Clic en una
    banda: esos pacientes."""

    band_clicked = Signal(list)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.r: dict | None = None
        self.bandas: list[tuple[QPainterPath, list[int]]] = []
        self.setMinimumHeight(300)
        self.setMouseTracking(True)
        self.hover: int | None = None

    def set_result(self, r: dict | None) -> None:
        self.r = r
        self.update()

    def _nodos(self, tamanos: list[int], orden: list[int], top: float, alto: float, gap: float):
        total = max(sum(tamanos), 1)
        escala = (alto - gap * (len(tamanos) - 1)) / total
        y, out = top, {}
        for c in orden:
            h = tamanos[c] * escala
            out[c] = [y, h]
            y += h + gap
        return out, escala

    def paintEvent(self, _event) -> None:
        if not self.r:
            return
        t = tk.tokens(theme.is_dark())
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.r
        w, h = self.width(), self.height()
        top, alto, ancho_nodo = 30.0, h - 44.0, 14.0
        xa, xb = 110.0, w - 110.0 - ancho_nodo
        ta, tb = r["tamanos_a"], r["tamanos_b"]
        nodos_a, esc = self._nodos(ta, list(range(r["k_a"])), top, alto, 8)
        nodos_b, _ = self._nodos(tb, r["orden_b"], top, alto, 8)
        p.setPen(QColor(t["text_secondary"]))
        p.drawText(QRectF(0, 4, w / 2, 20), Qt.AlignmentFlag.AlignLeft, f"A · {r['a']}")
        p.drawText(QRectF(w / 2, 4, w / 2, 20), Qt.AlignmentFlag.AlignRight, f"B · {r['b']}")
        # Bandas
        sal = {c: v[0] for c, v in nodos_a.items()}
        lle = {c: v[0] for c, v in nodos_b.items()}
        self.bandas = []
        flujos = sorted(r["flujos"], key=lambda f: (f["a"], r["orden_b"].index(f["b"])))
        for i, f in enumerate(flujos):
            grosor = f["n"] * esc
            y0, y1 = sal[f["a"]], lle[f["b"]]
            sal[f["a"]] += grosor
            lle[f["b"]] += grosor
            x0, x1 = xa + ancho_nodo, xb
            cx = (x1 - x0) / 2
            path = QPainterPath(QPointF(x0, y0))
            path.cubicTo(QPointF(x0 + cx, y0), QPointF(x1 - cx, y1), QPointF(x1, y1))
            path.lineTo(QPointF(x1, y1 + grosor))
            path.cubicTo(QPointF(x1 - cx, y1 + grosor), QPointF(x0 + cx, y0 + grosor), QPointF(x0, y0 + grosor))
            path.closeSubpath()
            color = QColor(cl.color(f["a"]))
            color.setAlpha(150 if self.hover == i else 80)
            p.fillPath(path, color)
            self.bandas.append((path, f.get("filas_a", []), f))
        # Nodos y etiquetas
        p.setPen(Qt.PenStyle.NoPen)
        for lado, nodos, x, tam in (("a", nodos_a, xa, ta), ("b", nodos_b, xb, tb)):
            for c, (y, hh) in nodos.items():
                p.setBrush(QColor(cl.color(c)))
                p.drawRoundedRect(QRectF(x, y, ancho_nodo, max(hh, 1.5)), 2, 2)
                texto = f"{cl.glyph(c)} {cl.name(c)} · {tam[c]}"
                p.setPen(QColor(t["text"]))
                if lado == "a":
                    p.drawText(QRectF(0, y, x - 8, max(hh, 16)),
                               Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, texto)
                else:
                    p.drawText(QRectF(x + ancho_nodo + 8, y, 110, max(hh, 16)),
                               Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, texto)
                p.setPen(Qt.PenStyle.NoPen)
        p.end()

    def _banda_en(self, pos) -> int | None:
        for i, (path, _filas, _f) in enumerate(self.bandas):
            if path.contains(QPointF(pos)):
                return i
        return None

    def mouseMoveEvent(self, event) -> None:
        i = self._banda_en(event.position())
        if i != self.hover:
            self.hover = i
            if i is not None:
                f = self.bandas[i][2]
                self.setToolTip(S.CMP_BAND_TIP.format(a=cl.name(f["a"]), b=cl.name(f["b"]), n=f["n"]))
            else:
                self.setToolTip("")
            self.update()

    def mousePressEvent(self, event) -> None:
        i = self._banda_en(event.position())
        if i is not None and self.bandas[i][1]:
            self.band_clicked.emit(list(self.bandas[i][1]))


class ComparisonPanel(QWidget):
    """Barra izquierda (elegir A y B, importar) y resultados a la derecha."""

    changed = Signal()  # elección o soluciones importadas (para marcar la sesión como modificada)
    select_in_analysis = Signal(str, list)  # id del análisis, filas

    def __init__(self, fuentes: Callable[[], list[tuple[str, cmp.Solucion]]], parent: QWidget | None = None):
        super().__init__(parent)
        self.fuentes = fuentes  # soluciones de los análisis de la sesión: (clave, solución)
        self.importadas: list[cmp.Solucion] = []
        self.eleccion: dict[str, str | None] = {"a": None, "b": None}
        self.resultado: dict | None = None

        lateral = QScrollArea()
        lateral.setObjectName("Sidebar")
        lateral.setWidgetResizable(True)
        lateral.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        lateral.setFixedWidth(tk.METRICS["sidebar_width"])
        contenido = QWidget()
        contenido.setObjectName("SidebarContent")
        lc = QVBoxLayout(contenido)
        lc.setContentsMargins(16, 16, 16, 16)
        lc.setSpacing(10)
        lc.addWidget(_label(S.CMP_TITLE.upper(), "SidebarTitle", wrap=False))

        tarjeta = QFrame()
        tarjeta.setObjectName("StepCard")
        tc = QVBoxLayout(tarjeta)
        tc.setContentsMargins(14, 12, 14, 12)
        tc.setSpacing(6)
        tc.addWidget(_label(S.CMP_SOLUTIONS, "StepTitle", wrap=False))
        self.combo_a, self.combo_b = QComboBox(), QComboBox()
        for nombre, combo in (("A", self.combo_a), ("B", self.combo_b)):
            combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            combo.setMinimumContentsLength(10)
            tc.addWidget(_label(S.CMP_SOLUTION.format(x=nombre), "FieldLabel", wrap=False))
            tc.addWidget(combo)
            combo.activated.connect(self._eleccion_cambiada)
        self.swap = QPushButton(S.CMP_SWAP)
        self.swap.setObjectName("LinkButton")
        self.swap.clicked.connect(self._intercambiar)
        tc.addWidget(self.swap, 0, Qt.AlignmentFlag.AlignLeft)
        lc.addWidget(tarjeta)

        imp = QFrame()
        imp.setObjectName("StepCard")
        ic = QVBoxLayout(imp)
        ic.setContentsMargins(14, 12, 14, 12)
        ic.setSpacing(6)
        ic.addWidget(_label(S.CMP_IMPORTED, "StepTitle", wrap=False))
        ic.addWidget(_label(S.CMP_IMPORT_HINT, "Hint"))
        fila = QHBoxLayout()
        self.import_session = QPushButton(S.CMP_FROM_SESSION)
        self.import_csv = QPushButton(S.CMP_FROM_CSV)
        self.import_session.clicked.connect(self.importar_sesion)
        self.import_csv.clicked.connect(self.importar_csv)
        fila.addWidget(self.import_session)
        fila.addWidget(self.import_csv)
        ic.addLayout(fila)
        self.lista = QListWidget()
        self.lista.setObjectName("ImportedList")
        self.lista.setMaximumHeight(110)
        ic.addWidget(self.lista)
        self.quitar = QPushButton(S.CMP_REMOVE)
        self.quitar.setObjectName("LinkButton")
        self.quitar.clicked.connect(self._quitar_importada)
        ic.addWidget(self.quitar, 0, Qt.AlignmentFlag.AlignLeft)
        lc.addWidget(imp)
        lc.addStretch(1)
        lateral.setWidget(contenido)

        # Resultados
        self.vacio = _label(S.CMP_EMPTY, "EmptyBody")
        self.vacio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error = _label("", "ValidationNote")
        self.kpis = QWidget()
        kr = QHBoxLayout(self.kpis)
        kr.setContentsMargins(0, 0, 0, 0)
        kr.setSpacing(10)
        self.kpi_ari = KpiCard(S.KPI_CMP_ARI, "—", "")
        self.kpi_same = KpiCard(S.KPI_CMP_SAME, "—", "")
        self.kpi_disc = KpiCard(S.KPI_CMP_DISC, "—", "")
        for card in (self.kpi_ari, self.kpi_same, self.kpi_disc):
            kr.addWidget(card, 1)
        self.nota = _label("", "Hint")
        self.ver_disc = QPushButton(S.CMP_SELECT_DISC)
        self.ver_disc.clicked.connect(self._seleccionar_discordantes)
        fila_disc = QHBoxLayout()
        fila_disc.addWidget(self.ver_disc)
        fila_disc.addStretch(1)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("ResultTabs")
        self.tabs.setDocumentMode(True)
        self.sankey = Sankey()
        self.sankey.band_clicked.connect(self._seleccionar_banda)
        sk = QWidget()
        skl = QVBoxLayout(sk)
        skl.setContentsMargins(0, 10, 0, 0)
        skl.addWidget(self.sankey, 1)
        skl.addWidget(_label(S.CMP_SANKEY_HINT, "Hint"))
        self.tabs.addTab(sk, S.CMP_TAB_FLOW)
        self.cruzada = QTableWidget()
        self.cruzada.setObjectName("IndexTable")
        self.cruzada.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        cz = QWidget()
        czl = QVBoxLayout(cz)
        czl.setContentsMargins(0, 10, 0, 0)
        czl.addWidget(self.cruzada)
        czl.addWidget(_label(S.CMP_CROSSTAB_HINT, "Hint"))
        self.tabs.addTab(cz, S.CMP_TAB_CROSSTAB)
        self.disc_tabla = QTableWidget()
        self.disc_tabla.setObjectName("IndexTable")
        self.disc_tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        dz = QWidget()
        dzl = QVBoxLayout(dz)
        dzl.setContentsMargins(0, 10, 0, 0)
        self.disc_nota = _label("", "Hint")
        dzl.addWidget(self.disc_nota)
        dzl.addWidget(self.disc_tabla)
        self.tabs.addTab(dz, S.CMP_TAB_DISC)

        self.resultados = QFrame()
        self.resultados.setObjectName("Panel")
        rc = QVBoxLayout(self.resultados)
        rc.setContentsMargins(20, 16, 20, 16)
        rc.setSpacing(10)
        rc.addWidget(self.vacio, 1)
        rc.addWidget(self.error)
        rc.addWidget(self.kpis)
        rc.addWidget(self.nota)
        rc.addLayout(fila_disc)
        rc.addWidget(self.tabs, 1)
        derecha = QWidget()
        dl = QVBoxLayout(derecha)
        dl.setContentsMargins(16, 16, 16, 16)
        dl.addWidget(self.resultados)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        row.addWidget(lateral)
        row.addWidget(derecha, 1)
        self.refresh()

    # --- Fuentes -------------------------------------------------------
    def soluciones(self) -> list[tuple[str, cmp.Solucion]]:
        out = list(self.fuentes())
        out += [(f"importada:{i}", s) for i, s in enumerate(self.importadas)]
        return out

    def refresh(self, *_args) -> None:
        """Rehace las listas (han cambiado los análisis o las importadas) y la comparación."""
        sols = self.soluciones()
        claves = [c for c, _ in sols]
        for lado, combo in (("a", self.combo_a), ("b", self.combo_b)):
            combo.blockSignals(True)
            combo.clear()
            for clave, s in sols:
                combo.addItem(s.nombre, clave)
            elegida = self.eleccion[lado]
            if elegida not in claves:
                elegida = claves[0 if lado == "a" else min(1, len(claves) - 1)] if claves else None
                self.eleccion[lado] = elegida
            combo.setCurrentIndex(max(combo.findData(elegida), 0))
            combo.blockSignals(False)
        self.lista.clear()
        self.lista.addItems([f"{s.nombre} · k = {s.k}" for s in self.importadas])
        self.lista.setVisible(bool(self.importadas))
        self.quitar.setVisible(bool(self.importadas))
        self._comparar()

    def _eleccion_cambiada(self, *_args) -> None:
        self.eleccion = {"a": self.combo_a.currentData(), "b": self.combo_b.currentData()}
        self.changed.emit()
        self._comparar()

    def _intercambiar(self) -> None:
        self.eleccion = {"a": self.eleccion["b"], "b": self.eleccion["a"]}
        self.changed.emit()
        self.refresh()

    def _comparar(self) -> None:
        sols = dict(self.soluciones())
        a, b = sols.get(self.eleccion["a"]), sols.get(self.eleccion["b"])
        self.resultado = None
        self.error.hide()
        if len(sols) < 2 or a is None or b is None or self.eleccion["a"] == self.eleccion["b"]:
            self._mostrar(None, S.CMP_EMPTY if len(sols) < 2 else S.CMP_SAME)
            return
        try:
            self.resultado = cmp.comparar(a, b)
        except ErrorUsuario as e:
            self._mostrar(None, "")
            self.error.setText(str(e))
            self.error.show()
            return
        self._mostrar(self.resultado, "")

    def _mostrar(self, r: dict | None, vacio: str) -> None:
        for w in (self.kpis, self.nota, self.tabs, self.ver_disc):
            w.setVisible(r is not None)
        self.vacio.setText(vacio)
        self.vacio.setVisible(r is None and bool(vacio))
        self.sankey.set_result(r)
        if r is None:
            return
        lo, hi = r["ari_ic"]
        self.kpi_ari.set_value(fmt.num(r["ari"]), f"{r['interpretacion']} · IC95 % {fmt.num(lo)} – {fmt.num(hi)}")
        if r["mismo_k"]:
            self.kpi_same.set_value(fmt.pct(r["concordancia_pct"], 1), S.KPI_CMP_SAME_NOTE)
        else:
            self.kpi_same.set_value("—", S.KPI_CMP_DIFF_K)
        self.kpi_disc.set_value(str(r["n_discordantes"]), S.KPI_CMP_DISC_NOTE.format(n=r["comunes"]))
        partes = [S.CMP_MATCHED_BY_ID if r["por"] == "id" else S.CMP_MATCHED_BY_ROW]
        if r["solo_a"] or r["solo_b"]:
            partes.append(S.CMP_PARTIAL.format(n=r["comunes"], a=r["solo_a"], b=r["solo_b"]))
        self.nota.setText(" ".join(partes))
        self.ver_disc.setEnabled(bool(r["n_discordantes"]) and str(self.eleccion["a"]).startswith("analisis:"))
        self._llenar_cruzada(r)
        self._llenar_discordantes(r)

    def _llenar_cruzada(self, r: dict) -> None:
        t = tk.tokens(theme.is_dark())
        orden = r["orden_b"]
        self.cruzada.setRowCount(r["k_a"])
        self.cruzada.setColumnCount(len(orden))
        self.cruzada.setVerticalHeaderLabels([f"A · {cl.name(c)}" for c in range(r["k_a"])])
        self.cruzada.setHorizontalHeaderLabels([f"B · {cl.name(c)}" for c in orden])
        for i in range(r["k_a"]):
            total = max(sum(r["cruzada"][i]), 1)
            for j, c in enumerate(orden):
                n = r["cruzada"][i][c]
                item = QTableWidgetItem(f"{n}  ({fmt.pct(100 * n / total, 0)})" if n else "·")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if n:
                    color = QColor(t["accent"] if r["pareja"].get(i) == c else t["stale"])
                    color.setAlpha(int(25 + 120 * n / total))
                    item.setBackground(color)
                self.cruzada.setItem(i, j, item)
        self.cruzada.resizeColumnsToContents()

    def _llenar_discordantes(self, r: dict) -> None:
        d = r["discordantes"]
        prob = r.get("prob_b") or r.get("prob_a")
        cabecera = [S.CMP_HEAD_ID if d["ids"] else S.PREP_ROW, "A", "B"] + ([S.CMP_HEAD_PROB] if prob else [])
        self.disc_tabla.setColumnCount(len(cabecera))
        self.disc_tabla.setHorizontalHeaderLabels(cabecera)
        n = len(d["a"])
        self.disc_tabla.setRowCount(n)
        for i in range(n):
            ident = d["ids"][i] if d["ids"] else str(d["fila_a"][i] + 1)
            ca, cb = d["a"][i], d["b"][i]
            celdas = [ident, f"{cl.glyph(ca)} {cl.name(ca)}", f"{cl.glyph(cb)} {cl.name(cb)}"]
            if prob:
                celdas.append(fmt.num(prob["por_discordante"][i]))
            for j, texto in enumerate(celdas):
                self.disc_tabla.setItem(i, j, QTableWidgetItem(texto))
        self.disc_tabla.resizeColumnsToContents()
        nota = ""
        if prob and prob["discordantes"] is not None and prob["concordantes"] is not None:
            nota = S.CMP_PROB_NOTE.format(d=fmt.num(prob["discordantes"]), c=fmt.num(prob["concordantes"]))
        self.disc_nota.setText(nota)
        self.disc_nota.setVisible(bool(nota))

    # --- Selección en la tabla del análisis A --------------------------
    def _analisis_a(self) -> str | None:
        clave = str(self.eleccion["a"])
        return clave.split(":", 1)[1] if clave.startswith("analisis:") else None

    def _seleccionar_discordantes(self) -> None:
        if self.resultado and self._analisis_a():
            self.select_in_analysis.emit(self._analisis_a(), list(self.resultado["discordantes"]["fila_a"]))

    def _seleccionar_banda(self, filas: list[int]) -> None:
        if self._analisis_a() and filas and filas[0] >= 0:
            self.select_in_analysis.emit(self._analisis_a(), filas)

    # --- Importar ------------------------------------------------------
    def importar_sesion(self, path: str | None = None) -> None:
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, S.CMP_FROM_SESSION, "", S.SESSION_FILTER)
        if not path:
            return
        try:
            disponibles = cmp.desde_sesion(path)
        except (ErrorUsuario, OSError) as e:
            QMessageBox.warning(self, S.CMP_TITLE, str(e))
            return
        sols = disponibles.soluciones
        if len(sols) > 1:
            nombre, ok = self._elegir([s.nombre for s in sols])
            if not ok:
                return
            sols = [s for s in sols if s.nombre == nombre]
        self._anadir(sols[0])

    def _elegir(self, nombres: list[str]) -> tuple[str, bool]:
        return QInputDialog.getItem(self, S.CMP_FROM_SESSION, S.CMP_CHOOSE, nombres, 0, False)

    def importar_csv(self, path: str | None = None) -> None:
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, S.CMP_FROM_CSV, "", S.OPEN_DIALOG_FILTER)
        if not path:
            return
        try:
            self._anadir(cmp.desde_csv(path))
        except (ErrorUsuario, OSError) as e:
            QMessageBox.warning(self, S.CMP_TITLE, str(e))

    def _anadir(self, s: cmp.Solucion) -> None:
        self.importadas.append(s)
        self.eleccion["b"] = f"importada:{len(self.importadas) - 1}"
        self.changed.emit()
        self.refresh()

    def _quitar_importada(self) -> None:
        i = self.lista.currentRow()
        if i < 0 and self.importadas:
            i = len(self.importadas) - 1
        if 0 <= i < len(self.importadas):
            self.importadas.pop(i)
            self.eleccion = {k: (None if v and v.startswith("importada:") else v) for k, v in self.eleccion.items()}
            self.changed.emit()
            self.refresh()

    # --- Sesión ----------------------------------------------------------
    def to_dict(self) -> dict:
        return {"importadas": [s.to_dict() for s in self.importadas], "eleccion": dict(self.eleccion)}

    def load(self, d: dict | None) -> None:
        d = d or {}
        self.importadas = [cmp.Solucion.from_dict(s) for s in d.get("importadas", [])]
        self.eleccion = {"a": None, "b": None, **d.get("eleccion", {})}
        self.refresh()

