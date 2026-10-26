"""Panel de resultados: muestra los paneles del paso más avanzado que tenga resultado."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QScrollArea, QStackedWidget, QVBoxLayout, QWidget

from statlab import strings_es as S
from statlab.core.flow import EstadoPaso
from statlab.ui import theme
from statlab.ui.session import SessionController


class ResultsPanel(QFrame):
    content_shown = Signal()  # pasa de vacío a mostrar resultados

    def __init__(self, session: SessionController, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Panel")
        self.session = session
        self._shown: tuple | None = None
        self.current_step: str | None = None

        self.empty = QLabel(S.RESULTS_EMPTY)
        self.empty.setObjectName("Muted")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.stale = QLabel(S.RESULTS_STALE)
        self.stale.setObjectName("StaleBanner")
        self.stale.setWordWrap(True)
        self.stale.hide()
        self.scroll = QScrollArea()
        self.scroll.setObjectName("ResultsScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        holder = QWidget()
        holder_col = QVBoxLayout(holder)
        holder_col.setContentsMargins(0, 0, 0, 0)
        holder_col.setSpacing(0)
        holder_col.addWidget(self.stale)
        holder_col.addWidget(self.scroll, 1)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.empty)
        self.stack.addWidget(holder)
        col = QVBoxLayout(self)
        col.setContentsMargins(1, 1, 1, 1)
        col.addWidget(self.stack)

        for signal in (session.flow_changed, session.dataset_changed):
            signal.connect(self.refresh)
        session.step_updated.connect(self.refresh)

    def _target(self) -> tuple[str, dict] | None:
        estado = self.session.estado
        for paso in reversed(self.session.module.pasos()):
            r = estado.resultados.get(paso.id)
            if r and "error" not in r and estado.flujo[paso.id] != EstadoPaso.PENDIENTE:
                return paso.id, r
        return None

    def refresh(self, *_args, force: bool = False) -> None:
        target = self._target()
        if target is None:
            self._shown = None
            self.current_step = None
            self.stack.setCurrentWidget(self.empty)
            return
        paso, r = target
        key = (paso, id(r), theme.is_dark())
        if key != self._shown or force:
            widgets = self.session.module.paneles(paso, r, self.session)
            if not widgets:
                self._shown = None
                self.current_step = None
                self.stack.setCurrentWidget(self.empty)
                return
            content = QWidget()
            content.setObjectName("ResultsContent")
            content_col = QVBoxLayout(content)
            content_col.setContentsMargins(0, 0, 0, 0)
            for w in widgets:
                content_col.addWidget(w)
            content_col.addStretch(1)
            old = self.scroll.takeWidget()
            if old is not None:
                old.deleteLater()
            self.scroll.setWidget(content)
            self._shown = key
            self.current_step = paso
        self.stale.setVisible(self.session.flujo[paso] == EstadoPaso.DESACTUALIZADO)
        if self.stack.currentIndex() != 1:
            self.stack.setCurrentIndex(1)
            self.content_shown.emit()
