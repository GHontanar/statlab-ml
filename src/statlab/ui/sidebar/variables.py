"""Contenido del paso «Variables y filas»: refleja en tiempo real lo elegido en la tabla."""
from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from statlab import strings_es as S
from statlab.core.dataset import Dataset, Rol
from statlab.ui.session import SessionController
from statlab.ui.widgets.flow_layout import FlowLayout


def role_chip(text: str, role: str) -> QLabel:
    chip = QLabel(text)
    chip.setObjectName("RoleChip")
    chip.setProperty("role", role)
    chip.ensurePolished()  # medir con la fuente y el relleno de la QSS
    return chip


class _ChipGroup(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(4)
        self.label = QLabel()
        self.label.setObjectName("FieldLabel")
        col.addWidget(self.label)
        self.chips = QWidget()
        self.flow = FlowLayout(self.chips)
        col.addWidget(self.chips)

    def set_items(self, label: str, items: list[tuple[str, str]]) -> None:
        self.label.setText(label)
        self.flow.clear()
        for text, role in items:
            chip = role_chip(text, role)
            self.flow.addWidget(chip)
            chip.show()  # sin esperar al bucle de eventos
        self.chips.setVisible(bool(items))
        self.flow.invalidate()
        self.chips.updateGeometry()


class VariablesSummary(QWidget):
    """Paso 2: se rellena desde la tabla y muestra los roles en tiempo real."""

    def __init__(self, session: SessionController, parent: QWidget | None = None):
        super().__init__(parent)
        self.session = session
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 4, 0, 0)
        col.setSpacing(8)
        self.model = _ChipGroup()
        self.descr = _ChipGroup()
        self.facts = QLabel()
        self.facts.setObjectName("StepSummary")
        self.facts.setWordWrap(True)
        self.all_rows = QPushButton(S.VARS_USE_ALL_ROWS)
        self.all_rows.setObjectName("LinkButton")
        self.all_rows.clicked.connect(session.use_all_rows)
        self.hint = QLabel(f"{S.VARS_HINT}\n{S.VARS_SHORTCUTS}")
        self.hint.setObjectName("Hint")
        self.hint.setWordWrap(True)
        for w in (self.model, self.descr, self.facts, self.all_rows, self.hint):
            col.addWidget(w)
        for signal in (session.dataset_changed, session.roles_changed, session.rows_changed):
            signal.connect(self._refresh)

    def set_compact(self, compact: bool) -> None:
        """Cuando el paso está hecho se ocultan las ayudas."""
        self.hint.setVisible(not compact)

    def _refresh(self) -> None:
        if self.session.dataset is not None:
            self.update_from(self.session.dataset)

    def update_from(self, ds: Dataset) -> None:
        model = [(f"{c} · log" if c in ds.log else c, "model") for c in ds.con_rol(Rol.MODELO)]
        self.model.set_items(S.VARS_MODEL.format(n=len(model)), model)
        descr = [(c, "descr") for c in ds.con_rol(Rol.DESCRIPTIVA)]
        self.descr.set_items(S.VARS_DESCR.format(n=len(descr)), descr)
        facts = [S.VARS_ID.format(id=ds.identificador or S.VARS_NONE), S.VARS_ROWS.format(rows=ds.resumen_filas())]
        if ds.subgrupos:
            facts.append(S.VARS_SUBGROUPS.format(names=", ".join(ds.subgrupos)))
        self.facts.setText(" · ".join(facts[:2]) + ("\n" + facts[2] if len(facts) > 2 else ""))
        self.all_rows.setVisible(ds.filtro_filas_activo)
