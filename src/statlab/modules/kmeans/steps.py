"""Controles de los pasos propios del módulo k-means."""
from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QGridLayout, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget

from statlab import strings_es as S
from statlab.ui.session import SessionController
from statlab.ui.widgets.help import HelpButton

PASO = "preprocesado"


def _label(text: str, help_text: str) -> QWidget:
    w = QWidget()
    row = QHBoxLayout(w)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(4)
    label = QLabel(text)
    label.setObjectName("FieldLabel")
    row.addWidget(label)
    row.addWidget(HelpButton(help_text))
    row.addStretch(1)
    return w


def _combo(options: dict[str, str]) -> QComboBox:
    combo = QComboBox()
    # No pedir el ancho de la opción más larga: la barra lateral es estrecha.
    combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    combo.setMinimumContentsLength(12)
    for key, text in options.items():
        combo.addItem(text, key)
    return combo


class PreprocessWidget(QWidget):
    """Paso 3: valores perdidos y escalado, con vista previa del resultado y avisos."""

    def __init__(self, session: SessionController, parent: QWidget | None = None):
        super().__init__(parent)
        self.session = session

        self.missing = _combo(S.PREP_MISSING_OPTIONS)
        self.neighbors = QSpinBox()
        self.neighbors.setRange(1, 15)
        self.scaling = _combo(S.PREP_SCALING_OPTIONS)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)
        grid.addWidget(_label(S.PREP_MISSING, S.HELP_MISSING), 0, 0, 1, 2)
        grid.addWidget(self.missing, 1, 0, 1, 2)
        self.neighbors_label = _label(S.PREP_NEIGHBORS, S.HELP_NEIGHBORS)
        grid.addWidget(self.neighbors_label, 2, 0)
        grid.addWidget(self.neighbors, 2, 1)
        grid.addWidget(_label(S.PREP_SCALING, S.HELP_SCALING), 3, 0, 1, 2)
        grid.addWidget(self.scaling, 4, 0, 1, 2)
        grid.setColumnStretch(0, 1)

        self.result = QLabel()
        self.result.setObjectName("StepResult")
        self.result.setWordWrap(True)
        self.warnings = QLabel()
        self.warnings.setObjectName("WarningNote")
        self.warnings.setWordWrap(True)

        col = QVBoxLayout(self)
        col.setContentsMargins(0, 4, 0, 0)
        col.setSpacing(8)
        col.addLayout(grid)
        col.addWidget(self.result)
        col.addWidget(self.warnings)

        self.missing.currentIndexChanged.connect(self._changed)
        self.scaling.currentIndexChanged.connect(self._changed)
        self.neighbors.valueChanged.connect(self._changed)
        session.step_updated.connect(self._on_updated)
        session.step_running.connect(self._on_running)
        session.dataset_changed.connect(self._load_params)
        self._load_params()

    def _load_params(self) -> None:
        params = self.session.params(PASO)
        for w in (self.missing, self.scaling, self.neighbors):
            w.blockSignals(True)
        self.missing.setCurrentIndex(self.missing.findData(params["imputacion"]))
        self.scaling.setCurrentIndex(self.scaling.findData(params["escalado"]))
        self.neighbors.setValue(int(params["vecinos"]))
        for w in (self.missing, self.scaling, self.neighbors):
            w.blockSignals(False)
        self._sync_neighbors()
        self._show_result()

    def _changed(self, *_args) -> None:
        self._sync_neighbors()
        self.session.set_params(
            PASO,
            imputacion=self.missing.currentData(),
            escalado=self.scaling.currentData(),
            vecinos=self.neighbors.value(),
        )

    def _sync_neighbors(self) -> None:
        knn = self.missing.currentData() == "knn"
        self.neighbors.setVisible(knn)
        self.neighbors_label.setVisible(knn)

    def _on_updated(self, paso: str) -> None:
        if paso == PASO:
            self._load_params()  # por si cambian desde fuera (p. ej. al abrir una sesión)

    def _on_running(self, paso: str, running: bool) -> None:
        if paso == PASO and running:
            self.result.setText(S.RUNNING)

    def _show_result(self) -> None:
        r = self.session.estado.resultados.get(PASO)
        if self.session.running(PASO) or r is None:
            self.result.setText(S.RUNNING if self.session.running(PASO) else "")
            self.warnings.hide()
            return
        if "error" in r:
            self.result.setText("")
            self.warnings.setText(r["error"])
            self.warnings.show()
            return
        self.result.setText(
            S.PREP_RESULT.format(n=r["n_analizadas"], excl=r["n_excluidas"], imp=r["celdas_imputadas"])
        )
        self.warnings.setText("\n".join(f"• {w}" for w in r["avisos"]))
        self.warnings.setVisible(bool(r["avisos"]))
