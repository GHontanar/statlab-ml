"""Paneles de resultados del módulo k-means."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from statlab import strings_es as S
from statlab.core import fmt
from statlab.modules.kmeans.module import k_elegido
from statlab.ui import clusters as cl
from statlab.ui import theme
from statlab.ui.charts.clusters import BootHistogram, JaccardChart, PCAChart, ProbHistogram, SilhouetteBars
from statlab.ui.charts.heatmap import Heatmap
from statlab.ui.charts.sweep import KChart, criterion_chart, silhouette_chart
from statlab.ui.session import SessionController
from statlab.ui.widgets.flow_layout import FlowLayout
from statlab.ui.widgets.kpi import KpiCard
from statlab.ui.widgets.tables import FitTable, result_table


def _chart_box(title: str, chart: KChart) -> QFrame:
    box = QFrame()
    box.setObjectName("ChartBox")
    col = QVBoxLayout(box)
    col.setContentsMargins(12, 10, 12, 8)
    col.setSpacing(4)
    label = QLabel(title)
    label.setObjectName("ChartTitle")
    col.addWidget(label)
    col.addWidget(chart, 1)
    return box


def index_table(r: dict) -> QTableWidget:
    """Índices por k; el mejor de cada columna, en negrita."""
    boot = r.get("boot")
    table = FitTable(len(r["ks"]), len(S.INDEX_TABLE_HEAD))
    table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    table.setObjectName("IndexTable")
    criterio = r.get("criterio", {"id": "inercia", "valores": r.get("inercia")})
    head = list(S.INDEX_TABLE_HEAD)
    head[1] = S.CRITERION_HEAD[criterio["id"]]
    table.setHorizontalHeaderLabels(head)
    decimales = {"inercia": 1, "bic": 0, "altura": 2}[criterio["id"]]
    table.verticalHeader().hide()
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.setFont(theme.tabular_font())
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setStretchLastSection(True)
    best = {2: r["mejor"]["silueta"], 4: r["mejor"]["ch"], 5: r["mejor"]["db"]}
    bold = QFont(table.font())
    bold.setWeight(QFont.Weight.Bold)
    for i, k in enumerate(r["ks"]):
        ic = (f"{fmt.num(boot['ic_inf'][i], 3)} – {fmt.num(boot['ic_sup'][i], 3)}" if boot else "—")
        cells = [str(k), fmt.num(criterio["valores"][i], decimales), fmt.num(r["silueta"][i], 3), ic,
                 fmt.num(r["ch"][i], 1), fmt.num(r["db"][i], 3), str(r["tam_min"][i])]
        for j, text in enumerate(cells):
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if best.get(j) == k:
                item.setFont(bold)
                item.setData(Qt.ItemDataRole.UserRole, "best")
            table.setItem(i, j, item)
    table.fit_height()
    return table


class SweepPanel(QWidget):
    """Resultados del paso 4: mejor k por índice, codo, silueta con IC y tabla de índices."""

    def __init__(self, r: dict, session: SessionController, parent: QWidget | None = None):
        super().__init__(parent)
        self.session = session
        self.r = r

        best = QWidget()
        best_row = QHBoxLayout(best)
        best_row.setContentsMargins(0, 0, 0, 0)
        best_row.setSpacing(10)
        title = QLabel(S.BEST_K_TITLE)
        title.setObjectName("SectionTitle")
        best_row.addWidget(title)
        chips = QWidget()
        flow = FlowLayout(chips, spacing=6)
        m = r["mejor"]
        alg = r.get("algoritmo", "kmeans")
        propio = {"kmeans": S.BEST_K_ELBOW, "gmm": S.BEST_K_BIC, "jerarquico": S.BEST_K_HEIGHT}[alg]
        k_propio = m.get("criterio", m.get("codo"))
        for text in (S.BEST_K_SIL.format(k=m["silueta"]), S.BEST_K_CH.format(k=m["ch"]),
                     S.BEST_K_DB.format(k=m["db"]), propio.format(k=k_propio)):
            chip = QLabel(text)
            chip.setObjectName("KChip")
            chip.ensurePolished()
            flow.addWidget(chip)
        best_row.addWidget(chips, 1)

        self.elbow = criterion_chart(r)
        self.silhouette = silhouette_chart(r)
        for chart in (self.elbow, self.silhouette):
            chart.k_clicked.connect(self._choose)
        charts = QHBoxLayout()
        charts.setSpacing(12)
        titulo = {"kmeans": S.CHART_ELBOW, "gmm": S.CHART_BIC, "jerarquico": S.CHART_DENDRO}[alg]
        charts.addWidget(_chart_box(titulo, self.elbow), 1)
        charts.addWidget(_chart_box(S.CHART_SIL, self.silhouette), 1)
        self.bic_note = None
        if alg == "gmm" and r.get("bic_covarianzas"):
            mejor = min(((v, c, k) for c, vals in r["bic_covarianzas"].items()
                         for k, v in zip(r["ks"], vals, strict=True) if v is not None), default=None)
            if mejor:
                self.bic_note = _note(S.BIC_BEST_COV.format(cov=S.COV_SHORT[mejor[1]].lower(), k=mejor[2]))

        self.table = index_table(r)
        note = QLabel(S.INDEX_TABLE_NOTE)
        note.setObjectName("Hint")
        note.setWordWrap(True)

        self.card = QFrame()
        self.card.setObjectName("InfoCard")
        card_col = QVBoxLayout(self.card)
        card_col.setContentsMargins(14, 12, 14, 12)
        card_col.setSpacing(8)
        card_title = QLabel(S.CONTINUE_FINAL_TITLE)
        card_title.setObjectName("SectionTitle")
        self.card_body = QLabel()
        self.card_body.setWordWrap(True)
        self.go = QPushButton(S.CONTINUE_FINAL_BUTTON)
        self.go.setProperty("variant", "primary")
        self.go.clicked.connect(lambda: session.focus_step("modelo_final"))
        card_col.addWidget(card_title)
        card_col.addWidget(self.card_body)
        card_col.addStretch(1)
        card_col.addWidget(self.go)

        bottom = QGridLayout()
        bottom.setHorizontalSpacing(12)
        bottom.setVerticalSpacing(4)
        bottom.addWidget(self.table, 0, 0)
        bottom.addWidget(note, 1, 0)
        bottom.addWidget(self.card, 0, 1, 2, 1)
        bottom.setColumnStretch(0, 3)
        bottom.setColumnStretch(1, 1)

        col = QVBoxLayout(self)
        col.setContentsMargins(16, 14, 16, 16)
        col.setSpacing(12)
        col.addWidget(best)
        col.addLayout(charts)
        if self.bic_note is not None:
            col.addWidget(self.bic_note)
        col.addLayout(bottom)

        session.step_updated.connect(self._on_updated)
        self._show_k()

    def _choose(self, k: int) -> None:
        self.session.set_params("modelo_final", k=int(k))

    def _on_updated(self, paso: str) -> None:
        if paso == "modelo_final":
            self._show_k()

    @property
    def k(self) -> int | None:
        return k_elegido(self.session.estado)

    def _show_k(self) -> None:
        k = self.k
        for chart in (self.elbow, self.silhouette):
            chart.set_selected(k)
        self.card_body.setText(S.CONTINUE_FINAL_BODY.format(k=k))



def _section(title: str, *widgets: QWidget, hint: str = "") -> QFrame:
    box = QFrame()
    box.setObjectName("ChartBox")
    col = QVBoxLayout(box)
    col.setContentsMargins(12, 10, 12, 10)
    col.setSpacing(6)
    label = QLabel(title)
    label.setObjectName("ChartTitle")
    col.addWidget(label)
    for w in widgets:
        col.addWidget(w)
    if hint:
        note = QLabel(hint)
        note.setObjectName("Hint")
        note.setWordWrap(True)
        col.addWidget(note)
    return box


def _note(text: str, name: str = "Hint") -> QLabel:
    label = QLabel(text)
    label.setObjectName(name)
    label.setWordWrap(True)
    return label


class FinalPanel(QWidget):
    """Resultados del paso 5: cifras clave, tamaños y pestañas de resumen, silueta, estabilidad,
    sensibilidad y descriptivas. El PCA está enlazado con la tabla de datos."""

    def __init__(self, r: dict, session: SessionController, parent: QWidget | None = None):
        super().__init__(parent)
        self.session = session
        self.r = r
        k, boot = r["k"], r["boot"]

        kpis = QHBoxLayout()
        kpis.setSpacing(10)
        lo, hi = boot["silueta_ic"]
        self.kpi_sil = KpiCard(S.KPI_SIL, fmt.num(r["silueta_media"]), S.KPI_SIL_NOTE)
        self.kpi_ci = KpiCard(S.KPI_CI, f"{fmt.num(lo, 3)} – {fmt.num(hi, 3)}", S.KPI_CI_NOTE.format(b=boot["B"]))
        self.kpi_ari = KpiCard(S.KPI_ARI, fmt.num(boot["ari_media"]), S.KPI_ARI_NOTE)
        self.kpi_unstable = KpiCard(S.KPI_UNSTABLE, S.KPI_UNSTABLE_VALUE.format(n=r["inestables"], k=k),
                                    S.KPI_UNSTABLE_NOTE)
        for card in (self.kpi_sil, self.kpi_ci, self.kpi_ari, self.kpi_unstable):
            kpis.addWidget(card, 1)

        n = sum(r["tamanos"])
        sizes = " &nbsp;&nbsp; ".join(
            cl.html_label(c, S.SIZE_ITEM.format(n=r["tamanos"][c], pct=fmt.pct(100 * r["tamanos"][c] / n, 0)))
            for c in range(k)
        )
        self.sizes = QLabel(f"<b>{S.SIZES}</b> &nbsp; {sizes}")
        self.sizes.setObjectName("SizesLine")

        self.tabs = QTabWidget()
        self.tabs.setObjectName("ResultTabs")
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self._summary_tab(), S.TAB_SUMMARY)
        self.tabs.addTab(self._silhouette_tab(), S.TAB_SILHOUETTE)
        self.tabs.addTab(self._stability_tab(), S.TAB_STABILITY)
        self.tabs.addTab(self._sensitivity_tab(), S.TAB_SENSITIVITY)
        self.tabs.addTab(self._descriptive_tab(), S.TAB_DESCRIPTIVE)
        if r.get("probabilidad"):
            self.tabs.insertTab(1, self._membership_tab(), S.TAB_MEMBERSHIP)

        col = QVBoxLayout(self)
        col.setContentsMargins(16, 14, 16, 16)
        col.setSpacing(12)
        col.addLayout(kpis)
        col.addWidget(self.sizes)
        col.addWidget(self.tabs)
        col.addWidget(_note(S.NO_TESTS_NOTE, "WarningNote"))

    # --- Pestañas --------------------------------------------------------
    def _summary_tab(self) -> QWidget:
        r = self.r
        self.pca = PCAChart(r)
        self.pca.rows_selected.connect(self._select_rows)
        self.heatmap = Heatmap(r["perfiles"]["z"], r["perfiles"]["columnas"])
        self.heatmap.row_clicked.connect(self._show_profile)
        self.profile = _note("", "StepResult")
        self.profile.hide()
        tab = QWidget()
        row = QHBoxLayout(tab)
        row.setContentsMargins(0, 10, 0, 0)
        row.setSpacing(12)
        row.addWidget(_section(S.PCA_TITLE, self.pca, hint=S.PCA_HINT), 3)
        right = QVBoxLayout()
        right.addWidget(_section(S.HEATMAP_TITLE, self.heatmap, self.profile, hint=S.HEATMAP_HINT))
        right.addStretch(1)
        row.addLayout(right, 2)
        return tab

    def _select_rows(self, rows: list[int]) -> None:
        self.pca.show_selected(rows)
        self.session.select_rows(rows)

    def _show_profile(self, c: int) -> None:
        tabla = self.r["perfiles"]["tabla"]
        cols = tabla["columnas"]
        fila = tabla["filas"][c]
        values = " · ".join(f"{name} {fila[cols.index(name)]}" for name in self.r["perfiles"]["columnas"])
        self.profile.setText(S.HEATMAP_DETAIL.format(cluster=cl.name(c), n=fila[cols.index("n")], values=values))
        self.profile.show()

    def _membership_tab(self) -> QWidget:
        """GMM: probabilidad de pertenencia al cluster asignado; los de frontera, seleccionables."""
        p = self.r["probabilidad"]
        frontera = [self.r["filas"][i] for i, v in enumerate(p["p_max"]) if v < p["umbral"]]
        tab = QWidget()
        col = QVBoxLayout(tab)
        col.setContentsMargins(0, 10, 0, 0)
        col.setSpacing(8)
        formato = S.MEMBERSHIP_NOTE_1 if p["n_frontera"] == 1 else S.MEMBERSHIP_NOTE
        note = formato.format(n=p["n_frontera"], u=fmt.num(p["umbral"], 1), m=fmt.num(p["media"]))
        col.addWidget(_section(S.MEMBERSHIP_TITLE, ProbHistogram(p), hint=note))
        texto = S.MEMBERSHIP_SELECT_1 if len(frontera) == 1 else S.MEMBERSHIP_SELECT.format(n=len(frontera))
        self.frontier_button = QPushButton(texto)
        self.frontier_button.setEnabled(bool(frontera))
        self.frontier_button.clicked.connect(lambda: self._select_rows(frontera))
        row = QHBoxLayout()
        row.addWidget(self.frontier_button)
        row.addStretch(1)
        col.addLayout(row)
        col.addStretch(1)
        return tab

    def _silhouette_tab(self) -> QWidget:
        r = self.r
        self.sil_bars = SilhouetteBars(r)
        note = S.SIL_NOTE.format(mean=fmt.num(r["silueta_media"]), neg=fmt.pct(r["silueta_negativas_pct"]))
        tab = QWidget()
        col = QVBoxLayout(tab)
        col.setContentsMargins(0, 10, 0, 0)
        col.addWidget(_section(S.SIL_TITLE, self.sil_bars, hint=note))
        return tab

    def _stability_tab(self) -> QWidget:
        r, boot = self.r, self.r["boot"]
        charts = QHBoxLayout()
        charts.setSpacing(12)
        charts.addWidget(_section(S.JACCARD_TITLE, JaccardChart(r)), 1)
        charts.addWidget(_section(S.HIST_TITLE, BootHistogram(r)), 1)
        rows, colors = [], {}
        for c in range(r["k"]):
            lo, hi = boot["jaccard_ic"][c]
            rows.append([f"{cl.glyph(c)} {cl.name(c)}", str(r["tamanos"][c]), fmt.num(boot["jaccard_media"][c]),
                         f"{fmt.num(lo)} – {fmt.num(hi)}", fmt.num(boot["disuelto_pct"][c], 1),
                         boot["interpretacion"][c]])
            colors[(c, 0)] = cl.color(c)
        self.stability_table = result_table(S.STABILITY_HEAD, rows, left_cols={0, 5}, colors=colors)
        tab = QWidget()
        col = QVBoxLayout(tab)
        col.setContentsMargins(0, 10, 0, 0)
        col.setSpacing(10)
        col.addLayout(charts)
        col.addWidget(self.stability_table)
        col.addWidget(_note(S.STABILITY_NOTE))
        return tab

    def _sensitivity_tab(self) -> QWidget:
        sens = self.r["sensibilidad"]
        metodos = sens["metodos"]
        ari = sens["ari"]
        rows = [[m] + ["—" if v is None else fmt.num(v) for v in fila] for m, fila in zip(metodos, ari, strict=True)]
        low = any(v is not None and v < 0.8 for i, fila in enumerate(ari) for j, v in enumerate(fila) if i != j)
        self.sensitivity_table = result_table([""] + metodos, rows)
        items = " · ".join(f"{m}: {n}" for m, n in sens["n"].items())
        tab = QWidget()
        col = QVBoxLayout(tab)
        col.setContentsMargins(0, 10, 0, 0)
        col.setSpacing(8)
        col.addWidget(_note(S.SENS_TITLE, "SectionTitle"))
        col.addWidget(self.sensitivity_table)
        col.addWidget(_note(S.SENS_N.format(items=items)))
        self.sensitivity_warning = _note(S.SENS_WARN if low else S.SENS_OK, "WarningNote" if low else "StepResult")
        col.addWidget(self.sensitivity_warning)
        col.addStretch(1)
        return tab

    def _descriptive_tab(self) -> QWidget:
        tab = QWidget()
        col = QVBoxLayout(tab)
        col.setContentsMargins(0, 10, 0, 0)
        col.setSpacing(8)
        desc = self.r.get("descriptivas")
        if not desc:
            col.addWidget(_note(S.DESC_EMPTY))
        else:
            k = self.r["k"]
            clusters = [f"{cl.glyph(c)} {cl.name(c)}" for c in range(k)]
            headers = [S.DESC_HEAD_VAR, S.DESC_HEAD_LEVEL, *clusters, *desc["columnas"][2 + k:]]  # + NA
            rows = [["" if v is None else str(v) for v in fila] for fila in desc["filas"]]
            self.descriptive_table = result_table(headers, rows, left_cols={0, 1})
            col.addWidget(self.descriptive_table)
            col.addWidget(_note(S.DESC_NOTE))
        col.addStretch(1)
        return tab
