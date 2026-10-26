"""Tablas de resultados de solo lectura que se ajustan a su contenido (sin scroll propio)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem

from statlab.ui import theme


class FitTable(QTableWidget):
    """Su altura se ajusta a las filas una vez aplicado el estilo."""

    def fit_height(self) -> None:
        self.resizeRowsToContents()
        rows = sum(self.rowHeight(i) for i in range(self.rowCount()))
        self.setFixedHeight(self.horizontalHeader().sizeHint().height() + rows + 2 * self.frameWidth() + 2)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.fit_height()


def result_table(
    headers: list[str],
    rows: list[list[str]],
    left_cols: set[int] = frozenset({0}),
    bold: set[tuple[int, int]] = frozenset(),
    colors: dict[tuple[int, int], str] | None = None,
) -> FitTable:
    table = FitTable(len(rows), len(headers))
    table.setObjectName("IndexTable")
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().hide()
    table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.setFont(theme.tabular_font())
    header = table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    header.setStretchLastSection(True)
    bold_font = QFont(table.font())
    bold_font.setWeight(QFont.Weight.Bold)
    for i, row in enumerate(rows):
        for j, text in enumerate(row):
            item = QTableWidgetItem("" if text is None else str(text))
            align = Qt.AlignmentFlag.AlignLeft if j in left_cols else Qt.AlignmentFlag.AlignRight
            item.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
            if (i, j) in bold:
                item.setFont(bold_font)
            if colors and (i, j) in colors:
                item.setForeground(QColor(colors[(i, j)]))
            table.setItem(i, j, item)
    table.fit_height()
    return table
