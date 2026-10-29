"""Diálogo para crear o editar un paso de la receta, con vista previa.

Cada tipo de paso se describe con una lista de campos; el diálogo construye el
formulario y, con cada cambio, aplica la receta con el paso candidato para
mostrar qué cambiaría (celdas, filas excluidas, columnas nuevas y un antes/después).
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

import pandas as pd
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from statlab import strings_es as S
from statlab.core import fmt
from statlab.core.errors import ErrorUsuario
from statlab.core.prep import formula
from statlab.core.prep import receta as rc
from statlab.core.prep.receta import Paso, Receta
from statlab.ui.widgets.toggle import Toggle

PREVIEW_ROWS = 8


@dataclass
class Campo:
    clave: str
    etiqueta: str
    tipo: str  # columna, columnas, texto, formula, opcion, numero, entero, valores, recodificar, casilla
    opciones: tuple = ()  # (valor, texto) para «opcion»
    filtro: str = ""  # «fecha» o «numerica» para columnas
    ayuda: str = ""
    si: tuple | None = None  # (clave, valores) → solo visible si otro campo vale eso
    opcional: bool = False


def _tipos():
    return tuple((t, S.PREP_TYPE_NAMES[t]) for t in rc.TIPOS)


def _formatos():
    return tuple(S.PREP_DATE_FORMATS.items())


_UNIDADES = (("anos", S.UNIT_YEARS), ("meses", S.UNIT_MONTHS), ("dias", S.UNIT_DAYS))

FORMULARIOS: dict[str, list[Campo]] = {
    "tipo": [
        Campo("columna", S.F_COLUMN, "columna"),
        Campo("tipo", S.F_TYPE, "opcion", _tipos()),
        Campo("formato", S.F_DATE_FORMAT, "opcion", _formatos(), si=("tipo", ("fecha",))),
        Campo("limites", S.F_LIMITS, "opcion", (("valor", S.F_LIMITS_VALUE), ("na", S.F_LIMITS_NA)),
              si=("tipo", ("numerica",))),
        Campo("orden", S.F_ORDER, "valores", si=("tipo", ("ordinal",)), ayuda=S.F_ORDER_HELP),
    ],
    "perdidos": [
        Campo("columnas", S.F_COLUMNS, "columnas"),
        Campo("valores", S.F_MISSING_VALUES, "valores", ayuda=S.F_MISSING_HELP, opcional=True),
        Campo("condicion", S.F_CONDITION_OPTIONAL, "formula", opcional=True, ayuda=S.F_CONDITION_HELP),
    ],
    "recodificar": [
        Campo("columna", S.F_COLUMN, "columna"),
        Campo("mapa", S.F_RECODE, "recodificar", ayuda=S.F_RECODE_HELP),
        Campo("destino", S.F_TARGET_OPTIONAL, "texto", opcional=True),
    ],
    "unidades": [
        Campo("columna", S.F_COLUMN, "columna", filtro="numerica"),
        Campo("factor", S.F_FACTOR, "numero", ayuda=S.F_FACTOR_HELP),
        Campo("condicion", S.F_CONDITION_OPTIONAL, "formula", opcional=True, ayuda=S.F_UNITS_CONDITION_HELP),
    ],
    "categorizar": [
        Campo("columna", S.F_COLUMN, "columna", filtro="numerica"),
        Campo("modo", S.F_CUT_MODE, "opcion", (("cortes", S.F_CUT_POINTS), ("cuantiles", S.F_CUT_QUANTILES))),
        Campo("cortes", S.F_CUTS, "valores", si=("modo", ("cortes",)), ayuda=S.F_CUTS_HELP),
        Campo("cuantiles", S.F_QUANTILES, "entero", si=("modo", ("cuantiles",))),
        Campo("etiquetas", S.F_LABELS_OPTIONAL, "valores", opcional=True),
        Campo("destino", S.F_TARGET_OPTIONAL, "texto", opcional=True),
    ],
    "calcular": [
        Campo("destino", S.F_TARGET, "texto"),
        Campo("formula", S.F_FORMULA, "formula", ayuda=S.F_FORMULA_HELP),
        Campo("guardar", S.F_SAVE_MYF, "casilla", opcional=True),
    ],
    "fechas": [
        Campo("destino", S.F_TARGET, "texto"),
        Campo("inicio", S.F_DATE_START, "columna", filtro="fecha"),
        Campo("fin", S.F_DATE_END, "columna", filtro="fecha"),
        Campo("unidad", S.F_UNIT, "opcion", _UNIDADES),
    ],
    "seguimiento": [
        Campo("inicio", S.F_FU_START, "columna", filtro="fecha"),
        Campo("evento", S.F_FU_EVENT, "columna", filtro="fecha"),
        Campo("ultimo_contacto", S.F_FU_LAST, "columna", filtro="fecha"),
        Campo("unidad", S.F_UNIT, "opcion", _UNIDADES),
        Campo("destino_tiempo", S.F_FU_TIME_NAME, "texto"),
        Campo("destino_evento", S.F_FU_EVENT_NAME, "texto"),
    ],
    "excluir": [
        Campo("condicion", S.F_EXCLUDE_IF, "formula", ayuda=S.F_EXCLUDE_HELP),
        Campo("motivo", S.F_REASON, "texto", ayuda=S.F_REASON_HELP),
    ],
    "duplicados": [
        Campo("columnas", S.F_DUP_COLUMNS, "columnas", opcional=True, ayuda=S.F_DUP_HELP),
        Campo("motivo", S.F_REASON, "texto", opcional=True),
    ],
    "renombrar": [
        Campo("columna", S.F_COLUMN, "columna"),
        Campo("nombre", S.F_NEW_NAME, "texto"),
    ],
    "quitar": [Campo("columnas", S.F_COLUMNS, "columnas")],
}

DEFECTOS: dict[str, dict[str, Any]] = {
    "tipo": {"tipo": "numerica", "formato": "dma", "limites": "valor"},
    "categorizar": {"modo": "cortes", "cuantiles": 4},
    "fechas": {"unidad": "anos"},
    "seguimiento": {"unidad": "meses", "destino_tiempo": "tiempo", "destino_evento": "evento"},
    "unidades": {"factor": 0.1},
}


def _num_txt(v: Any) -> str:
    return str(v).replace(".", ",")


def _valores_txt(vals) -> str:
    return "; ".join(_num_txt(v) for v in vals or [])


def _valores(texto: str, numeros: bool = False) -> list:
    partes = [p.strip() for p in texto.split(";") if p.strip()]
    if not numeros:
        return partes
    try:
        return [float(p.replace(",", ".")) for p in partes]
    except ValueError as e:
        raise ErrorUsuario(S.F_BAD_NUMBERS) from e


class RecodeTable(QTableWidget):
    """Valores actuales de una columna → valor nuevo (vacío = perdido)."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(0, 3, parent)
        self.setHorizontalHeaderLabels([S.F_RECODE_OLD, S.F_RECODE_N, S.F_RECODE_NEW])
        self.verticalHeader().hide()
        h = self.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.setMinimumHeight(180)

    def cargar(self, serie: pd.Series | None, mapa: dict[str, Any]) -> None:
        self.blockSignals(True)
        self.setRowCount(0)
        if serie is not None:
            cuenta = serie.astype("string").str.strip().value_counts(dropna=True)
            for i, (valor, n) in enumerate(cuenta.items()):
                self.insertRow(i)
                viejo = QTableWidgetItem(str(valor))
                viejo.setFlags(viejo.flags() & ~Qt.ItemFlag.ItemIsEditable)
                cnt = QTableWidgetItem(str(n))
                cnt.setFlags(cnt.flags() & ~Qt.ItemFlag.ItemIsEditable)
                nuevo = mapa.get(str(valor), str(valor))
                self.setItem(i, 0, viejo)
                self.setItem(i, 1, cnt)
                self.setItem(i, 2, QTableWidgetItem("" if nuevo is None else str(nuevo)))
        self.blockSignals(False)

    def mapa(self) -> dict[str, Any]:
        out = {}
        for i in range(self.rowCount()):
            viejo = self.item(i, 0).text()
            nuevo = self.item(i, 2).text().strip()
            if nuevo != viejo:
                out[viejo] = nuevo or None
        return out


