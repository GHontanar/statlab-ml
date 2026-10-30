"""Panel inferior del modo «Preparar datos»: diagrama de flujo de pacientes."""
from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from statlab import strings_es as S
from statlab.core.prep.preparacion import FlujoPacientes, diagrama_flujo
from statlab.core.report import figures as fig
from statlab.ui import theme
from statlab.ui.session import SessionController
from statlab.ui.theme import tokens as tk


class FlowDiagram(QWidget):
    BOX_W, BOX_H, SIDE_W, GAP = 230, 42, 280, 12

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.flujo: FlujoPacientes | None = None
        self.setMinimumHeight(160)

    def set_flujo(self, flujo: FlujoPacientes | None) -> None:
        self.flujo = flujo
        self.setMinimumSize(self.sizeHint())
        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QSize:
        n = len(self.flujo.exclusiones) if self.flujo else 0
        return QSize(self.BOX_W + self.SIDE_W + 80, 2 * self.BOX_H + n * (self.BOX_H + self.GAP) + 2 * self.GAP + 24)

    def paintEvent(self, _event) -> None:
        if self.flujo is None:
            return
        t = tk.tokens(theme.is_dark())
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        f = self.flujo
        x0, y0 = 16, 10
        n = len(f.exclusiones)
        alto_medio = max(n, 0) * (self.BOX_H + self.GAP) + self.GAP
        cx = x0 + self.BOX_W / 2
        top = QRectF(x0, y0, self.BOX_W, self.BOX_H)
        bottom = QRectF(x0, y0 + self.BOX_H + alto_medio + self.GAP, self.BOX_W, self.BOX_H)
        pen = QPen(QColor(t["text_muted"]), 1.2)
        p.setPen(pen)
        p.drawLine(int(cx), int(top.bottom()), int(cx), int(bottom.top()))
        for i, (motivo, k) in enumerate(f.exclusiones):
            y = top.bottom() + self.GAP + i * (self.BOX_H + self.GAP) + self.BOX_H / 2
            side = QRectF(x0 + self.BOX_W + 50, y - self.BOX_H / 2, self.SIDE_W, self.BOX_H)
            p.setPen(pen)
            p.drawLine(int(cx), int(y), int(side.left()), int(y))
            self._box(p, side, S.FLOW_EXCLUDED.format(motivo=motivo, n=fig.fmt_n(k)), t, fuerte=False)
        self._box(p, top, S.FLOW_TOTAL.format(n=fig.fmt_n(f.n_total)), t, fuerte=True)
        self._box(p, bottom, S.FLOW_FINAL.format(n=fig.fmt_n(f.n_final)), t, fuerte=True)
        p.end()

    def _box(self, p: QPainter, r: QRectF, texto: str, t: dict, fuerte: bool) -> None:
        p.setPen(QPen(QColor(t["accent"] if fuerte else t["border_strong"]), 1.2))
        p.setBrush(QColor(t["accent_soft"] if fuerte else t["panel"]))
        p.drawRoundedRect(r, 6, 6)
        p.setPen(QColor(t["text"]))
        p.drawText(r.adjusted(8, 2, -8, -2), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, texto)


class PrepResults(QFrame):
    def __init__(self, session: SessionController, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Panel")
        self.session = session
        col = QVBoxLayout(self)
        col.setContentsMargins(20, 16, 20, 16)
        head = QHBoxLayout()
        titulo = QLabel(S.FLOW_TITLE)
        titulo.setObjectName("SectionTitle")
        head.addWidget(titulo)
        head.addStretch(1)
        self.export = QPushButton(S.FLOW_EXPORT)
        self.export.clicked.connect(self.exportar)
        head.addWidget(self.export)
        col.addLayout(head)
        self.nota = QLabel(S.FLOW_NOTE)
        self.nota.setObjectName("Hint")
        self.nota.setWordWrap(True)
        col.addWidget(self.nota)
        self.diagrama = FlowDiagram()
        scroll = QScrollArea()
        scroll.setObjectName("FlowScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.diagrama)
        col.addWidget(scroll, 1)
        for s in (session.prep_changed, session.dataset_changed, session.rows_changed):
            s.connect(self.refresh)
        self.refresh()

    def flujo(self) -> FlujoPacientes | None:
        ds = self.session.dataset
        if ds is None:
            return None
        return diagrama_flujo(ds, self.session.prep.receta if self.session.prep else None)

    def refresh(self, *_args) -> None:
        f = self.flujo()
        self.diagrama.set_flujo(f)
        self.export.setEnabled(f is not None)

    def exportar(self) -> None:
        f = self.flujo()
        if f is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, S.FLOW_EXPORT, "flujo_pacientes.png", S.FLOW_FILTER)
        if not path:
            return
        try:
            figura = fig.flujo_pacientes(f)
            with fig._style():
                figura.savefig(path, dpi=300, facecolor="white")
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, S.FLOW_TITLE, str(e))
