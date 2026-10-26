"""Tarjeta de un paso: número o ✓, título, resumen y (si está activo) controles."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from statlab.modules.base import EstadoPaso


def _repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class StepCard(QFrame):
    def __init__(self, number: int, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("StepCard")
        self.number = number

        self.badge = QLabel(str(number))
        self.badge.setObjectName("StepBadge")
        self.badge.setFixedSize(22, 22)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title = QLabel(title)
        self.title.setObjectName("StepTitle")
        self.summary = QLabel()
        self.summary.setObjectName("StepSummary")
        self.summary.setWordWrap(True)
        self.summary.hide()

        self.body = QVBoxLayout()
        self.body.setSpacing(4)
        self.body.addWidget(self.title)
        self.body.addWidget(self.summary)

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 12, 12, 12)
        row.setSpacing(10)
        row.addWidget(self.badge, 0, Qt.AlignmentFlag.AlignTop)
        row.addLayout(self.body, 1)

        self.set_state(EstadoPaso.PENDIENTE)

    @property
    def state(self) -> EstadoPaso:
        return EstadoPaso(self.property("state"))

    def set_state(self, state: EstadoPaso) -> None:
        self.setProperty("state", state.value)
        self.badge.setProperty("state", state.value)
        self.badge.setText("✓" if state == EstadoPaso.HECHO else str(self.number))
        _repolish(self)
        _repolish(self.badge)
        for child in self.findChildren(QLabel):
            _repolish(child)

    def set_content(self, widget: QWidget) -> None:
        """Controles o resumen detallado del paso, bajo el título."""
        self.body.addWidget(widget)

    def set_summary(self, text: str) -> None:
        self.summary.setText(text)
        self.summary.setVisible(bool(text))
