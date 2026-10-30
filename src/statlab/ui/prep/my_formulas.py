"""«Mis fórmulas»: biblioteca personal (fuera de las sesiones) y su diálogo."""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from statlab import strings_es as S
from statlab.core.errors import ErrorUsuario
from statlab.core.prep.mis_formulas import Biblioteca, FormulaGuardada
from statlab.ui.session import SessionController

ENV_PATH = "STATLAB_MIS_FORMULAS"  # para tests o para compartir una biblioteca en red


def ruta() -> Path:
    if os.environ.get(ENV_PATH):
        return Path(os.environ[ENV_PATH])
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    return Path(base or Path.home() / ".statlab") / "mis_formulas.json"


def cargar() -> Biblioteca:
    try:
        return Biblioteca.leer(ruta())
    except ErrorUsuario:
        return Biblioteca()


def guardar_en_biblioteca(parent: QWidget, nombre: str, texto: str) -> None:
    bib = cargar()
    try:
        bib.guardar_formula(FormulaGuardada(nombre, texto))
        bib.escribir(ruta())
    except (ErrorUsuario, OSError) as e:
        QMessageBox.warning(parent, S.MYF_TITLE, str(e))


class MisFormulasDialog(QDialog):
    """Elegir una fórmula guardada, indicar qué columna es cada entrada y añadirla a la receta."""

    NINGUNA = "—"

    def __init__(self, session: SessionController, parent: QWidget | None = None):
        super().__init__(parent)
        self.session = session
        self.setWindowTitle(S.MYF_TITLE)
        self.setMinimumSize(640, 420)
        self.bib = cargar()
        self.combos: dict[str, QComboBox] = {}

        row = QHBoxLayout(self)
        izq = QVBoxLayout()
        self.lista = QListWidget()
        self.lista.currentTextChanged.connect(self._mostrar)
        izq.addWidget(self.lista, 1)
        botones = QHBoxLayout()
        for texto, slot in ((S.MYF_IMPORT, self.importar), (S.MYF_EXPORT, self.exportar), (S.MYF_DELETE, self.borrar)):
            b = QPushButton(texto)
            b.clicked.connect(slot)
            botones.addWidget(b)
        izq.addLayout(botones)
        row.addLayout(izq, 1)

        der = QVBoxLayout()
        self.vacio = QLabel(S.MYF_EMPTY)
        self.vacio.setObjectName("Hint")
        self.vacio.setWordWrap(True)
        der.addWidget(self.vacio)
        self.texto = QLabel()
        self.texto.setObjectName("FormulaText")
        self.texto.setWordWrap(True)
        der.addWidget(self.texto)
        self.descr = QLabel()
        self.descr.setObjectName("Hint")
        self.descr.setWordWrap(True)
        der.addWidget(self.descr)
        self.form = QFormLayout()
        der.addLayout(self.form)
        self.destino = QLineEdit()
        fila = QFormLayout()
        lab = QLabel(S.F_TARGET)
        lab.setObjectName("FieldLabel")
        fila.addRow(lab, self.destino)
        der.addLayout(fila)
        der.addStretch(1)
        pie = QHBoxLayout()
        pie.addStretch(1)
        cerrar = QPushButton(S.CLOSE)
        cerrar.clicked.connect(self.reject)
        self.aplicar_b = QPushButton(S.MYF_APPLY)
        self.aplicar_b.setProperty("variant", "primary")
        self.aplicar_b.clicked.connect(self.aplicar)
        pie.addWidget(cerrar)
        pie.addWidget(self.aplicar_b)
        der.addLayout(pie)
        row.addLayout(der, 2)
        self._rellenar()

    def _rellenar(self) -> None:
        self.lista.clear()
        self.lista.addItems([f.nombre for f in self.bib.formulas])
        if self.bib.formulas:
            self.lista.setCurrentRow(0)
        self._mostrar(self.lista.currentItem().text() if self.lista.currentItem() else "")

    def _mostrar(self, nombre: str) -> None:
        f = self.bib.get(nombre)
        self.vacio.setVisible(f is None)
        self.aplicar_b.setEnabled(f is not None)
        while self.form.rowCount():
            self.form.removeRow(0)
        self.combos = {}
        if f is None:
            self.texto.clear()
            self.descr.clear()
            return
        self.texto.setText(f.formula)
        self.descr.setText(f.descripcion)
        self.destino.setText(f.nombre)
        columnas = self.session.dataset.columnas if self.session.dataset else []
        for e in f.entradas:
            combo = QComboBox()
            combo.addItem(self.NINGUNA)
            combo.addItems(columnas)
            if e in columnas:  # mismo nombre: se propone, el usuario lo ve y lo puede cambiar
                combo.setCurrentText(e)
            lab = QLabel(S.MYF_INPUT.format(name=e))
            lab.setObjectName("FieldLabel")
            self.form.addRow(lab, combo)
            self.combos[e] = combo

    def actual(self) -> FormulaGuardada | None:
        item = self.lista.currentItem()
        return self.bib.get(item.text()) if item else None

    def mapa(self) -> dict[str, str]:
        return {e: c.currentText() for e, c in self.combos.items() if c.currentText() != self.NINGUNA}

    def aplicar(self) -> None:
        f = self.actual()
        if f is None:
            return
        try:
            paso = f.paso(self.mapa(), self.destino.text().strip() or None)
            self.session.change_preparation(lambda p: p.receta.añadir(paso))
        except ErrorUsuario as e:
            QMessageBox.warning(self, S.MYF_TITLE, str(e))
            return
        self.accept()

    def _guardar(self) -> None:
        try:
            self.bib.escribir(ruta())
        except OSError as e:
            QMessageBox.warning(self, S.MYF_TITLE, str(e))

    def borrar(self) -> None:
        f = self.actual()
        if f is not None:
            self.bib.quitar(f.nombre)
            self._guardar()
            self._rellenar()

    def importar(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, S.MYF_IMPORT, "", S.MYF_FILTER)
        if not path:
            return
        try:
            nuevas, sustituidas = self.bib.importar(Biblioteca.leer(path))
        except ErrorUsuario as e:
            QMessageBox.warning(self, S.MYF_TITLE, str(e))
            return
        self._guardar()
        self._rellenar()
        QMessageBox.information(self, S.MYF_TITLE, S.MYF_IMPORTED.format(n=nuevas, m=sustituidas))

    def exportar(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, S.MYF_EXPORT, "mis_formulas.json", S.MYF_FILTER)
        if path:
            try:
                self.bib.escribir(path)
            except OSError as e:
                QMessageBox.warning(self, S.MYF_TITLE, str(e))
