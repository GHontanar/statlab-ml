"""Tarjeta de un paso de la barra lateral.

- hecho: ✓ verde, resumen de una línea y enlace «Editar» (clic en la tarjeta la reabre);
- activo: borde azul, controles del paso, avisos de validación y botón principal;
- pendiente: atenuada;
- desactualizado: ámbar, conserva el resumen y ofrece «Recalcular».
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from statlab import strings_es as S
from statlab.core.flow import EstadoPaso


def _repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class StepCard(QFrame):
    reopen_requested = Signal()
    primary_clicked = Signal()
    recalc_clicked = Signal()
    cancel_clicked = Signal()

    def __init__(self, number: int, title: str, button_text: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("StepCard")
        self.number = number
        self.content: QWidget | None = None

        self.badge = QLabel(str(number))
        self.badge.setObjectName("StepBadge")
        self.badge.setFixedSize(22, 22)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title = QLabel(title)
        self.title.setObjectName("StepTitle")
        self.edit_link = QPushButton(S.EDIT)
        self.edit_link.setObjectName("LinkButton")
        self.edit_link.clicked.connect(self.reopen_requested)
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title_row.addWidget(self.title, 1)
        title_row.addWidget(self.edit_link)

        self.summary = QLabel()
        self.summary.setObjectName("StepSummary")
        self.summary.setWordWrap(True)

        self.stale_note = QLabel(S.STALE_NOTE)
        self.stale_note.setObjectName("StaleNote")
        self.stale_note.setWordWrap(True)
        self.recalc_button = QPushButton(S.RECALCULATE)
        self.recalc_button.clicked.connect(self.recalc_clicked)

        self.progress = QProgressBar()
        self.progress.setObjectName("StepProgress")
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        self.cancel_button = QPushButton(S.CANCEL)
        self.cancel_button.setObjectName("LinkButton")
        self.cancel_button.clicked.connect(self.cancel_clicked)
        running_row = QHBoxLayout()
        running_row.addWidget(self.progress, 1)
        running_row.addWidget(self.cancel_button)
        self.running_box = QWidget()
        self.running_box.setLayout(running_row)
        running_row.setContentsMargins(0, 0, 0, 0)

        self.errors = QLabel()
        self.errors.setObjectName("ValidationNote")
        self.errors.setWordWrap(True)

        self.primary = QPushButton(button_text)
        self.primary.setProperty("variant", "primary")
        self.primary.clicked.connect(self.primary_clicked)
        self.has_primary = bool(button_text)

        self.body = QVBoxLayout()
        self.body.setSpacing(6)
        self.body.addLayout(title_row)
        self.body.addWidget(self.summary)
        self._content_index = self.body.count()
        for w in (self.stale_note, self.recalc_button, self.running_box, self.errors, self.primary):
            self.body.addWidget(w)

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 12, 12, 12)
        row.setSpacing(10)
        row.addWidget(self.badge, 0, Qt.AlignmentFlag.AlignTop)
        row.addLayout(self.body, 1)

        self.set_state(EstadoPaso.PENDIENTE)

    # --- Contenido -------------------------------------------------------
    def set_content(self, widget: QWidget | None) -> None:
        """Controles del paso. Si el widget tiene `set_compact`, también se muestra
        (compacto) cuando el paso está hecho, en lugar del resumen de texto."""
        if widget is None:
            return
        self.content = widget
        self.body.insertWidget(self._content_index, widget)

    @property
    def content_always(self) -> bool:
        return self.content is not None and hasattr(self.content, "set_compact")

    # --- Estado ----------------------------------------------------------
    @property
    def state(self) -> EstadoPaso:
        return EstadoPaso(self.property("state"))

    def set_state(self, state: EstadoPaso) -> None:
        self.setProperty("state", state.value)
        self.badge.setProperty("state", state.value)
        self.badge.setText("✓" if state == EstadoPaso.HECHO else str(self.number))
        self.setCursor(Qt.CursorShape.PointingHandCursor if self.reopenable else Qt.CursorShape.ArrowCursor)
        for w in (self, self.badge, *self.findChildren(QLabel)):
            _repolish(w)

    @property
    def reopenable(self) -> bool:
        return self.state in (EstadoPaso.HECHO, EstadoPaso.DESACTUALIZADO)

    def update_view(
        self,
        state: EstadoPaso,
        summary: str,
        errors: list[str],
        running: bool,
        can_recalc: bool,
        edit_text: str = S.EDIT,
    ) -> None:
        self.set_state(state)
        active = state == EstadoPaso.ACTIVO
        done_like = self.reopenable

        self.edit_link.setText(edit_text)
        self.edit_link.setVisible(done_like)
        show_summary = bool(summary) and (done_like or (active and self.content is None))
        if self.content_always:
            show_summary = False
        self.summary.setText(summary)
        self.summary.setVisible(show_summary)
        if self.content is not None:
            if self.content_always:
                self.content.set_compact(not active)
                self.content.setVisible(state != EstadoPaso.PENDIENTE)
            else:
                self.content.setVisible(active)

        stale = state == EstadoPaso.DESACTUALIZADO
        self.stale_note.setVisible(stale)
        self.recalc_button.setVisible(stale and can_recalc and not running)
        self.running_box.setVisible(running and not active)
        self.errors.setText("\n".join(errors))
        self.errors.setVisible(active and bool(errors) and not running)
        self.primary.setVisible(active and self.has_primary)
        self.primary.setEnabled(not errors and not running)

    def set_progress(self, fraction: float) -> None:
        if self.progress.maximum() == 0:
            self.progress.setRange(0, 1000)
        self.progress.setValue(int(fraction * 1000))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.reopenable:
            self.reopen_requested.emit()
        super().mousePressEvent(event)
