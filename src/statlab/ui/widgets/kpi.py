"""Tarjeta de cifra clave: título, valor grande y una línea de contexto."""
from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class KpiCard(QFrame):
    def __init__(self, title: str, value: str, note: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("KpiCard")
        col = QVBoxLayout(self)
        col.setContentsMargins(14, 10, 14, 10)
        col.setSpacing(2)
        self.title = QLabel(title)
        self.title.setObjectName("KpiTitle")
        self.title.setWordWrap(True)
        self.value = QLabel(value)
        self.value.setObjectName("KpiValue")
        self.note = QLabel(note)
        self.note.setObjectName("KpiNote")
        self.note.setWordWrap(True)
        self.note.setVisible(bool(note))
        for w in (self.title, self.value, self.note):
            col.addWidget(w)

    def set_value(self, value: str, note: str = "") -> None:
        self.value.setText(value)
        self.note.setText(note)
        self.note.setVisible(bool(note))
