"""Barra lateral del modo «Preparar datos»: archivo, revisión de calidad, receta y diccionario.

Mismo lenguaje visual que la barra del análisis: tarjetas con título, una línea de
resumen y un enlace a la derecha. Los detalles (opciones de lectura, explicación
de cada aviso, acciones de cada paso) aparecen solo cuando se piden.
"""
from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
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
from statlab.ui.widgets.toggle import Toggle

# Orden del menú «Añadir paso»
TIPOS_MENU = ["calcular", "tipo", "perdidos", "recodificar", "categorizar", "unidades", "fechas", "seguimiento",
              None, "excluir", "duplicados", None, "renombrar", "quitar"]
MAX_PROBLEMAS = 5  # el resto, tras «Mostrar todos»


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


def _link(texto: str) -> QPushButton:
    b = QPushButton(texto)
    b.setObjectName("LinkButton")
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def _repolish(w: QWidget) -> None:
    w.style().unpolish(w)
    w.style().polish(w)


class ElidedLabel(QLabel):
    """Una sola línea con «…» si no cabe; el texto completo en el tooltip."""

    def __init__(self, texto: str = "", parent: QWidget | None = None):
        super().__init__(texto, parent)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setToolTip(texto)

    def setText(self, texto: str) -> None:
        super().setText(texto)
        self.setToolTip(texto)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        r = self.contentsRect()
        texto = self.fontMetrics().elidedText(self.text(), Qt.TextElideMode.ElideRight, r.width())
        p.setPen(self.palette().color(self.foregroundRole()))
        p.drawText(r, int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), texto)


