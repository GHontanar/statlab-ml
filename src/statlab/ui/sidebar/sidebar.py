"""Barra lateral de proceso: una tarjeta por paso del módulo activo."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from statlab import strings_es as S
from statlab.modules.base import AnalysisModule, EstadoPaso
from statlab.ui.sidebar.step_card import StepCard


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

        first = next(iter(self.cards.values()))
        first.set_state(EstadoPaso.ACTIVO)
        first.set_summary(S.STEP_DATA_HINT)
