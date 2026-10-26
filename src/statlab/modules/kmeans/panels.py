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
    QVBoxLayout,
    QWidget,
)

from statlab import strings_es as S
from statlab.core import fmt
from statlab.modules.kmeans.module import k_elegido
from statlab.ui import theme
from statlab.ui.charts.sweep import KChart, elbow_chart, silhouette_chart
from statlab.ui.session import SessionController
from statlab.ui.widgets.flow_layout import FlowLayout


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


class FitTable(QTableWidget):
    """Tabla sin scroll propio: su altura se ajusta a las filas (una vez aplicado el estilo)."""

    def fit_height(self) -> None:
        self.resizeRowsToContents()
        rows = sum(self.rowHeight(i) for i in range(self.rowCount()))
        self.setFixedHeight(self.horizontalHeader().sizeHint().height() + rows + 2 * self.frameWidth() + 2)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.fit_height()


def index_table(r: dict) -> QTableWidget:
    """Índices por k; el mejor de cada columna, en negrita."""
    boot = r.get("boot")
    table = FitTable(len(r["ks"]), len(S.INDEX_TABLE_HEAD))
    table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    table.setObjectName("IndexTable")
    table.setHorizontalHeaderLabels(S.INDEX_TABLE_HEAD)
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
        cells = [str(k), fmt.num(r["inercia"][i], 1), fmt.num(r["silueta"][i], 3), ic,
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
        for text in (S.BEST_K_SIL.format(k=m["silueta"]), S.BEST_K_CH.format(k=m["ch"]),
                     S.BEST_K_DB.format(k=m["db"]), S.BEST_K_ELBOW.format(k=m["codo"])):
            chip = QLabel(text)
            chip.setObjectName("KChip")
            chip.ensurePolished()
            flow.addWidget(chip)
        best_row.addWidget(chips, 1)

        self.elbow = elbow_chart(r)
        self.silhouette = silhouette_chart(r)
        for chart in (self.elbow, self.silhouette):
            chart.k_clicked.connect(self._choose)
        charts = QHBoxLayout()
        charts.setSpacing(12)
        charts.addWidget(_chart_box(S.CHART_ELBOW, self.elbow), 1)
        charts.addWidget(_chart_box(S.CHART_SIL, self.silhouette), 1)

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

