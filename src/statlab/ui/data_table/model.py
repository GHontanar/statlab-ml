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
ROLE_CLUSTER = Qt.ItemDataRole.UserRole + 5  # int (−1 si la fila no entró en el modelo)
RESULT = "result"  # «rol» de las columnas que añade el modelo final

_Index = QModelIndex | QPersistentModelIndex
_ROOT = QModelIndex()


def _format_column(series: pd.Series) -> np.ndarray:
    if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
        d = fmt.column_decimals(series)
        values = series.to_numpy(dtype=float)
        return np.array([fmt.num(v, d) for v in values], dtype=object)
    if pd.api.types.is_datetime64_any_dtype(series):
        horas = series.dropna().dt.normalize().ne(series.dropna()).any()
        formato = "%d/%m/%Y %H:%M" if horas else "%d/%m/%Y"
        return np.array(["" if pd.isna(v) else v.strftime(formato) for v in series], dtype=object)
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
        # Columnas de resultado (cluster, silueta), delante de las de los datos
        self._extra: list[str] = []
        self._cluster = np.full(len(df), -1)
        self._sil = np.full(len(df), np.nan)
        self.highlight: int | None = None
        self.etiquetas: dict[str, str] = {}  # nombre → «Etiqueta (unidad)» del diccionario, para el tooltip

    # --- Tamaño ---------------------------------------------------------
    def rowCount(self, parent: _Index = _ROOT) -> int:
        return 0 if parent.isValid() else len(self._order)

    def columnCount(self, parent: _Index = _ROOT) -> int:
        return 0 if parent.isValid() else len(self._extra) + len(self._text)

    # --- Traducción vista ↔ datos ---------------------------------------
    def source_row(self, view_row: int) -> int:
        return int(self._order[view_row])

    def view_row(self, source_row: int) -> int:
        return int(np.flatnonzero(self._order == source_row)[0])

    def column_name(self, col: int) -> str:
        n = len(self._extra)
        return self._extra[col] if col < n else self.dataset.columnas[col - n]

    def column_index(self, name: str) -> int:
        if name in self._extra:
            return self._extra.index(name)
        return self.dataset.columnas.index(name) + len(self._extra)

    def is_result_column(self, col: int) -> bool:
        return col < len(self._extra)

    def cell_text(self, view_row: int, col: int) -> str:
        src = self._order[view_row]
        if self.is_result_column(col):
            return self._result_text(col, src)
        return self._text[col - len(self._extra)][src]

    def _result_text(self, col: int, src: int) -> str:
        if self._extra[col] == S.COL_CLUSTER:
            c = self._cluster[src]
            return f"C{c + 1}" if c >= 0 else "—"
        v = self._sil[src]
        return "—" if np.isnan(v) else fmt.num(v, 3)

    # --- Resultados del modelo ------------------------------------------
    def set_results(self, rows: list[int], labels: list[int], silhouettes: list[float]) -> None:
        self.beginResetModel()
        self._cluster = np.full(self.dataset.n_filas, -1)
        self._sil = np.full(self.dataset.n_filas, np.nan)
        self._cluster[rows] = labels
        self._sil[rows] = silhouettes
        self._extra = [S.COL_CLUSTER, S.COL_SILHOUETTE]
        self._sort = None
        self._order = np.arange(self.dataset.n_filas)
        if self.highlight is not None and self.highlight > max(labels, default=-1):
            self.highlight = None
        self.endResetModel()

    def clear_results(self) -> None:
        if not self._extra:
            return
        self.beginResetModel()
        self._extra = []
        self.highlight = None
        self._sort = None
        self._order = np.arange(self.dataset.n_filas)
        self.endResetModel()

    @property
    def has_results(self) -> bool:
        return bool(self._extra)

    def set_highlight(self, cluster: int | None) -> None:
        self.highlight = cluster
        self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount() - 1, self.columnCount() - 1))

    def _result_data(self, col: int, src: int, role: int):
        if role == Qt.ItemDataRole.DisplayRole:
            return self._result_text(col, src)
        if role == ROLE_CLUSTER and self._extra[col] == S.COL_CLUSTER:
            return int(self._cluster[src])
        if role == Qt.ItemDataRole.TextAlignmentRole:
            h = Qt.AlignmentFlag.AlignLeft if self._extra[col] == S.COL_CLUSTER else Qt.AlignmentFlag.AlignRight
            return int(h | Qt.AlignmentFlag.AlignVCenter)
        t = tk.tokens(theme.is_dark())
        if role == Qt.ItemDataRole.ForegroundRole:
            if self.highlight is not None and self._cluster[src] != self.highlight:
                return QColor(t["text_muted"])
            v = self._sil[src]
            negative = self._extra[col] == S.COL_SILHOUETTE and not np.isnan(v) and v < 0
            return QColor(t["na_text"] if negative else t["text_body"])
        if role == Qt.ItemDataRole.BackgroundRole:
            return self._highlight_brush(src)
        return None

    def _highlight_brush(self, src: int):
        if self.highlight is None or self._cluster[src] != self.highlight:
            return None
        color = QColor(tk.SERIES[self.highlight])
        color.setAlpha(40)
        return color

    # --- Datos ----------------------------------------------------------
    def data(self, index: _Index, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        col = index.column()
        src = self._order[index.row()]
        if self.is_result_column(col):
            return self._result_data(col, int(src), role)
        col -= len(self._extra)
        is_na = self._na[src, col]
        if role == Qt.ItemDataRole.DisplayRole:
            return "NA" if is_na else self._text[col][src]
        t = tk.tokens(theme.is_dark())
        active = self.dataset.fila_activa(int(src))
        if role == Qt.ItemDataRole.TextAlignmentRole:
            h = Qt.AlignmentFlag.AlignRight if self._numeric[col] else Qt.AlignmentFlag.AlignLeft
            return int(h | Qt.AlignmentFlag.AlignVCenter)
        dimmed = self.highlight is not None and self._cluster[src] != self.highlight
        if role == Qt.ItemDataRole.ForegroundRole:
            if not active or dimmed:
                return QColor(t["text_muted"])
            return QColor(t["na_text"] if is_na else t["text_body"])
        if role == Qt.ItemDataRole.BackgroundRole:
            if is_na:
                return QColor(t["na_bg"])
            highlighted = self._highlight_brush(int(src))
            if highlighted is not None:
                return highlighted
            if self.dataset.roles.get(self.dataset.columnas[col]) == Rol.MODELO:
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
            if role == Qt.ItemDataRole.DisplayRole:
                return name
            if role == Qt.ItemDataRole.ToolTipRole:
                return self.etiquetas.get(name, name)
            if role == ROLE_COLUMN_ROLE:
                return RESULT if self.is_result_column(section) else self.dataset.roles.get(name)
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
        if role == Qt.ItemDataRole.ToolTipRole and src in self.dataset.excluidas_receta:
            return S.ROW_EXCLUDED_BY_RECIPE.format(motivo=self.dataset.excluidas_receta[src])
        return None

    # --- Orden ----------------------------------------------------------
    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        self.layoutAboutToBeChanged.emit()
        if column < 0:
            self._order = np.arange(self.dataset.n_filas)
            self._sort = None
        else:
            if self.is_result_column(column) and self._extra[column] == S.COL_CLUSTER:
                series = pd.Series(np.where(self._cluster < 0, np.nan, self._cluster.astype(float)))
            elif self.is_result_column(column):
                series = pd.Series(self._sil)
            else:
                series = self.dataset.df.iloc[:, column - len(self._extra)]
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
