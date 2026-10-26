"""Delegates de la tabla: pastilla de cluster con color y símbolo."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

from statlab.ui import clusters as cl
from statlab.ui import theme
from statlab.ui.data_table.model import ROLE_CLUSTER
from statlab.ui.theme import tokens as tk


class ClusterDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option, index) -> None:
        c = index.data(ROLE_CLUSTER)
        if c is None or c < 0:
            super().paint(painter, option, index)
            return
        t = tk.tokens(theme.is_dark())
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor(t["selection"]))
        else:
            bg = index.data(Qt.ItemDataRole.BackgroundRole)
            if bg is not None:
                painter.fillRect(option.rect, bg)
        fm = QFontMetrics(option.font)
        text = f"{cl.glyph(c)} {cl.name(c)}"
        w, h = fm.horizontalAdvance(text) + 14, fm.height() + 4
        rect = QRectF(option.rect.left() + 8, option.rect.center().y() - h / 2, w, h)
        fill = QColor(cl.color(c))
        fill.setAlpha(46)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(fill)
        painter.drawRoundedRect(rect, h / 2, h / 2)
        painter.setFont(option.font)
        painter.setPen(QColor(cl.color(c)))
        glyph_w = fm.horizontalAdvance(cl.glyph(c) + " ")
        painter.drawText(rect.adjusted(7, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, cl.glyph(c))
        painter.setPen(QColor(t["text"]))
        painter.drawText(rect.adjusted(7 + glyph_w, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, cl.name(c))
        painter.restore()
