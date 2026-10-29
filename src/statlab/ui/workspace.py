"""Espacio de trabajo de un análisis: su controlador, barras laterales, tabla y resultados.

Una sesión puede tener varios análisis (una pestaña cada uno) sobre los mismos datos:
todos comparten la preparación (archivo, receta y diccionario), y cada uno tiene sus
roles, sus filas, sus parámetros y sus resultados.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter, QStackedWidget, QVBoxLayout, QWidget

from statlab import strings_es as S
from statlab.modules.base import AnalysisModule
from statlab.ui.data_table.panel import DataPanel
from statlab.ui.prep.flow import PrepResults
from statlab.ui.prep.sidebar import PrepSidebar
from statlab.ui.results_panel import ResultsPanel
from statlab.ui.session import SessionController
from statlab.ui.sidebar.sidebar import Sidebar
from statlab.ui.theme import tokens as tk

MODO_PREPARAR, MODO_ANALIZAR = "preparar", "analizar"


class Workspace(QWidget):
    def __init__(self, module: AnalysisModule, analysis_id: str, welcome: QWidget, parent: QWidget | None = None):
        super().__init__(parent)
        self.analysis_id = analysis_id
        self.nombre = ""  # nombre puesto por el usuario («» = automático)
        self.session = SessionController(module, self)

        self.sidebar = Sidebar(self.session)
        self.prep_sidebar = PrepSidebar(self.session)
        self.sidebar_stack = QStackedWidget()
        self.sidebar_stack.setMinimumWidth(260)
        self.sidebar_stack.addWidget(self.sidebar)
        self.sidebar_stack.addWidget(self.prep_sidebar)

        self.welcome = welcome
        self.data_panel = DataPanel(self.session)
        self.data_stack = QStackedWidget()
        self.data_stack.addWidget(self.welcome)
        self.data_stack.addWidget(self.data_panel)

        self.results = ResultsPanel(self.session)
        self.prep_results = PrepResults(self.session)
        self.results_stack = QStackedWidget()
        self.results_stack.addWidget(self.results)
        self.results_stack.addWidget(self.prep_results)

        self.work_splitter = QSplitter(Qt.Orientation.Vertical)
        self.work_splitter.setChildrenCollapsible(False)
        self.work_splitter.setHandleWidth(10)
        self.work_splitter.addWidget(self.data_stack)
        self.work_splitter.addWidget(self.results_stack)
        self.work_splitter.setSizes([480, 320])

        work = QWidget()
        work_layout = QVBoxLayout(work)
        work_layout.setContentsMargins(16, 16, 16, 16)
        work_layout.addWidget(self.work_splitter)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(1)
        self.main_splitter.addWidget(self.sidebar_stack)
        self.main_splitter.addWidget(work)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setSizes([tk.METRICS["sidebar_width"], 1120])

        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.addWidget(self.main_splitter)
        self.results.content_shown.connect(self._make_room_for_results)

    @property
    def module(self) -> AnalysisModule:
        return self.session.module

    def set_mode(self, modo: str) -> None:
        preparar = modo == MODO_PREPARAR
        self.sidebar_stack.setCurrentWidget(self.prep_sidebar if preparar else self.sidebar)
        self.results_stack.setCurrentWidget(self.prep_results if preparar else self.results)

    def titulo(self) -> str:
        """Nombre de la pestaña: el del usuario o «Algoritmo · k = 4» cuando hay modelo final."""
        if self.nombre:
            return self.nombre
        base = S.ANALYSIS_SHORT.get(self.module.id, self.module.nombre)
        r = self.session.estado.resultados.get("modelo_final")
        if r and "error" not in r:
            return S.ANALYSIS_TAB_K.format(name=base, k=r["k"])
        return base

    def _make_room_for_results(self) -> None:
        total = sum(self.work_splitter.sizes())
        self.work_splitter.setSizes([int(total * 0.35), total - int(total * 0.35)])

    def show_data(self) -> None:
        self.data_stack.setCurrentWidget(self.data_panel)
        self.data_panel.table.setFocus()

    def refresh_theme(self) -> None:
        self.data_panel.refresh_theme()
        self.results.refresh(force=True)
