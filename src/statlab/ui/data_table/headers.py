"""Cabeceras de la tabla, pintadas a mano para seguir el tema.

- Columnas: nombre y, debajo, la etiqueta de rol (MODELO / DESCR. / ID / —, más
  la insignia «log»). Las columnas del modelo llevan tinte azul.
- Filas: número de fila original; las filas fuera del análisis, tachadas.
"""
from __future__ import annotations

from PySide6.QtCore import QModelIndex, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter
from PySide6.QtWidgets import QHeaderView

from statlab import strings_es as S
from statlab.core.dataset import Rol
from statlab.ui import theme
from statlab.ui.data_table.model import (
    RESULT,
    ROLE_COLUMN_LOG,
    ROLE_COLUMN_ROLE,
    ROLE_LABELS,
    ROLE_ROW_ACTIVE,
    ROLE_SORT,
)
from statlab.ui.theme import tokens as tk

_ROLE_COLORS = {
    Rol.MODELO: ("role_model_bg", "role_model_fg"),
    Rol.DESCRIPTIVA: ("role_descr_bg", "role_descr_fg"),
    Rol.IDENTIFICADOR: ("role_id_bg", "role_id_fg"),
}
PAD_X = 10


def _chip_font(base: QFont) -> QFont:
    font = QFont(base)
    font.setPixelSize(11)
    font.setWeight(QFont.Weight.DemiBold)
    font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 102)
    return font


def _draw_chip(painter: QPainter, x: int, y: int, text: str, bg: str, fg: str, font: QFont) -> int:
    fm = QFontMetrics(font)
    w, h = fm.horizontalAdvance(text) + 12, fm.height() + 4
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(bg))
    painter.drawRoundedRect(QRectF(x, y, w, h), 4, 4)
    painter.setPen(QColor(fg))
    painter.setFont(font)
    painter.drawText(QRect(x, y, w, h), Qt.AlignmentFlag.AlignCenter, text)
    return w


class RoleHeader(QHeaderView):
    HEIGHT = 56

    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setSectionsClickable(True)
        self.setHighlightSections(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setFixedHeight(self.HEIGHT)
        self.setMinimumSectionSize(64)

    def _selected(self, logical: int) -> bool:
        sm = self.selectionModel()
        return bool(sm and sm.isColumnSelected(logical, QModelIndex()))

    def mousePressEvent(self, event) -> None:
        # Clic derecho sobre una columna ya seleccionada: conservar la selección múltiple.
        if event.button() == Qt.MouseButton.RightButton:
            logical = self.logicalIndexAt(event.position().toPoint())
            if logical >= 0 and self._selected(logical):
                event.accept()
                return
        super().mousePressEvent(event)

    def width_for(self, logical: int) -> int:
        model = self.model()
        bold = QFont(self.font())
        bold.setWeight(QFont.Weight.DemiBold)
        name = model.headerData(logical, Qt.Orientation.Horizontal)
        name_w = QFontMetrics(bold).horizontalAdvance(name) + 16  # hueco para la flecha de orden
        chip = QFontMetrics(_chip_font(self.font()))
        chips_w = chip.horizontalAdvance(S.ROLE_LABEL_MODEL) + 12 + chip.horizontalAdvance(S.ROLE_LABEL_LOG) + 16
        return max(name_w, chips_w) + 2 * PAD_X

    def sizeHint(self) -> QSize:
        size = super().sizeHint()
        size.setHeight(self.HEIGHT)
        return size

    def paintSection(self, painter: QPainter, rect: QRect, logical: int) -> None:
        if not rect.isValid():
            return
        model = self.model()
        t = tk.tokens(theme.is_dark())
        rol = model.headerData(logical, Qt.Orientation.Horizontal, ROLE_COLUMN_ROLE)
        log = model.headerData(logical, Qt.Orientation.Horizontal, ROLE_COLUMN_LOG)
        sort = model.headerData(logical, Qt.Orientation.Horizontal, ROLE_SORT)

        painter.save()
        if self._selected(logical):
            bg = t["selection"]
        elif rol == Rol.MODELO:
            bg = t["accent_soft"]
        else:
            bg = t["header_cell"]
        painter.fillRect(rect, QColor(bg))
        painter.setPen(QColor(t["gridline"]))
        painter.drawLine(rect.topRight(), rect.bottomRight())
        painter.setPen(QColor(t["border"]))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())

        bold = QFont(self.font())
        bold.setWeight(QFont.Weight.DemiBold)
        painter.setFont(bold)
        painter.setPen(QColor(t["text"]))
        name = model.headerData(logical, Qt.Orientation.Horizontal)
        if sort is not None:
            name += "  ▲" if sort == Qt.SortOrder.AscendingOrder else "  ▼"
        name_rect = QRect(rect.left() + PAD_X, rect.top() + 8, rect.width() - 2 * PAD_X, 18)
        elided = QFontMetrics(bold).elidedText(name, Qt.TextElideMode.ElideRight, name_rect.width())
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided)

        chip_font = _chip_font(self.font())
        y = rect.top() + 31
        x = rect.left() + PAD_X
        if rol == RESULT:
            _draw_chip(painter, x, y, S.ROLE_LABEL_RESULT, t["accent"], t["accent_text"], chip_font)
        elif rol in _ROLE_COLORS:
            bg_key, fg_key = _ROLE_COLORS[rol]
            x += _draw_chip(painter, x, y, ROLE_LABELS[rol], t[bg_key], t[fg_key], chip_font) + 4
            if log:
                _draw_chip(painter, x, y, S.ROLE_LABEL_LOG, t["role_log_bg"], t["role_log_fg"], chip_font)
        else:
            painter.setFont(chip_font)
            painter.setPen(QColor(t["text_muted"]))
            painter.drawText(QRect(x, y, 40, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                             S.ROLE_LABEL_NONE)
        painter.restore()


class RowHeader(QHeaderView):
    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Vertical, parent)
        self.setSectionsClickable(True)
        self.setHighlightSections(True)
        self.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.setDefaultSectionSize(28)

    def sizeHint(self) -> QSize:
        size = super().sizeHint()
        model = self.model()
        digits = len(str(model.rowCount())) if model else 3
        size.setWidth(QFontMetrics(self.font()).horizontalAdvance("9" * max(digits, 2)) + 2 * PAD_X + 4)
        return size

    def paintSection(self, painter: QPainter, rect: QRect, logical: int) -> None:
        if not rect.isValid():
            return
        model = self.model()
        t = tk.tokens(theme.is_dark())
        sm = self.selectionModel()
        selected = bool(sm and sm.isRowSelected(logical, QModelIndex()))
        active = model.headerData(logical, Qt.Orientation.Vertical, ROLE_ROW_ACTIVE)

        painter.save()
        painter.fillRect(rect, QColor(t["selection"] if selected else t["header_cell"]))
        painter.setPen(QColor(t["border"]))
        painter.drawLine(rect.topRight(), rect.bottomRight())
        painter.setPen(QColor(t["gridline"]))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        font = QFont(self.font())
        font.setStrikeOut(not active)
        painter.setFont(font)
        painter.setPen(QColor(t["text"] if selected else t["text_muted"]))
        painter.drawText(rect.adjusted(PAD_X, 0, -PAD_X, 0),
                         Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                         model.headerData(logical, Qt.Orientation.Vertical))
        painter.restore()
