"""Editor del diccionario de variables (una fila por columna de la tabla de análisis)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from statlab import strings_es as S
from statlab.core.errors import ErrorUsuario
from statlab.core.prep.diccionario import COLUMNAS, Diccionario
from statlab.ui.session import SessionController

CABECERAS = [S.DICT_COLS[c] for c in COLUMNAS]


class DiccionarioDialog(QDialog):
    def __init__(self, session: SessionController, parent: QWidget | None = None):
        super().__init__(parent)
        self.session = session
        self.setWindowTitle(S.DICT_TITLE)
        self.setMinimumSize(900, 480)
        col = QVBoxLayout(self)
        intro = QLabel(S.DICT_INTRO)
        intro.setObjectName("Hint")
        intro.setWordWrap(True)
        col.addWidget(intro)
        self.tabla = QTableWidget(0, len(COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(CABECERAS)
        self.tabla.verticalHeader().hide()
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tabla.horizontalHeader().setStretchLastSection(True)
        col.addWidget(self.tabla, 1)
        pie = QHBoxLayout()
        for texto, slot in ((S.DICT_IMPORT, self.importar), (S.DICT_EXPORT, self.exportar)):
            b = QPushButton(texto)
            b.clicked.connect(slot)
            pie.addWidget(b)
        pie.addStretch(1)
        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText(S.UNSAVED_CANCEL)
        botones.accepted.connect(self._aceptar)
        botones.rejected.connect(self.reject)
        pie.addWidget(botones)
        col.addLayout(pie)
        self.columnas = session.dataset.columnas
        self.cargar(session.prep.diccionario)

    def cargar(self, dic: Diccionario) -> None:
        tabla = dic.a_tabla(self.columnas)
        self.tabla.setRowCount(len(tabla))
        for i, fila in tabla.iterrows():
            for j, c in enumerate(COLUMNAS):
                v = fila[c]
                texto = "" if v is None or (isinstance(v, float) and v != v) else str(v)
                if c in ("minimo", "maximo") and texto:
                    texto = texto.removesuffix(".0").replace(".", ",")
                item = QTableWidgetItem(texto)
                if c == "variable":
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.tabla.setItem(int(i), j, item)
        self.tabla.resizeColumnsToContents()

    def leer(self) -> Diccionario:
        import pandas as pd

        filas = []
        for i in range(self.tabla.rowCount()):
            filas.append({c: (self.tabla.item(i, j).text() if self.tabla.item(i, j) else "")
                          for j, c in enumerate(COLUMNAS)})
        return Diccionario.desde_tabla(pd.DataFrame(filas, columns=list(COLUMNAS)))

    def _aceptar(self) -> None:
        try:
            nuevo = self.leer()
        except ErrorUsuario as e:
            QMessageBox.warning(self, S.DICT_TITLE, str(e))
            return
        # se conservan las entradas de columnas que ahora no están en la tabla
        otras = {c: e for c, e in self.session.prep.diccionario.entradas.items() if c not in self.columnas}

        def cambio(dic: Diccionario) -> None:
            dic.entradas = {**otras, **nuevo.entradas}

        self.session.change_dictionary(cambio)
        self.accept()

    def importar(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, S.DICT_IMPORT, "", S.DICT_FILTER)
        if not path:
            return
        try:
            importado = Diccionario.importar(path)
        except ErrorUsuario as e:
            QMessageBox.warning(self, S.DICT_TITLE, str(e))
            return
        actual = self.leer()
        actual.entradas.update(importado.entradas)
        self.cargar(actual)
        fuera = [c for c in importado.entradas if c not in self.columnas]
        if fuera:
            QMessageBox.information(self, S.DICT_TITLE, S.DICT_IMPORT_UNKNOWN.format(n=len(fuera)))

    def exportar(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, S.DICT_EXPORT, "diccionario.xlsx", S.DICT_FILTER)
        if not path:
            return
        try:
            self.leer().exportar(path, self.columnas)
        except (ErrorUsuario, OSError) as e:
            QMessageBox.warning(self, S.DICT_TITLE, str(e))