class FormulaField(QWidget):
    """Editor de fórmula con listas para insertar columnas y funciones."""

    def __init__(self, columnas: list[str], parent: QWidget | None = None):
        super().__init__(parent)
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        self.edit = QPlainTextEdit()
        self.edit.setObjectName("FormulaEdit")
        self.edit.setFixedHeight(64)
        col.addWidget(self.edit)
        row = QHBoxLayout()
        self.cols = QComboBox()
        self.cols.addItem(S.F_INSERT_COLUMN)
        self.cols.addItems(columnas)
        self.funcs = QComboBox()
        self.funcs.addItem(S.F_INSERT_FUNCTION)
        self.funcs.addItems(formula.NOMBRES_FUNCIONES)
        self.cols.activated.connect(self._insert_col)
        self.funcs.activated.connect(self._insert_func)
        row.addWidget(self.cols, 1)
        row.addWidget(self.funcs, 1)
        col.addLayout(row)

    def _insert_col(self, i: int) -> None:
        if i > 0:
            nombre = self.cols.itemText(i)
            simple = nombre.isidentifier() and formula._clave(nombre) not in formula.FUNCIONES
            self.edit.insertPlainText(nombre if simple else f"[{nombre}]")
            self.cols.setCurrentIndex(0)
            self.edit.setFocus()

    def _insert_func(self, i: int) -> None:
        if i > 0:
            self.edit.insertPlainText(f"{self.funcs.itemText(i)}(")
            self.funcs.setCurrentIndex(0)
            self.edit.setFocus()

    def text(self) -> str:
        return self.edit.toPlainText().strip()

    def setText(self, t: str) -> None:
        self.edit.setPlainText(t)


