"""Modelo Qt sobre el DataFrame cargado.

Los textos de cada celda se formatean una sola vez al cargar (coma decimal,
decimales uniformes por columna) para que el scroll sea fluido con 5.000 × 50.
La vista se puede ordenar sin tocar los datos: `_order` traduce fila de la
vista → posición original.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, Qt
from PySide6.QtGui import QColor, QFont

from statlab import strings_es as S
from statlab.core import fmt
from statlab.core.dataset import Dataset, Rol
from statlab.ui import theme
from statlab.ui.theme import tokens as tk

# Roles propios para la cabecera
ROLE_COLUMN_ROLE = Qt.ItemDataRole.UserRole + 1  # Rol | None
ROLE_COLUMN_LOG = Qt.ItemDataRole.UserRole + 2  # bool
ROLE_SORT = Qt.ItemDataRole.UserRole + 3  # Qt.SortOrder | None
ROLE_ROW_ACTIVE = Qt.ItemDataRole.UserRole + 4  # bool

_Index = QModelIndex | QPersistentModelIndex
_ROOT = QModelIndex()


def _format_column(series: pd.Series) -> np.ndarray:
    if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
        d = fmt.column_decimals(series)
        values = series.to_numpy(dtype=float)
        return np.array([fmt.num(v, d) for v in values], dtype=object)
    return np.array(["" if pd.isna(v) else str(v) for v in series], dtype=object)


class DataFrameModel(QAbstractTableModel):
    def __init__(self, dataset: Dataset, parent=None):
        super().__init__(parent)
        self.dataset = dataset
        df = dataset.df
        self._text = [_format_column(df[c]) for c in df.columns]
        self._na = df.isna().to_numpy()
        self._numeric = [dataset.numerica(c) for c in df.columns]
        self._order = np.arange(len(df))
        self._sort: tuple[int, Qt.SortOrder] | None = None
        self._na_font = QFont()
        self._na_font.setItalic(True)
        self._inactive_font = QFont()
        self._inactive_font.setStrikeOut(True)

    # --- Tamaño ---------------------------------------------------------
    def rowCount(self, parent: _Index = _ROOT) -> int:
        return 0 if parent.isValid() else len(self._order)

    def columnCount(self, parent: _Index = _ROOT) -> int:
        return 0 if parent.isValid() else len(self._text)

    # --- Traducción vista ↔ datos ---------------------------------------
    def source_row(self, view_row: int) -> int:
        return int(self._order[view_row])

    def view_row(self, source_row: int) -> int:
        return int(np.flatnonzero(self._order == source_row)[0])

    def column_name(self, col: int) -> str:
        return self.dataset.columnas[col]

    def column_index(self, name: str) -> int:
        return self.dataset.columnas.index(name)

    def cell_text(self, view_row: int, col: int) -> str:
        return self._text[col][self._order[view_row]]

    # --- Datos ----------------------------------------------------------
    def data(self, index: _Index, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        col = index.column()
        src = self._order[index.row()]
        is_na = self._na[src, col]
        if role == Qt.ItemDataRole.DisplayRole:
            return "NA" if is_na else self._text[col][src]
        t = tk.tokens(theme.is_dark())
        active = self.dataset.fila_activa(int(src))
        if role == Qt.ItemDataRole.TextAlignmentRole:
            h = Qt.AlignmentFlag.AlignRight if self._numeric[col] else Qt.AlignmentFlag.AlignLeft
            return int(h | Qt.AlignmentFlag.AlignVCenter)
        if role == Qt.ItemDataRole.ForegroundRole:
            if not active:
                return QColor(t["text_muted"])
            return QColor(t["na_text"] if is_na else t["text_body"])
        if role == Qt.ItemDataRole.BackgroundRole:
            if is_na:
                return QColor(t["na_bg"])
            if self.dataset.roles.get(self.column_name(col)) == Rol.MODELO:
                return QColor(t["role_model_tint"])
            return None
        if role == Qt.ItemDataRole.FontRole:
            if is_na:
                return self._na_font
            if not active:
                return self._inactive_font
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal:
            name = self.column_name(section)
            if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole):
                return name
            if role == ROLE_COLUMN_ROLE:
                return self.dataset.roles.get(name)
            if role == ROLE_COLUMN_LOG:
                return name in self.dataset.log
            if role == ROLE_SORT:
                return self._sort[1] if self._sort and self._sort[0] == section else None
            return None
        src = int(self._order[section])
        if role == Qt.ItemDataRole.DisplayRole:
            return str(src + 1)
        if role == ROLE_ROW_ACTIVE:
            return self.dataset.fila_activa(src)
        return None

    # --- Orden ----------------------------------------------------------
    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        self.layoutAboutToBeChanged.emit()
        if column < 0:
            self._order = np.arange(self.dataset.n_filas)
            self._sort = None
        else:
            series = self.dataset.df.iloc[:, column]
            asc = order == Qt.SortOrder.AscendingOrder
            # Los NA siempre al final; orden estable para empates.
            self._order = series.sort_values(ascending=asc, na_position="last", kind="stable").index.to_numpy()
            self._sort = (column, order)
        self.layoutChanged.emit()

    # --- Avisos de cambios ---------------------------------------------
    def roles_changed(self) -> None:
        last = self.columnCount() - 1
        self.headerDataChanged.emit(Qt.Orientation.Horizontal, 0, last)
        self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount() - 1, last))

    def rows_changed(self) -> None:
        self.headerDataChanged.emit(Qt.Orientation.Vertical, 0, self.rowCount() - 1)
        self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount() - 1, self.columnCount() - 1))

    def na_count(self) -> int:
        return int(self._na.sum())


ROLE_LABELS = {
    Rol.MODELO: S.ROLE_LABEL_MODEL,
    Rol.DESCRIPTIVA: S.ROLE_LABEL_DESCR,
    Rol.IDENTIFICADOR: S.ROLE_LABEL_ID,
}
