"""Controles de los pasos propios del módulo k-means."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from statlab import strings_es as S
from statlab.modules.kmeans.module import K_MAX
from statlab.ui.session import SessionController
from statlab.ui.widgets.help import HelpButton
from statlab.ui.widgets.range_slider import RangeSlider
from statlab.ui.widgets.toggle import Toggle

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
        self.neighbors.setFixedWidth(80)
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


class SweepWidget(QWidget):
    """Paso 4: rango de k, inicializaciones, semilla e IC bootstrap de la silueta."""

    PASO = "elegir_k"

    def __init__(self, session: SessionController, parent: QWidget | None = None):
        super().__init__(parent)
        self.session = session

        self.range = RangeSlider(2, K_MAX)
        self.range_value = QLabel()
        self.range_value.setObjectName("StepResult")
        range_head = QHBoxLayout()
        range_head.setContentsMargins(0, 0, 0, 0)
        range_head.addWidget(_label(S.SWEEP_RANGE, S.HELP_RANGE), 1)
        range_head.addWidget(self.range_value)

        self.n_init = QSpinBox()
        self.n_init.setRange(1, 200)
        self.seed = QSpinBox()
        self.seed.setRange(0, 999_999)
        self.boot = Toggle()
        self.boot.setAccessibleName(S.SWEEP_BOOT)
        boot_label = QLabel(S.SWEEP_BOOT)
        boot_label.setWordWrap(True)
        boot_label.setBuddy(self.boot)
        boot_row = QHBoxLayout()
        boot_row.setContentsMargins(0, 0, 0, 0)
        boot_row.setSpacing(8)
        boot_row.addWidget(self.boot)
        boot_row.addWidget(boot_label, 1)
        boot_row.addWidget(HelpButton(S.HELP_BOOT))
        self.B = QSpinBox()
        self.B.setRange(20, 200)
        self.B.setSingleStep(10)
        for spin in (self.n_init, self.seed, self.B):
            spin.setFixedWidth(80)  # la barra lateral es estrecha
        self.B_label = _label(S.SWEEP_BOOT_B, S.HELP_BOOT)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        grid.addWidget(_label(S.SWEEP_NINIT, S.HELP_NINIT), 0, 0)
        grid.addWidget(self.n_init, 0, 1)
        grid.addWidget(_label(S.SWEEP_SEED, S.HELP_SEED), 1, 0)
        grid.addWidget(self.seed, 1, 1)
        grid.addLayout(boot_row, 2, 0, 1, 2)
        grid.addWidget(self.B_label, 3, 0)
        grid.addWidget(self.B, 3, 1)
        grid.setColumnStretch(0, 1)

        col = QVBoxLayout(self)
        col.setContentsMargins(0, 4, 0, 0)
        col.setSpacing(8)
        col.addLayout(range_head)
        col.addWidget(self.range)
        col.addLayout(grid)

        self.range.range_changed.connect(self._changed)
        for spin in (self.n_init, self.seed, self.B):
            spin.valueChanged.connect(self._changed)
        self.boot.toggled.connect(self._changed)
        session.dataset_changed.connect(self._load_params)
        session.step_updated.connect(lambda p: p == self.PASO and self._load_params())
        self._load_params()

    def _widgets(self):
        return (self.range, self.n_init, self.seed, self.boot, self.B)

    def _load_params(self) -> None:
        p = self.session.params(self.PASO)
        for w in self._widgets():
            w.blockSignals(True)
        self.range.set_values(p["k_min"], p["k_max"], emit=False)
        self.n_init.setValue(int(p["n_init"]))
        self.seed.setValue(int(p["semilla"]))
        self.boot.setChecked(bool(p["bootstrap"]))
        self.B.setValue(int(p["B"]))
        for w in self._widgets():
            w.blockSignals(False)
        self._sync()

    def _sync(self) -> None:
        lo, hi = self.range.values()
        self.range_value.setText(S.SWEEP_RANGE_VALUE.format(lo=lo, hi=hi))
        self.B.setVisible(self.boot.isChecked())
        self.B_label.setVisible(self.boot.isChecked())
        self.boot.update()

    def _changed(self, *_args) -> None:
        self._sync()
        lo, hi = self.range.values()
        self.session.set_params(
            self.PASO,
            k_min=lo,
            k_max=hi,
            n_init=self.n_init.value(),
            semilla=self.seed.value(),
            bootstrap=self.boot.isChecked(),
            B=self.B.value(),
        )


class FinalWidget(QWidget):
    """Paso 5: k elegido (también con clic en los gráficos) y remuestras bootstrap."""

    PASO = "modelo_final"
    B_OPTIONS = (50, 100, 200, 500, 1000)

    def __init__(self, session: SessionController, parent: QWidget | None = None):
        super().__init__(parent)
        self.session = session
        self.k = QComboBox()
        self.k.setFixedWidth(80)
        self.B = QComboBox()
        self.B.setFixedWidth(80)
        for b in self.B_OPTIONS:
            self.B.addItem(str(b), b)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        grid.addWidget(_label(S.FINAL_K, S.HELP_FINAL_K), 0, 0)
        grid.addWidget(self.k, 0, 1)
        grid.addWidget(_label(S.FINAL_B, S.HELP_FINAL_B), 1, 0)
        grid.addWidget(self.B, 1, 1)
        grid.setColumnStretch(0, 1)
        hint = QLabel(S.FINAL_K_HINT)
        hint.setObjectName("Hint")
        hint.setWordWrap(True)

        col = QVBoxLayout(self)
        col.setContentsMargins(0, 4, 0, 0)
        col.setSpacing(8)
        col.addLayout(grid)
        col.addWidget(hint)

        self.k.currentIndexChanged.connect(self._changed)
        self.B.currentIndexChanged.connect(self._changed)
        session.dataset_changed.connect(self._load)
        session.step_updated.connect(lambda p: p in (self.PASO, "elegir_k") and self._load())
        self._load()

    def _load(self) -> None:
        from statlab.modules.kmeans.module import k_elegido

        estado = self.session.estado
        sweep = estado.resultados.get("elegir_k") or {}
        for w in (self.k, self.B):
            w.blockSignals(True)
        self.k.clear()
        for k in sweep.get("ks", []):
            self.k.addItem(str(k), k)
        k = k_elegido(estado)
        if k is not None:
            self.k.setCurrentIndex(self.k.findData(k))
        self.B.setCurrentIndex(max(self.B.findData(int(self.session.params(self.PASO)["B"])), 0))
        for w in (self.k, self.B):
            w.blockSignals(False)

    def _changed(self, *_args) -> None:
        if self.k.currentData() is None:
            return
        self.session.set_params(self.PASO, k=int(self.k.currentData()), B=int(self.B.currentData()))


class ExportWidget(QWidget):
    """Paso 6: un botón por exporte; cada uno pide dónde guardar y trabaja en segundo plano."""

    PASO = "exportar"
    TIPOS = (("pdf", S.EXPORT_PDF), ("docx", S.EXPORT_DOCX), ("figuras", S.EXPORT_FIGURES),
             ("csv", S.EXPORT_CSV), ("json", S.EXPORT_JSON), ("md", S.EXPORT_MD), ("todo", S.EXPORT_ALL))

    def __init__(self, session: SessionController, parent: QWidget | None = None):
        super().__init__(parent)
        self.session = session
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 4, 0, 0)
        col.setSpacing(6)
        self.buttons: dict[str, QPushButton] = {}
        for tipo, texto in self.TIPOS:
            button = QPushButton(texto)
            button.setObjectName("ExportButton")
            button.clicked.connect(lambda _=False, t=tipo: self.export(t))
            col.addWidget(button)
            self.buttons[tipo] = button
        self.hint = QLabel(S.EXPORT_HINT)
        self.hint.setObjectName("Hint")
        self.hint.setWordWrap(True)
        col.addWidget(self.hint)
        session.step_running.connect(lambda p, running: p == self.PASO and self._busy(running))

    def set_compact(self, compact: bool) -> None:
        """Los botones siguen visibles con el paso hecho: se puede exportar otra vez."""
        self.hint.setVisible(not compact)

    def _busy(self, running: bool) -> None:
        for button in self.buttons.values():
            button.setEnabled(not running)

    def export(self, tipo: str) -> None:
        destino = self._ask_path(tipo)
        if destino:
            self.session.export(tipo, destino)

    def _ask_path(self, tipo: str) -> str:
        """Diálogo para elegir archivo (o carpeta para «figuras» y «todo»)."""
        from pathlib import Path

        from PySide6.QtWidgets import QFileDialog

        from statlab.ui.main_window import SETTINGS_LAST_DIR, settings

        start = Path(str(settings().value(SETTINGS_LAST_DIR, "")) or Path.home())
        if tipo in ("figuras", "todo"):
            return QFileDialog.getExistingDirectory(self, S.EXPORT_FOLDER, str(start))
        base = Path(self.session.dataset.fuente).stem or "statlab"
        nombre = S.EXPORT_NAMES[tipo].format(base=base)
        path, _ = QFileDialog.getSaveFileName(self, S.STEP_EXPORT, str(start / nombre), S.EXPORT_FILTERS[tipo])
        return path