class PasoDialog(QDialog):
    """Crea (paso_id=None) o edita un paso. `datos` es la tabla de entrada (leída)."""

    def __init__(self, tipo: str, receta: Receta, datos: pd.DataFrame, params: dict | None = None,
                 paso_id: str | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.tipo = tipo
        self.receta = receta
        self.datos = datos
        self.paso_id = paso_id
        self.setWindowTitle(S.PREP_STEP_TITLES[tipo])
        self.setMinimumWidth(620)
        self.params: dict[str, Any] = {**DEFECTOS.get(tipo, {}), **copy.deepcopy(params or {})}
        if tipo == "categorizar" and params and params.get("cuantiles") and "modo" not in params:
            self.params["modo"] = "cuantiles"
        # Columnas disponibles: las que hay justo antes de este paso
        self.entrada = rc.aplicar(datos, self._receta_hasta()).df
        self.widgets: dict[str, QWidget] = {}
        self.filas_form: dict[str, tuple[QLabel, QWidget]] = {}

        col = QVBoxLayout(self)
        intro = QLabel(S.PREP_STEP_INTROS[tipo])
        intro.setWordWrap(True)
        intro.setObjectName("Hint")
        col.addWidget(intro)
        self.form = QFormLayout()
        self.form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        for campo in FORMULARIOS[tipo]:
            w = self._crear(campo)
            self.widgets[campo.clave] = w
            label = QLabel("" if campo.tipo == "casilla" else campo.etiqueta)
            label.setObjectName("FieldLabel")
            contenedor = w
            if campo.ayuda:
                contenedor = QWidget()
                c = QVBoxLayout(contenedor)
                c.setContentsMargins(0, 0, 0, 0)
                c.setSpacing(2)
                c.addWidget(w)
                ayuda = QLabel(campo.ayuda)
                ayuda.setObjectName("Hint")
                ayuda.setWordWrap(True)
                c.addWidget(ayuda)
            self.form.addRow(label, contenedor)
            self.filas_form[campo.clave] = (label, contenedor)
        col.addLayout(self.form)

        titulo = QLabel(S.PREP_PREVIEW)
        titulo.setObjectName("SectionTitle")
        col.addWidget(titulo)
        self.resumen = QLabel()
        self.resumen.setWordWrap(True)
        col.addWidget(self.resumen)
        self.tabla = QTableWidget(0, 0)
        self.tabla.setObjectName("IndexTable")
        self.tabla.verticalHeader().hide()
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setMinimumHeight(150)
        col.addWidget(self.tabla, 1)

        self.botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.botones.button(QDialogButtonBox.StandardButton.Ok).setText(S.PREP_ADD if paso_id is None else S.PREP_SAVE)
        self.botones.button(QDialogButtonBox.StandardButton.Cancel).setText(S.UNSAVED_CANCEL)
        self.botones.accepted.connect(self._aceptar)
        self.botones.rejected.connect(self.reject)
        col.addWidget(self.botones)

        self._timer = QTimer(self, singleShot=True, interval=250)
        self._timer.timeout.connect(self.actualizar)
        self._visibilidad()
        self.actualizar()

    # --- Construcción -------------------------------------------------
    def _receta_hasta(self) -> Receta:
        """Pasos anteriores al que se edita (o todos, si es nuevo)."""
        if self.paso_id is None:
            return Receta(list(self.receta.pasos))
        i = next(i for i, p in enumerate(self.receta.pasos) if p.id == self.paso_id)
        return Receta(self.receta.pasos[:i])

    def _columnas(self, filtro: str) -> list[str]:
        df = self.entrada
        if filtro == "fecha":
            return [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
        if filtro == "numerica":
            return [c for c in df.columns if rc.is_numeric_col(df[c])]
        return list(df.columns)

    def _crear(self, campo: Campo) -> QWidget:
        v = self.params.get(campo.clave)
        if campo.tipo == "columna":
            w = QComboBox()
            cols = self._columnas(campo.filtro)
            if campo.filtro == "fecha" and not cols:
                w.addItem(S.F_NO_DATE_COLUMNS)
                w.setEnabled(False)
            w.addItems(cols)
            if v in cols:
                w.setCurrentText(v)
            w.currentTextChanged.connect(self._cambio)
            if campo.clave == "columna" and self.tipo == "recodificar":
                w.currentTextChanged.connect(lambda _t: self._recargar_recode())
            return w
        if campo.tipo == "columnas":
            w = QListWidget()
            w.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
            w.setMaximumHeight(140)
            for c in self._columnas(campo.filtro):
                item = QListWidgetItem(c)
                w.addItem(item)
                item.setSelected(c in (v or []))
            w.itemSelectionChanged.connect(self._cambio)
            return w
        if campo.tipo == "opcion":
            w = QComboBox()
            for valor, texto in campo.opciones:
                w.addItem(texto, valor)
            i = w.findData(v)
            w.setCurrentIndex(max(i, 0))
            w.currentIndexChanged.connect(self._cambio)
            w.currentIndexChanged.connect(lambda _i: self._visibilidad())
            return w
        if campo.tipo == "formula":
            w = FormulaField(list(self.entrada.columns))
            w.setText(v or "")
            w.edit.textChanged.connect(self._cambio)
            return w
        if campo.tipo == "recodificar":
            w = RecodeTable()
            w.itemChanged.connect(self._cambio)
            self._recode = w
            QTimer.singleShot(0, self._recargar_recode)
            return w
        if campo.tipo == "entero":
            w = QSpinBox()
            w.setRange(2, 20)
            w.setValue(int(v or 4))
            w.valueChanged.connect(self._cambio)
            return w
        if campo.tipo == "casilla":
            w = Toggle(campo.etiqueta)
            w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            w.setChecked(bool(v))
            return w
        w = QLineEdit()
        if campo.tipo == "numero":
            w.setText("" if v is None else _num_txt(v))
        elif campo.tipo == "valores":
            w.setText(_valores_txt(v))
        else:
            w.setText("" if v is None else str(v))
        w.textChanged.connect(self._cambio)
        return w

    def _recargar_recode(self) -> None:
        col = self.widgets["columna"].currentText()
        serie = self.entrada[col] if col in self.entrada.columns else None
        mapa = self.params.get("mapa", {}) if self.params.get("columna") in (None, col) else {}
        self._recode.cargar(serie, mapa)
        self._cambio()

    def _visibilidad(self) -> None:
        for campo in FORMULARIOS[self.tipo]:
            if campo.si is None:
                continue
            otro = self.widgets[campo.si[0]]
            visible = otro.currentData() in campo.si[1]
            for w in self.filas_form[campo.clave]:
                w.setVisible(visible)

    # --- Lectura del formulario ----------------------------------------
    def leer(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for campo in FORMULARIOS[self.tipo]:
            if campo.si is not None and self.widgets[campo.si[0]].currentData() not in campo.si[1]:
                continue
            w = self.widgets[campo.clave]
            if campo.tipo == "columna":
                v = w.currentText() if w.isEnabled() else ""
            elif campo.tipo == "columnas":
                v = [i.text() for i in w.selectedItems()]
            elif campo.tipo == "opcion":
                v = w.currentData()
            elif campo.tipo == "formula":
                v = w.text()
            elif campo.tipo == "recodificar":
                v = w.mapa()
            elif campo.tipo == "entero":
                v = w.value()
            elif campo.tipo == "casilla":
                v = w.isChecked()
            elif campo.tipo == "numero":
                t = w.text().strip().replace(",", ".")
                try:
                    v = float(t)
                except ValueError as e:
                    raise ErrorUsuario(S.F_BAD_NUMBER.format(field=campo.etiqueta)) from e
            elif campo.tipo == "valores":
                v = _valores(w.text(), numeros=campo.clave == "cortes")
            else:
                v = w.text().strip()
            if not campo.opcional and v in ("", [], None) and campo.tipo != "casilla":
                raise ErrorUsuario(S.F_REQUIRED.format(field=campo.etiqueta))
            if v not in ("", [], None, {}):
                out[campo.clave] = v
        if self.tipo == "categorizar":
            if out.pop("modo", "cortes") == "cuantiles":
                out.pop("cortes", None)
            else:
                out.pop("cuantiles", None)
        if self.tipo == "perdidos" and not out.get("valores") and not out.get("condicion"):
            raise ErrorUsuario(S.F_MISSING_NOTHING)
        if self.tipo == "recodificar" and not out.get("mapa"):
            raise ErrorUsuario(S.F_RECODE_NOTHING)
        return out

    def paso(self) -> Paso:
        params = self.leer()
        params.pop("guardar", None)
        p = Paso(self.tipo, params)
        if self.paso_id is not None:
            p.id = self.paso_id
        rc.validar(p)
        return p

    @property
    def guardar_en_mis_formulas(self) -> bool:
        w = self.widgets.get("guardar")
        return isinstance(w, Toggle) and w.isChecked()

    # --- Vista previa ----------------------------------------------------
    def _cambio(self, *_args) -> None:
        self._timer.start()

    def actualizar(self) -> None:
        ok = self.botones.button(QDialogButtonBox.StandardButton.Ok)
        try:
            paso = self.paso()
        except ErrorUsuario as e:
            self._mostrar_error(str(e))
            ok.setEnabled(False)
            return
        # Hasta este paso incluido: el «antes» es la tabla justo antes de él
        out = rc.aplicar(self.datos, Receta([*self._receta_hasta().pasos, paso]))
        inf = out.informes[-1]
        if not inf.ok:
            self._mostrar_error(inf.mensaje)
            ok.setEnabled(False)
            return
        ok.setEnabled(True)
        partes = []
        if inf.celdas:
            partes.append(S.PREP_PREVIEW_CELLS_1 if inf.celdas == 1 else S.PREP_PREVIEW_CELLS.format(n=inf.celdas))
        if inf.filas:
            partes.append(S.PREP_PREVIEW_ROWS_1 if inf.filas == 1 else S.PREP_PREVIEW_ROWS.format(n=inf.filas))
        if inf.columnas_nuevas:
            partes.append(S.PREP_PREVIEW_NEWCOLS.format(cols=", ".join(f"«{c}»" for c in inf.columnas_nuevas)))
        if not partes:
            partes.append(S.PREP_PREVIEW_NOTHING)
        texto = " · ".join(partes)
        if inf.mensaje:
            texto += f"\n{inf.mensaje}"
        self.resumen.setObjectName("StepResult" if not inf.mensaje else "WarningNote")
        self.resumen.setStyleSheet("")
        self.resumen.setText(texto)
        self._tabla_antes_despues(paso, out)

    def _mostrar_error(self, texto: str) -> None:
        self.resumen.setObjectName("ValidationNote")
        self.resumen.setStyleSheet("")
        self.resumen.setText(texto)
        self.tabla.setRowCount(0)
        self.tabla.setColumnCount(0)

    def _tabla_antes_despues(self, paso: Paso, out: rc.Preparado) -> None:
        """Hasta 8 filas afectadas: valor antes y después (o motivo de exclusión)."""
        antes, despues = self.entrada, out.df
        p = paso.params
        if paso.tipo in ("excluir", "duplicados"):
            filas = [f for f, m in out.excluidas.items() if m == (p.get("motivo") or S.PREP_DUPLICATE_REASON)]
            cols = (formula.columnas(formula.analizar(p["condicion"])) if p.get("condicion")
                    else list(p.get("columnas") or []))
            cols = [c for c in cols if c in despues.columns][:4] or list(despues.columns[:4])
            self._llenar(sorted(filas)[:PREVIEW_ROWS], [(c, despues[c]) for c in cols], S.PREP_EXCLUDED)
            return
        if paso.tipo in ("quitar", "renombrar"):
            self.tabla.setRowCount(0)
            self.tabla.setColumnCount(0)
            return
        destinos = [c for c in despues.columns if c not in antes.columns] or [p.get("columna")]
        destinos += [c for c in p.get("columnas", []) if c not in destinos]
        destinos = [c for c in destinos if c in despues.columns]
        origen = p.get("columna")
        series = []
        if origen and origen in antes.columns:
            series.append((f"{origen} ({S.PREP_BEFORE})", antes[origen]))
        for c in destinos:
            etiqueta = f"{c} ({S.PREP_AFTER})" if c in antes.columns else c
            series.append((etiqueta, despues[c]))
        filas = self._filas_afectadas(antes, despues, destinos)
        self._llenar(filas, series, None)

    def _filas_afectadas(self, antes, despues, cols) -> list[int]:
        cambiadas = pd.Series(False, index=despues.index)
        for c in cols:
            if c in antes.columns:
                a, d = antes[c].astype("string"), despues[c].astype("string")
                cambiadas |= ((a != d).fillna(True) & ~(a.isna() & d.isna()))
            else:
                cambiadas |= despues[c].notna()
        filas = list(cambiadas[cambiadas].index[:PREVIEW_ROWS])
        return filas or list(despues.index[:PREVIEW_ROWS])

    def _llenar(self, filas: list[int], series: list[tuple[str, pd.Series]], marca: str | None) -> None:
        cabecera = [S.PREP_ROW] + [n for n, _ in series] + ([S.PREP_STATUS] if marca else [])
        self.tabla.setColumnCount(len(cabecera))
        self.tabla.setHorizontalHeaderLabels(cabecera)
        self.tabla.setRowCount(len(filas))
        for i, f in enumerate(filas):
            self.tabla.setItem(i, 0, QTableWidgetItem(str(f + 1)))
            for j, (_n, s) in enumerate(series, start=1):
                self.tabla.setItem(i, j, QTableWidgetItem(texto_celda(s.iloc[f])))
            if marca:
                self.tabla.setItem(i, len(cabecera) - 1, QTableWidgetItem(marca))
        self.tabla.resizeColumnsToContents()

    def _aceptar(self) -> None:
        try:
            self.paso()
        except ErrorUsuario as e:
            self._mostrar_error(str(e))
            return
        self.accept()


def texto_celda(v: Any) -> str:
    if v is None or v is pd.NA or (isinstance(v, float) and pd.isna(v)) or v is pd.NaT:
        return "NA"
    if isinstance(v, pd.Timestamp):
        return v.strftime("%d/%m/%Y")
    if isinstance(v, float):
        return fmt.num(v, fmt.column_decimals(pd.Series([v])))
    return str(v)

