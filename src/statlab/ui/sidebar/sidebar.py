"""Barra lateral de proceso: una tarjeta por paso del módulo activo, sincronizada con la sesión."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from statlab import strings_es as S
from statlab.core.flow import EstadoPaso
from statlab.ui.session import SessionController
from statlab.ui.sidebar.step_card import StepCard


class Sidebar(QScrollArea):
    change_data_requested = Signal()

    def __init__(self, session: SessionController, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.session = session
        self.pasos = session.module.pasos()

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
        for i, paso in enumerate(self.pasos, start=1):
            card = StepCard(i, paso.titulo, paso.boton)
            card.set_content(paso.crear_widget(session))
            self.cards[paso.id] = card
            layout.addWidget(card)
            if paso.id == "datos":
                card.reopen_requested.connect(self.change_data_requested)
            else:
                card.reopen_requested.connect(lambda p=paso.id: session.reopen(p))
            card.primary_clicked.connect(lambda p=paso.id: session.complete(p))
            card.recalc_clicked.connect(lambda p=paso.id: session.recalculate(p))
            card.cancel_clicked.connect(lambda p=paso.id: session.cancel(p))
        layout.addStretch(1)
        self.setWidget(content)

        for signal in (session.flow_changed, session.roles_changed, session.rows_changed, session.dataset_changed):
            signal.connect(self.refresh)
        session.step_updated.connect(self.refresh)
        session.step_running.connect(self.refresh)
        session.step_progress.connect(lambda p, f: self.cards[p].set_progress(f))
        self.refresh()

    def refresh(self, *_args) -> None:
        estado = self.session.estado
        for paso in self.pasos:
            card = self.cards[paso.id]
            state = estado.flujo[paso.id]
            # Los avisos explican por qué el botón principal no está disponible.
            errors = self.session.validate(paso.id) if state == EstadoPaso.ACTIVO and paso.boton else []
            running = self.session.running(paso.id)
            if running and paso.automatico:
                errors = []  # la vista previa ya dice «Calculando…»
            card.update_view(
                state,
                paso.resumen(estado),
                errors,
                running,
                can_recalc=paso.calcula,
                edit_text=S.CHANGE if paso.id == "datos" else S.EDIT,
            )
