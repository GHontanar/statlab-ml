"""Barra lateral del modo «Preparar datos»: archivo, revisión de calidad, receta y diccionario."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from statlab import strings_es as S
from statlab.core import io as sio
from statlab.core.errors import ErrorUsuario
from statlab.core.prep import calidad as q
from statlab.core.prep.receta import Paso
from statlab.ui.prep.dialogs import PasoDialog
from statlab.ui.session import SessionController

# Orden del menú «Añadir paso»
TIPOS_MENU = ["calcular", "tipo", "perdidos", "recodificar", "categorizar", "unidades", "fechas", "seguimiento",
              None, "excluir", "duplicados", None, "renombrar", "quitar"]


def _clear(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.hide()
            w.deleteLater()
        elif item.layout() is not None:
            _clear(item.layout())


def _label(texto: str, name: str = "", wrap: bool = True) -> QLabel:
    lab = QLabel(texto)
    if name:
        lab.setObjectName(name)
    lab.setWordWrap(wrap)
    return lab


class Section(QFrame):
    def __init__(self, titulo: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("PrepSection")
        col = QVBoxLayout(self)
        col.setContentsMargins(14, 12, 14, 12)
        col.setSpacing(8)
        head = QHBoxLayout()
        self.title = _label(titulo, "StepTitle", wrap=False)
        self.counter = _label("", "Hint", wrap=False)
        head.addWidget(self.title)
        head.addStretch(1)
        head.addWidget(self.counter)
        col.addLayout(head)
        self.body = QVBoxLayout()
        self.body.setSpacing(8)
        col.addLayout(self.body)


class ProblemCard(QFrame):
    fix_requested = Signal(object)
    show_requested = Signal(list)
    ignore_requested = Signal(str)

    def __init__(self, p: q.Problema, parent: QWidget | None = None):
        super().__init__(parent)
        self.problema = p
        self.setObjectName("ProblemCard")
        self.setProperty("level", p.nivel)
        col = QVBoxLayout(self)
        col.setContentsMargins(10, 8, 10, 8)
        col.setSpacing(4)
        col.addWidget(_label(p.titulo, "ProblemTitle"))
        col.addWidget(_label(p.detalle, "Hint"))
        row = QHBoxLayout()
        row.setSpacing(12)
        if p.propuesta is not None:
            fix = QPushButton(S.PREP_FIX)
            fix.setObjectName("LinkButton")
            fix.clicked.connect(lambda: self.fix_requested.emit(p))
            row.addWidget(fix)
        if p.filas:
            ver = QPushButton(S.PREP_SHOW_ROWS.format(n=len(p.filas)))
            ver.setObjectName("LinkButton")
            ver.clicked.connect(lambda: self.show_requested.emit(list(p.filas)))
            row.addWidget(ver)
        ignorar = QPushButton(S.PREP_IGNORE)
        ignorar.setObjectName("LinkButton")
        ignorar.clicked.connect(lambda: self.ignore_requested.emit(clave(p)))
        row.addWidget(ignorar)
        row.addStretch(1)
        col.addLayout(row)


def clave(p: q.Problema) -> str:
    return f"{p.codigo}:{p.columna or ''}"


class RecipeRow(QFrame):
    toggled = Signal(str, bool)
    moved = Signal(str, int)
    edit_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, n: int, paso: Paso, informe, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("RecipeRow")
        self.setProperty("state", "off" if not paso.activo else ("error" if informe and not informe.ok else "ok"))
        col = QVBoxLayout(self)
        col.setContentsMargins(4, 6, 4, 6)
        col.setSpacing(2)
        arriba = QHBoxLayout()
        arriba.setSpacing(6)
        self.check = QCheckBox()
        self.check.setChecked(paso.activo)
        self.check.setToolTip(S.PREP_TOGGLE_STEP)
        self.check.toggled.connect(lambda v: self.toggled.emit(paso.id, v))
        arriba.addWidget(self.check, 0, Qt.AlignmentFlag.AlignTop)
        arriba.addWidget(_label(f"{n}. {paso.descripcion}", "RecipeText"), 1)
        col.addLayout(arriba)
        row = QHBoxLayout()
        row.setContentsMargins(24, 0, 0, 0)
        row.setSpacing(2)
        estado = resumen_informe(informe) if paso.activo else S.PREP_STEP_OFF
        nota = _label(estado, "ValidationNote" if informe and not informe.ok and paso.activo else "Hint")
        row.addWidget(nota, 1)
        col.addLayout(row)
        for icono, tip, slot in (
            ("↑", S.PREP_MOVE_UP, lambda: self.moved.emit(paso.id, -1)),
            ("↓", S.PREP_MOVE_DOWN, lambda: self.moved.emit(paso.id, +1)),
            ("✎", S.PREP_EDIT, lambda: self.edit_requested.emit(paso.id)),
            ("✕", S.PREP_DELETE, lambda: self.delete_requested.emit(paso.id)),
        ):
            b = QToolButton()
            b.setObjectName("RowTool")
            b.setText(icono)
            b.setToolTip(tip)
            b.setAutoRaise(True)
            b.clicked.connect(slot)
            row.addWidget(b, 0, Qt.AlignmentFlag.AlignTop)


def resumen_informe(inf) -> str:
    if inf is None:
        return ""
    if not inf.ok:
        return inf.mensaje
    partes = []
    if inf.celdas:
        partes.append(S.PREP_PREVIEW_CELLS.format(n=inf.celdas))
    if inf.filas:
        partes.append(S.PREP_PREVIEW_ROWS.format(n=inf.filas))
    if inf.columnas_nuevas:
        partes.append(S.PREP_PREVIEW_NEWCOLS.format(cols=", ".join(f"«{c}»" for c in inf.columnas_nuevas)))
    texto = " · ".join(partes)
    if inf.mensaje:
        texto = f"{texto}\n{inf.mensaje}" if texto else inf.mensaje
    return texto


class PrepSidebar(QScrollArea):
    continue_requested = Signal()
    dictionary_requested = Signal()
    my_formulas_requested = Signal()

    def __init__(self, session: SessionController, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.session = session
        self.problemas: list[q.Problema] = []

        content = QWidget()
        content.setObjectName("SidebarContent")
        col = QVBoxLayout(content)
        col.setContentsMargins(16, 16, 16, 16)
        col.setSpacing(10)
        title = _label(S.PREP_SIDEBAR_TITLE.upper(), "SidebarTitle", wrap=False)
        col.addWidget(title)

        self.lectura = Section(S.PREP_FILE)
        self.archivo = _label("", "StepSummary")
        self.lectura.body.addWidget(self.archivo)
        self.excel = QWidget()
        ex = QVBoxLayout(self.excel)
        ex.setContentsMargins(0, 0, 0, 0)
        ex.setSpacing(6)
        fila = QHBoxLayout()
        fila.addWidget(_label(S.PREP_SHEET, "FieldLabel", wrap=False))
        self.hoja = QComboBox()
        self.hoja.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.hoja.setMinimumContentsLength(8)
        self.hoja.activated.connect(self._opciones)
        fila.addWidget(self.hoja, 1)
        ex.addLayout(fila)
        fila = QHBoxLayout()
        fila.addWidget(_label(S.PREP_HEADER_ROW, "FieldLabel", wrap=False))
        self.fila_cab = QSpinBox()
        self.fila_cab.setRange(1, 200)
        self.fila_cab.setFixedWidth(72)
        self.fila_cab.editingFinished.connect(self._opciones)
        fila.addWidget(self.fila_cab)
        fila.addStretch(1)
        ex.addLayout(fila)
        self.dos_filas = QCheckBox(S.PREP_TWO_HEADER_ROWS)
        self.dos_filas.setToolTip(S.READ_TWO_HEADERS)
        self.dos_filas.clicked.connect(self._opciones)
        self.final = QCheckBox(S.PREP_DROP_TRAILING)
        self.final.clicked.connect(self._opciones)
        ex.addWidget(self.dos_filas)
        ex.addWidget(self.final)
        self.lectura.body.addWidget(self.excel)
        self.avisos = _label("", "Hint")
        self.lectura.body.addWidget(self.avisos)
        col.addWidget(self.lectura)

        self.calidad = Section(S.PREP_QUALITY)
        self.calidad_lista = QVBoxLayout()
        self.calidad_lista.setSpacing(6)
        self.calidad.body.addLayout(self.calidad_lista)
        col.addWidget(self.calidad)

        self.receta = Section(S.PREP_RECIPE)
        self.receta_lista = QVBoxLayout()
        self.receta_lista.setSpacing(4)
        self.receta.body.addLayout(self.receta_lista)
        botones = QHBoxLayout()
        self.add_button = QPushButton(S.PREP_ADD_STEP)
        self.add_button.setMenu(self._menu())
        self.myf_button = QPushButton(S.MYF_BUTTON)
        self.myf_button.clicked.connect(self.my_formulas_requested)
        botones.addWidget(self.add_button)
        botones.addWidget(self.myf_button)
        botones.addStretch(1)
        self.receta.body.addLayout(botones)
        col.addWidget(self.receta)

        self.dic = Section(S.DICT_TITLE)
        self.dic_resumen = _label("", "StepSummary")
        self.dic.body.addWidget(self.dic_resumen)
        self.dic_button = QPushButton(S.DICT_EDIT)
        self.dic_button.clicked.connect(self.dictionary_requested)
        fila = QHBoxLayout()
        fila.addWidget(self.dic_button)
        fila.addStretch(1)
        self.dic.body.addLayout(fila)
        col.addWidget(self.dic)

        col.addStretch(1)
        self.continuar = QPushButton(S.PREP_CONTINUE)
        self.continuar.setProperty("variant", "primary")
        self.continuar.clicked.connect(self.continue_requested)
        col.addWidget(self.continuar)
        self.setWidget(content)

        session.prep_changed.connect(self.refresh)
        session.dataset_changed.connect(self.refresh)
        session.roles_changed.connect(self._refresh_quality)  # el identificador cambia la revisión de ID
        self.refresh()

    def _menu(self) -> QMenu:
        menu = QMenu(self)
        for tipo in TIPOS_MENU:
            if tipo is None:
                menu.addSeparator()
                continue
            action = menu.addAction(S.PREP_STEP_TITLES[tipo])
            action.triggered.connect(lambda _=False, t=tipo: self.new_step(t))
        return menu

    # --- Refresco --------------------------------------------------------
    def refresh(self, *_args) -> None:
        prep = self.session.prep
        enabled = prep is not None
        for w in (self.lectura, self.calidad, self.receta, self.dic, self.continuar):
            w.setEnabled(enabled)
        if prep is None:
            self.archivo.setText(S.STEP_DATA_HINT)
            self.excel.hide()
            return
        lect = prep.leer()
        df = lect.df
        self.archivo.setText(S.PREP_FILE_SUMMARY.format(name=prep.nombre, rows=len(df), cols=df.shape[1]))
        es_excel = sio.es_excel(prep.nombre)
        self.excel.setVisible(es_excel)
        if es_excel:
            self.hoja.blockSignals(True)
            self.hoja.clear()
            self.hoja.addItems(lect.hojas)
            self.hoja.setCurrentText(prep.opciones.hoja or "")
            self.hoja.blockSignals(False)
            self.fila_cab.blockSignals(True)
            self.fila_cab.setValue(prep.opciones.fila_cabecera or 1)
            self.fila_cab.blockSignals(False)
            self.dos_filas.setChecked((prep.opciones.filas_cabecera or 1) == 2)
            self.final.setChecked(prep.opciones.quitar_final)
        self.avisos.setText("\n".join(lect.avisos))
        self.avisos.setVisible(bool(lect.avisos))
        self._refresh_quality()
        self._refresh_recipe()
        cols = self.session.dataset.columnas
        n = sum(1 for c in cols if prep.diccionario.get(c) and not prep.diccionario.get(c).vacia)
        self.dic_resumen.setText(S.DICT_SUMMARY.format(n=n, total=len(cols)))

    def _refresh_quality(self, *_args) -> None:
        prep, ds = self.session.prep, self.session.dataset
        _clear(self.calidad_lista)
        if prep is None or ds is None:
            return
        activas = ds.df.drop(index=list(ds.excluidas_receta))
        todos = q.revisar(activas, prep.diccionario, ds.identificador)
        problemas = [p for p in todos if clave(p) not in prep.ignorados]
        orden = {q.GRAVE: 0, q.AVISO: 1, q.INFO: 2}
        self.problemas = sorted(problemas, key=lambda p: orden[p.nivel])
        if not self.problemas:
            self.calidad_lista.addWidget(_label(S.PREP_QUALITY_OK, "StepResult"))
        for p in self.problemas:
            card = ProblemCard(p)
            card.fix_requested.connect(self.fix)
            card.show_requested.connect(self.session.select_rows)
            card.ignore_requested.connect(self.session.ignore_problem)
            self.calidad_lista.addWidget(card)
            card.show()
        graves = sum(p.nivel == q.GRAVE for p in self.problemas)
        formato = S.PREP_QUALITY_COUNT_1 if graves == 1 else S.PREP_QUALITY_COUNT
        self.calidad.counter.setText(formato.format(n=len(self.problemas), g=graves) if self.problemas else "")

    def _refresh_recipe(self) -> None:
        prep = self.session.prep
        _clear(self.receta_lista)
        informes = {i.id: i for i in (self.session.preparado.informes if self.session.preparado else [])}
        if not prep.receta.pasos:
            self.receta_lista.addWidget(_label(S.PREP_RECIPE_EMPTY, "Hint"))
        for n, paso in enumerate(prep.receta.pasos, start=1):
            row = RecipeRow(n, paso, informes.get(paso.id))
            row.toggled.connect(self.toggle)
            row.moved.connect(lambda pid, d: self._change(lambda p: p.receta.mover(pid, d)))
            row.edit_requested.connect(self.edit_step)
            row.delete_requested.connect(self.delete_step)
            self.receta_lista.addWidget(row)
            row.show()
        n = len(prep.receta.pasos)
        contador = S.PREP_RECIPE_COUNT_1 if n == 1 else S.PREP_RECIPE_COUNT.format(n=n)
        self.receta.counter.setText(contador if n else "")

    # --- Acciones ------------------------------------------------------
    def _change(self, cambio) -> bool:
        try:
            self.session.change_preparation(cambio)
        except ErrorUsuario as e:
            QMessageBox.warning(self, S.PREP_ERROR_TITLE, str(e))
            return False
        return True

    def _opciones(self, *_args) -> None:
        prev = self.session.prep.opciones
        hoja = self.hoja.currentText() or None
        if hoja != prev.hoja:  # otra hoja: se vuelve a detectar la cabecera
            nuevas = sio.OpcionesLectura(hoja=hoja, quitar_final=self.final.isChecked())
        else:
            nuevas = sio.OpcionesLectura(
                hoja=hoja,
                fila_cabecera=self.fila_cab.value(),
                filas_cabecera=2 if self.dos_filas.isChecked() else 1,
                quitar_final=self.final.isChecked(),
            )
        if nuevas != prev:
            self._change(lambda p: setattr(p, "opciones", nuevas))

    def open_dialog(self, tipo: str, params: dict | None = None, paso_id: str | None = None) -> PasoDialog:
        """Crea el diálogo (separado de exec() para poder probarlo)."""
        prep = self.session.prep
        return PasoDialog(tipo, prep.receta, prep.leidos, params, paso_id, self)

    def _exec(self, dialog: PasoDialog) -> bool:
        return dialog.exec() == PasoDialog.DialogCode.Accepted

    def new_step(self, tipo: str, params: dict | None = None) -> None:
        dialog = self.open_dialog(tipo, params)
        if self._exec(dialog):
            self.add_from_dialog(dialog)

    def add_from_dialog(self, dialog: PasoDialog) -> None:
        paso = dialog.paso()
        if dialog.paso_id is None:
            ok = self._change(lambda p: p.receta.añadir(paso))
        else:
            ok = self._change(lambda p: _sustituir(p, paso))
        if ok and dialog.guardar_en_mis_formulas:
            from statlab.ui.prep.my_formulas import guardar_en_biblioteca

            guardar_en_biblioteca(self, paso.params["destino"], paso.params["formula"])

    def fix(self, problema: q.Problema) -> None:
        self.new_step(problema.propuesta.tipo, problema.propuesta.params)

    def edit_step(self, paso_id: str) -> None:
        paso = self.session.prep.receta.paso(paso_id)
        dialog = self.open_dialog(paso.tipo, paso.params, paso_id)
        if self._exec(dialog):
            self.add_from_dialog(dialog)

    def toggle(self, paso_id: str, activo: bool) -> None:
        def cambio(prep):
            prep.receta.paso(paso_id).activo = activo

        self._change(cambio)

    def delete_step(self, paso_id: str) -> None:
        self._change(lambda p: p.receta.quitar(paso_id))


def _sustituir(prep, paso: Paso) -> None:
    prep.receta.pasos = [paso if p.id == paso.id else p for p in prep.receta.pasos]
