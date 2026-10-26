"""Barra lateral de proceso: una tarjeta por paso del módulo activo."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from statlab import strings_es as S
from statlab.core.dataset import Dataset
from statlab.modules.base import AnalysisModule, EstadoPaso
from statlab.ui.sidebar.step_card import StepCard
from statlab.ui.sidebar.variables import VariablesSummary


class Sidebar(QScrollArea):
    def __init__(self, module: AnalysisModule, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setObjectName("SidebarContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel(S.SIDEBAR_TITLE.upper())
        title.setObjectName("SidebarTitle")
        font = title.font()
        font.setLetterSpacing(font.SpacingType.PercentageSpacing, 106)
        title.setFont(font)
        layout.addWidget(title)

        self.cards: dict[str, StepCard] = {}
        for i, paso in enumerate(module.pasos(), start=1):
            card = StepCard(i, paso.titulo)
            self.cards[paso.id] = card
            layout.addWidget(card)
        layout.addStretch(1)
        self.setWidget(content)

        self.variables = VariablesSummary()
        self.variables.hide()
        self.cards["variables"].set_content(self.variables)

        first = self.cards["datos"]
        first.set_state(EstadoPaso.ACTIVO)
        first.set_summary(S.STEP_DATA_HINT)

    def show_dataset(self, ds: Dataset) -> None:
        # M1: estados mínimos; el stepper completo con invalidación llega en M2.
        data = self.cards["datos"]
        data.set_state(EstadoPaso.HECHO)
        data.set_summary(S.DATA_SUMMARY.format(name=ds.fuente, rows=ds.n_filas, cols=len(ds.columnas)))
        self.cards["variables"].set_state(EstadoPaso.ACTIVO)
        self.variables.show()
        self.update_variables(ds)

    def update_variables(self, ds: Dataset) -> None:
        self.variables.update_from(ds)