class Card(QFrame):
    """Tarjeta de la barra: título, enlace a la derecha, resumen y cuerpo."""

    def __init__(self, titulo: str, enlace: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("StepCard")
        col = QVBoxLayout(self)
        col.setContentsMargins(14, 12, 14, 12)
        col.setSpacing(6)
        head = QHBoxLayout()
        head.setSpacing(8)
        self.title = _label(titulo, "StepTitle", wrap=False)
        head.addWidget(self.title, 1)
        self.counter = _label("", "Hint", wrap=False)
        head.addWidget(self.counter)
        self.link = _link(enlace)
        self.link.setVisible(bool(enlace))
        head.addWidget(self.link)
        col.addLayout(head)
        self.summary = _label("", "StepSummary")
        col.addWidget(self.summary)
        self.body = QVBoxLayout()
        self.body.setSpacing(0)
        col.addLayout(self.body)


class ProblemRow(QFrame):
    """Un aviso: punto de color, «columna · problema» y «Corregir». Al pulsar la fila
    se despliega la explicación con «Ver filas» e «Ignorar»."""

    fix_requested = Signal(object)
    show_requested = Signal(list)
    ignore_requested = Signal(str)

    def __init__(self, p: q.Problema, parent: QWidget | None = None):
        super().__init__(parent)
        self.problema = p
        self.setObjectName("ListRow")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        col = QVBoxLayout(self)
        col.setContentsMargins(2, 7, 2, 7)
        col.setSpacing(4)
        row = QHBoxLayout()
        row.setSpacing(8)
        dot = QLabel()
        dot.setObjectName("SeverityDot")
        dot.setProperty("level", p.nivel)
        dot.setFixedSize(8, 8)
        row.addWidget(dot, 0, Qt.AlignmentFlag.AlignVCenter)
        corto = S.Q_SHORT.get(p.codigo, p.titulo)
        texto = f"<b>{p.columna}</b> · {corto}" if p.columna else f"<b>{corto}</b>"
        self.text = _label(texto, "RowText")
        self.text.setTextFormat(Qt.TextFormat.RichText)
        row.addWidget(self.text, 1)
        if p.propuesta is not None:
            fix = _link(S.PREP_FIX)
            fix.clicked.connect(lambda: self.fix_requested.emit(p))
            row.addWidget(fix, 0, Qt.AlignmentFlag.AlignVCenter)
        col.addLayout(row)

        self.detail = QWidget()
        d = QVBoxLayout(self.detail)
        d.setContentsMargins(16, 0, 0, 2)
        d.setSpacing(4)
        d.addWidget(_label(p.detalle, "Hint"))
        links = QHBoxLayout()
        links.setSpacing(14)
        if p.filas:
            ver = _link(S.PREP_SHOW_ROWS.format(n=len(p.filas)))
            ver.clicked.connect(lambda: self.show_requested.emit(list(p.filas)))
            links.addWidget(ver)
        ignorar = _link(S.PREP_IGNORE)
        ignorar.clicked.connect(lambda: self.ignore_requested.emit(clave(p)))
        links.addWidget(ignorar)
        links.addStretch(1)
        d.addLayout(links)
        self.detail.hide()
        col.addWidget(self.detail)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.detail.setVisible(not self.detail.isVisible())
        super().mousePressEvent(event)


def clave(p: q.Problema) -> str:
    return f"{p.codigo}:{p.columna or ''}"


class RecipeRow(QFrame):
    """Un paso de la receta: número, descripción en una línea, estado y menú «⋯»."""

    toggled = Signal(str, bool)
    moved = Signal(str, int)
    edit_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, n: int, total: int, paso: Paso, informe, parent: QWidget | None = None):
        super().__init__(parent)
        self.paso = paso
        self.setObjectName("ListRow")
        error = informe is not None and not informe.ok and paso.activo
        self.setProperty("state", "off" if not paso.activo else ("error" if error else "ok"))
        row = QHBoxLayout(self)
        row.setContentsMargins(2, 6, 0, 6)
        row.setSpacing(8)
        num = _label(str(n), "RowNumber", wrap=False)
        num.setFixedWidth(16)
        num.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        row.addWidget(num, 0, Qt.AlignmentFlag.AlignTop)
        textos = QVBoxLayout()
        textos.setSpacing(1)
        self.text = ElidedLabel(paso.descripcion)
        self.text.setObjectName("RowText")
        textos.addWidget(self.text)
        estado = resumen_informe(informe) if paso.activo else S.PREP_STEP_OFF
        self.status = ElidedLabel(estado.replace("\n", " · "))
        self.status.setObjectName("RowError" if error else "RowStatus")
        self.status.setVisible(bool(estado))
        textos.addWidget(self.status)
        row.addLayout(textos, 1)

        self.more = QToolButton()
        self.more.setObjectName("RowMenu")
        self.more.setText("⋯")
        self.more.setToolTip(S.PREP_STEP_ACTIONS)
        self.more.setCursor(Qt.CursorShape.PointingHandCursor)
        self.more.clicked.connect(lambda: self._open_menu(n, total))
        row.addWidget(self.more, 0, Qt.AlignmentFlag.AlignTop)
        for w in (self, self.text, self.status, num):
            _repolish(w)

    def _open_menu(self, n: int, total: int) -> None:
        self.menu(n, total).exec(self.more.mapToGlobal(QPoint(0, self.more.height())))

    def menu(self, n: int, total: int) -> QMenu:
        m = QMenu(self)
        pid = self.paso.id
        m.addAction(S.PREP_EDIT, lambda: self.edit_requested.emit(pid))
        activo = self.paso.activo
        m.addAction(S.PREP_DISABLE if activo else S.PREP_ENABLE, lambda: self.toggled.emit(pid, not activo))
        m.addSeparator()
        subir = m.addAction(S.PREP_MOVE_UP, lambda: self.moved.emit(pid, -1))
        bajar = m.addAction(S.PREP_MOVE_DOWN, lambda: self.moved.emit(pid, +1))
        subir.setEnabled(n > 1)
        bajar.setEnabled(n < total)
        m.addSeparator()
        m.addAction(S.PREP_DELETE, lambda: self.delete_requested.emit(pid))
        return m

    def mouseDoubleClickEvent(self, event) -> None:
        self.edit_requested.emit(self.paso.id)
        super().mouseDoubleClickEvent(event)


def celdas_txt(n: int) -> str:
    return S.PREP_PREVIEW_CELLS_1 if n == 1 else S.PREP_PREVIEW_CELLS.format(n=n)


def filas_txt(n: int) -> str:
    return S.PREP_PREVIEW_ROWS_1 if n == 1 else S.PREP_PREVIEW_ROWS.format(n=n)


