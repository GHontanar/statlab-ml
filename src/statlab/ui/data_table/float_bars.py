"""Barras flotantes sobre la tabla: acciones sobre las columnas o filas seleccionadas."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QPushButton, QWidget

from statlab import strings_es as S


class _FloatBar(QFrame):
    def __init__(self, object_name: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName(object_name)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 70))
        self.setGraphicsEffect(shadow)
        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(14, 6, 6, 6)
        self._row.setSpacing(4)
        self.count = QLabel()
        self.count.setObjectName("FloatCount")
        self._row.addWidget(self.count)
        self._row.addSpacing(8)
        self.hide()

    def _button(self, text: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("FloatButton")
        self._row.addWidget(button)
        return button


class ColumnBar(_FloatBar):
    model_clicked = Signal()
    descr_clicked = Signal()
    log_clicked = Signal()
    clear_clicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__("FloatBarColumns", parent)
        self._button(S.FLOAT_MODEL).clicked.connect(self.model_clicked)
        self._button(S.FLOAT_DESCR).clicked.connect(self.descr_clicked)
        self._button(S.FLOAT_LOG).clicked.connect(self.log_clicked)
        self._button(S.FLOAT_CLEAR_ROLE).clicked.connect(self.clear_clicked)

    def set_count(self, n: int) -> None:
        self.count.setText(S.FLOAT_COLUMNS.format(n=n))
        self.adjustSize()


class RowBar(_FloatBar):
    only_clicked = Signal()
    exclude_clicked = Signal()
    subgroup_clicked = Signal()
    clear_clicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__("FloatBarRows", parent)
        self._button(S.FLOAT_ONLY_THESE).clicked.connect(self.only_clicked)
        self._button(S.FLOAT_EXCLUDE).clicked.connect(self.exclude_clicked)
        self._button(S.FLOAT_SUBGROUP).clicked.connect(self.subgroup_clicked)
        self._button(S.FLOAT_CLEAR).clicked.connect(self.clear_clicked)

    def set_count(self, n: int) -> None:
        self.count.setText(S.FLOAT_ROWS.format(n=n))
        self.adjustSize()