def resumen_informe(inf) -> str:
    if inf is None:
        return ""
    if not inf.ok:
        return inf.mensaje
    partes = []
    if inf.celdas:
        partes.append(celdas_txt(inf.celdas))
    if inf.filas:
        partes.append(filas_txt(inf.filas))
    if inf.columnas_nuevas:
        partes.append(S.PREP_PREVIEW_NEWCOLS.format(cols=", ".join(f"«{c}»" for c in inf.columnas_nuevas)))
    if inf.mensaje:
        partes.append(inf.mensaje)
    return " · ".join(partes)


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
        self.todos = False  # mostrar todos los avisos

        content = QWidget()
        content.setObjectName("SidebarContent")
        col = QVBoxLayout(content)
        col.setContentsMargins(16, 16, 16, 16)
        col.setSpacing(10)
        title = _label(S.PREP_SIDEBAR_TITLE.upper(), "SidebarTitle", wrap=False)
        font = title.font()
        font.setLetterSpacing(font.SpacingType.PercentageSpacing, 106)
        title.setFont(font)
        col.addWidget(title)

        # Archivo
        self.lectura = Card(S.PREP_FILE, S.PREP_ADJUST)
        self.lectura.link.clicked.connect(self._toggle_options)
        self.opciones = QWidget()
        op = QVBoxLayout(self.opciones)
        op.setContentsMargins(0, 6, 0, 0)
        op.setSpacing(8)
        self.excel = QWidget()
        ex = QVBoxLayout(self.excel)
        ex.setContentsMargins(0, 0, 0, 0)
        ex.setSpacing(8)
        ex.addWidget(_label(S.PREP_SHEET, "FieldLabel", wrap=False))
        self.hoja = QComboBox()
        self.hoja.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.hoja.setMinimumContentsLength(8)
        self.hoja.activated.connect(self._opciones)
        ex.addWidget(self.hoja)
        fila = QHBoxLayout()
        fila.addWidget(_label(S.PREP_HEADER_ROW, "FieldLabel", wrap=False), 1)
        self.fila_cab = QSpinBox()
        self.fila_cab.setRange(1, 200)
        self.fila_cab.setFixedWidth(76)
        self.fila_cab.editingFinished.connect(self._opciones)
        fila.addWidget(self.fila_cab)
        ex.addLayout(fila)
        self.dos_filas = Toggle(S.PREP_TWO_HEADER_ROWS)
        self.dos_filas.setToolTip(S.READ_TWO_HEADERS)
        self.dos_filas.clicked.connect(self._opciones)
        self.final = Toggle(S.PREP_DROP_TRAILING)
        self.final.clicked.connect(self._opciones)
        ex.addWidget(self.dos_filas)
        ex.addWidget(self.final)
        op.addWidget(self.excel)
        self.avisos = _label("", "Hint")
        op.addWidget(self.avisos)
        op.addWidget(_label(S.PREP_ORIGINAL_SAFE, "Hint"))
        self.opciones.hide()
        self.lectura.body.addWidget(self.opciones)
        col.addWidget(self.lectura)

        # Revisión de calidad
        self.calidad = Card(S.PREP_QUALITY)
        self.calidad_lista = QVBoxLayout()
        self.calidad_lista.setSpacing(0)
        self.calidad.body.addLayout(self.calidad_lista)
        self.mas = _link("")
        self.mas.clicked.connect(self._mostrar_todos)
        fila = QHBoxLayout()
        fila.setContentsMargins(0, 6, 0, 0)
        fila.addWidget(self.mas)
        fila.addStretch(1)
        self.calidad.body.addLayout(fila)
        col.addWidget(self.calidad)

        # Receta
        self.receta = Card(S.PREP_RECIPE, S.PREP_ADD_STEP)
        self.add_menu = self._menu()
        self.receta.link.clicked.connect(
            lambda: self.add_menu.exec(self.receta.link.mapToGlobal(QPoint(0, self.receta.link.height()))))
        self.add_button = self.receta.link
        self.receta_lista = QVBoxLayout()
        self.receta_lista.setSpacing(0)
        self.receta.body.addLayout(self.receta_lista)
        col.addWidget(self.receta)

        # Diccionario
        self.dic = Card(S.DICT_TITLE, S.EDIT)
        self.dic.link.clicked.connect(self.dictionary_requested)
        self.dic_resumen = self.dic.summary
        self.dic_button = self.dic.link
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
        menu.addSeparator()
        menu.addAction(S.MYF_MENU, self.my_formulas_requested.emit)
        return menu

    def _toggle_options(self) -> None:
        visible = not self.opciones.isVisible()
        self.opciones.setVisible(visible)
        self.lectura.link.setText(S.PREP_ADJUST_HIDE if visible else S.PREP_ADJUST)

    # --- Refresco --------------------------------------------------------
    def refresh(self, *_args) -> None:
        prep = self.session.prep
        enabled = prep is not None
        for w in (self.lectura, self.calidad, self.receta, self.dic, self.continuar):
            w.setEnabled(enabled)
        if prep is None:
            self.lectura.summary.setText(S.STEP_DATA_HINT)
            return
        lect = prep.leer()
        df = lect.df
        es_excel = sio.es_excel(prep.nombre)
        lineas = [S.PREP_FILE_SUMMARY.format(name=prep.nombre, rows=len(df), cols=df.shape[1])]
        if es_excel:
            lineas.append(S.PREP_FILE_SHEET.format(sheet=prep.opciones.hoja, row=prep.opciones.fila_cabecera))
        self.lectura.summary.setText("\n".join(lineas))
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
        self.avisos.setText("\n".join(f"· {a}" for a in lect.avisos))
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
            self.calidad.summary.setText(S.PREP_QUALITY_OK)
            self.calidad.summary.setObjectName("OkNote")
        else:
            graves = sum(p.nivel == q.GRAVE for p in self.problemas)
            formato = S.PREP_QUALITY_SUMMARY_1 if len(self.problemas) == 1 else S.PREP_QUALITY_SUMMARY
            texto = formato.format(n=len(self.problemas))
            if graves:
                texto += " · " + (S.PREP_QUALITY_GRAVES_1 if graves == 1 else S.PREP_QUALITY_GRAVES.format(n=graves))
            self.calidad.summary.setText(texto)
            self.calidad.summary.setObjectName("StepSummary")
        _repolish(self.calidad.summary)
        visibles = self.problemas if self.todos else self.problemas[:MAX_PROBLEMAS]
        for p in visibles:
            row = ProblemRow(p)
            row.fix_requested.connect(self.fix)
            row.show_requested.connect(self.session.select_rows)
            row.ignore_requested.connect(self.session.ignore_problem)
            self.calidad_lista.addWidget(row)
            row.show()
        ocultos = len(self.problemas) - len(visibles)
        self.mas.setText(S.PREP_SHOW_ALL.format(n=ocultos))
        self.mas.setVisible(ocultos > 0)

    def _mostrar_todos(self) -> None:
        self.todos = True
        self._refresh_quality()

    def _refresh_recipe(self) -> None:
        prep = self.session.prep
        _clear(self.receta_lista)
        informes = {i.id: i for i in (self.session.preparado.informes if self.session.preparado else [])}
        pasos = prep.receta.pasos
        self.receta.summary.setText(S.PREP_RECIPE_EMPTY)
        self.receta.summary.setVisible(not pasos)
        for n, paso in enumerate(pasos, start=1):
            row = RecipeRow(n, len(pasos), paso, informes.get(paso.id))
            row.toggled.connect(self.toggle)
            row.moved.connect(lambda pid, d: self._change(lambda p: p.receta.mover(pid, d)))
            row.edit_requested.connect(self.edit_step)
            row.delete_requested.connect(self.delete_step)
            self.receta_lista.addWidget(row)
            row.show()
        errores = sum(1 for p in pasos if p.activo and p.id in informes and not informes[p.id].ok)
        self.receta.counter.setText(S.PREP_RECIPE_ERRORS.format(n=errores) if errores else "")
        self.receta.counter.setObjectName("RowError" if errores else "Hint")
        _repolish(self.receta.counter)

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
