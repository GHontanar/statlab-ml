"""Ventana principal: cabecera + barra lateral + tabla (arriba) y resultados (abajo)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, Qt, Signal, qVersion
from PySide6.QtGui import QAction, QActionGroup, QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTabBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from statlab import __version__
from statlab import strings_es as S
from statlab.core import comparacion as cmp
from statlab.core import session as ses
from statlab.core.errors import ErrorUsuario
from statlab.modules import available_modules
from statlab.modules.base import AnalysisModule
from statlab.ui import theme
from statlab.ui.comparison import ComparisonPanel
from statlab.ui.prep.dictionary import DiccionarioDialog
from statlab.ui.prep.my_formulas import MisFormulasDialog
from statlab.ui.theme import ThemeMode, icons
from statlab.ui.theme import tokens as tk
from statlab.ui.workspace import MODO_ANALIZAR, MODO_PREPARAR, Workspace

SETTINGS_THEME = "ui/theme"
SETTINGS_LAST_DIR = "files/last_dir"


def settings() -> QSettings:
    # INI en todos los SO (sin registro de Windows): más fácil de inspeccionar y de aislar en tests.
    return QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, "StatLab", "StatLab")


def _panel(parent: QWidget | None = None) -> QFrame:
    frame = QFrame(parent)
    frame.setObjectName("Panel")
    return frame


__all__ = ["MODO_ANALIZAR", "MODO_PREPARAR", "MainWindow"]


class Header(QFrame):
    open_requested = Signal()
    save_requested = Signal()
    mode_requested = Signal(str)

    def __init__(self, module_name: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Header")
        row = QHBoxLayout(self)
        row.setContentsMargins(20, 10, 20, 10)
        row.setSpacing(10)

        self.logo = QLabel()
        self.logo.setFixedSize(26, 26)
        title = QLabel(S.APP_NAME)
        title.setObjectName("AppTitle")
        self.module_label = QLabel(module_name)
        self.module_label.setObjectName("ModuleName")
        for w in (self.logo, title, self.module_label):
            row.addWidget(w)
        row.addSpacing(16)
        # Selector de modo: preparar los datos o analizarlos
        self.modes = QFrame()
        self.modes.setObjectName("ModeSwitch")
        modes_row = QHBoxLayout(self.modes)
        modes_row.setContentsMargins(3, 3, 3, 3)
        modes_row.setSpacing(2)
        self.mode_group = QButtonGroup(self)
        self.mode_buttons: dict[str, QPushButton] = {}
        for modo, texto in ((MODO_PREPARAR, S.MODE_PREPARE), (MODO_ANALIZAR, S.MODE_ANALYZE)):
            b = QPushButton(texto)
            b.setObjectName("ModeButton")
            b.setCheckable(True)
            b.setFocusPolicy(Qt.FocusPolicy.TabFocus)
            b.clicked.connect(lambda _=False, m=modo: self.mode_requested.emit(m))
            self.mode_group.addButton(b)
            modes_row.addWidget(b)
            self.mode_buttons[modo] = b
        self.modes.hide()
        row.addWidget(self.modes)
        row.addStretch(1)

        badge = QFrame()
        badge.setObjectName("OfflineBadge")
        badge_row = QHBoxLayout(badge)
        badge_row.setContentsMargins(10, 4, 10, 4)
        badge_row.setSpacing(6)
        self.lock = QLabel()
        self.lock.setFixedSize(12, 12)
        badge_row.addWidget(self.lock)
        badge_row.addWidget(QLabel(S.OFFLINE_BADGE))
        row.addWidget(badge)
        row.addSpacing(10)

        self.open_button = QPushButton(S.OPEN_DATA)
        self.save_button = QPushButton(S.SAVE_SESSION)
        self.save_button.setEnabled(False)
        for button in (self.open_button, self.save_button):
            button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.open_button.clicked.connect(self.open_requested)
        self.save_button.clicked.connect(self.save_requested)
        row.addWidget(self.open_button)
        row.addWidget(self.save_button)
        self.refresh_icons()

    def refresh_icons(self) -> None:
        t = tk.tokens(theme.is_dark())
        self.logo.setPixmap(icons.pixmap("logo", 26, accent=t["accent"]))
        self.lock.setPixmap(icons.pixmap("lock", 12, color=t["done"]))


class WelcomePanel(QFrame):
    """Estado vacío de la zona de datos: abrir un archivo o probar el ejemplo."""

    open_requested = Signal()
    example_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Panel")
        col = QVBoxLayout(self)
        col.setContentsMargins(32, 32, 32, 32)
        col.setSpacing(12)
        col.addStretch(1)

        title = QLabel(S.WELCOME_TITLE)
        title.setObjectName("EmptyTitle")
        body = QLabel(S.WELCOME_BODY)
        body.setObjectName("EmptyBody")
        body.setWordWrap(True)
        body.setFixedWidth(520)
        for w in (title, body):
            w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # Sin alineación en el layout: así respeta el alto del texto ajustado.
            centered = QHBoxLayout()
            centered.addStretch(1)
            centered.addWidget(w)
            centered.addStretch(1)
            col.addLayout(centered)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addStretch(1)
        self.open_button = QPushButton(S.OPEN_DATA)
        self.open_button.setProperty("variant", "primary")
        self.example_button = QPushButton(S.TRY_EXAMPLE)
        self.open_button.clicked.connect(self.open_requested)
        self.example_button.clicked.connect(self.example_requested)
        buttons.addWidget(self.open_button)
        buttons.addWidget(self.example_button)
        buttons.addStretch(1)
        col.addSpacing(8)
        col.addLayout(buttons)
        col.addStretch(2)


class AnalysisTabs(QFrame):
    """Pestañas de los análisis de la sesión y botón «Nuevo análisis»."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("AnalysisTabs")
        row = QHBoxLayout(self)
        row.setContentsMargins(16, 0, 16, 0)
        row.setSpacing(8)
        self.bar = QTabBar()
        self.bar.setObjectName("AnalysisTabBar")
        self.bar.setDocumentMode(True)
        self.bar.setExpanding(False)
        self.bar.setElideMode(Qt.TextElideMode.ElideNone)
        row.addWidget(self.bar)
        self.add_button = QToolButton()
        self.add_button.setObjectName("NewAnalysis")
        self.add_button.setText(S.NEW_ANALYSIS)
        self.add_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.add_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        row.addWidget(self.add_button)
        row.addStretch(1)


class MainWindow(QMainWindow):
    def __init__(self, module: AnalysisModule, parent: QWidget | None = None):
        super().__init__(parent)
        self.default_module = module
        self.modules = {m.id: m for m in available_modules()}
        self.modules.setdefault(module.id, module)
        self.setWindowTitle(f"{S.APP_NAME}[*]")
        self.setMinimumSize(1100, 700)
        self.resize(1440, 900)
        self.mode = MODO_ANALIZAR
        self.workspaces: list[Workspace] = []
        self._next_id = 1
        self._structure_dirty = False  # pestañas añadidas, cerradas o renombradas

        self.header = Header(module.nombre)
        self.tabs = AnalysisTabs()
        self.tabs.hide()
        self.stack = QStackedWidget()
        self.comparison = ComparisonPanel(self._soluciones_sesion)
        self.stack.addWidget(self.comparison)
        self.tabs.bar.addTab(S.CMP_TAB)  # siempre la última pestaña
        self._current: Workspace | None = None
        self._build_new_menu()

        central = QWidget()
        central.setObjectName("Central")
        col = QVBoxLayout(central)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)
        col.addWidget(self.header)
        col.addWidget(self.tabs)
        col.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        self._build_menus()
        self._activate(self._add_workspace(module))
        self.welcome.open_button.setFocus()

        self.header.open_requested.connect(self.open_data)
        self.header.save_requested.connect(self.save_session)
        self.header.mode_requested.connect(self.set_mode)
        self.tabs.bar.currentChanged.connect(self._tab_changed)
        self.tabs.bar.tabCloseRequested.connect(self.close_analysis)
        self.comparison.changed.connect(self._comparison_changed)
        self.comparison.select_in_analysis.connect(self._select_in_analysis)
        self.tabs.bar.tabBarDoubleClicked.connect(self.rename_analysis)
        QGuiApplication.styleHints().colorSchemeChanged.connect(self._on_system_scheme)

    # --- Análisis (pestañas) ---------------------------------------------
    @property
    def workspace(self) -> Workspace:
        """Análisis activo (si se está viendo la comparación, el último que se vio)."""
        return self._current

    @property
    def comparing(self) -> bool:
        return self.stack.currentWidget() is self.comparison

    # Atajos al análisis activo (los usan la app y los tests)
    session = property(lambda self: self.workspace.session)
    sidebar = property(lambda self: self.workspace.sidebar)
    prep_sidebar = property(lambda self: self.workspace.prep_sidebar)
    data_panel = property(lambda self: self.workspace.data_panel)
    data_stack = property(lambda self: self.workspace.data_stack)
    welcome = property(lambda self: self.workspace.welcome)
    results = property(lambda self: self.workspace.results)
    prep_results = property(lambda self: self.workspace.prep_results)
    sidebar_stack = property(lambda self: self.workspace.sidebar_stack)
    results_stack = property(lambda self: self.workspace.results_stack)
    work_splitter = property(lambda self: self.workspace.work_splitter)
    main_splitter = property(lambda self: self.workspace.main_splitter)
    module = property(lambda self: self.workspace.module)

    def _build_new_menu(self) -> None:
        menu = QMenu(self)
        for m in self.modules.values():
            action = menu.addAction(m.nombre)
            action.setToolTip(getattr(m, "descripcion", ""))
            action.triggered.connect(lambda _=False, mid=m.id: self.new_analysis(mid))
        menu.setToolTipsVisible(True)
        self.tabs.add_button.setMenu(menu)

    def _add_workspace(self, module: AnalysisModule, analysis_id: str | None = None) -> Workspace:
        if analysis_id is None:
            analysis_id = f"a{self._next_id}"
        welcome = WelcomePanel()
        ws = Workspace(module, analysis_id, welcome)
        ws.set_mode(self.mode)
        s = ws.session
        s.guardar_proyecto = self._save_project
        welcome.open_requested.connect(self.open_data)
        welcome.example_requested.connect(self.load_example)
        ws.sidebar.change_data_requested.connect(self.open_data)
        ws.prep_sidebar.continue_requested.connect(lambda: self.set_mode(MODO_ANALIZAR))
        ws.prep_sidebar.dictionary_requested.connect(self.edit_dictionary)
        ws.prep_sidebar.my_formulas_requested.connect(self.my_formulas)
        s.dataset_changed.connect(lambda w=ws: self._on_dataset(w))
        s.dirty_changed.connect(self._update_title)
        s.prep_edited.connect(lambda datos, w=ws: self._propagate_prep(w, datos))
        for signal in (s.flow_changed, s.step_updated):
            signal.connect(lambda *_a, w=ws: self._refresh_tab(w))
        self.tabs.bar.blockSignals(True)
        self.tabs.bar.insertTab(len(self.workspaces), ws.titulo())
        self.tabs.bar.blockSignals(False)
        self.workspaces.append(ws)
        self.stack.addWidget(ws)
        self._next_id = max(self._next_id, self._numero(analysis_id) + 1)
        self._update_tabs()
        return ws

    @staticmethod
    def _numero(analysis_id: str) -> int:
        return int(analysis_id[1:]) if analysis_id[1:].isdigit() else 0

    def _remove_workspace(self, ws: Workspace) -> None:
        i = self.workspaces.index(ws)
        ws.session.shutdown()
        self.workspaces.pop(i)
        self.tabs.bar.blockSignals(True)
        self.tabs.bar.removeTab(i)
        self.tabs.bar.blockSignals(False)
        self.stack.removeWidget(ws)
        ws.hide()
        ws.deleteLater()

    def _keep_only_first(self) -> Workspace:
        for ws in self.workspaces[1:]:
            self._remove_workspace(ws)
        first = self.workspaces[0]
        first.nombre = ""
        self._activate(first)
        self.comparison.load(None)
        self._next_id = self._numero(first.analysis_id) + 1
        self._structure_dirty = False
        return first

    def _activate(self, ws: Workspace) -> None:
        i = self.workspaces.index(ws)
        self._current = ws
        self.stack.setCurrentWidget(ws)
        self.tabs.bar.blockSignals(True)
        self.tabs.bar.setCurrentIndex(i)
        self.tabs.bar.blockSignals(False)
        self.header.module_label.setText(ws.module.nombre)
        self._update_title()

    def _tab_changed(self, i: int) -> None:
        if 0 <= i < len(self.workspaces):
            self._activate(self.workspaces[i])
        elif i == len(self.workspaces):
            self.show_comparison()

    def show_comparison(self) -> None:
        self.comparison.refresh()
        self.stack.setCurrentWidget(self.comparison)
        self.tabs.bar.blockSignals(True)
        self.tabs.bar.setCurrentIndex(len(self.workspaces))
        self.tabs.bar.blockSignals(False)
        self.header.module_label.setText(S.CMP_TITLE)

    def _soluciones_sesion(self) -> list[tuple[str, cmp.Solucion]]:
        """Los modelos finales de los análisis de la sesión, como soluciones comparables."""
        out = []
        for ws in self.workspaces:
            r = ws.session.estado.resultados.get("modelo_final")
            ds = ws.session.dataset
            if not r or "error" in r or ds is None:
                continue
            raw = ws.session.prep.raw if ws.session.prep else None
            sol = cmp.desde_resultado(ws.titulo(), r, ds.df, ds.identificador, raw, origen=f"analisis:{ws.analysis_id}")
            out.append((f"analisis:{ws.analysis_id}", sol))
        return out

    def _comparison_changed(self) -> None:
        self._structure_dirty = True
        self._update_title()

    def _select_in_analysis(self, analysis_id: str, filas: list) -> None:
        ws = next((w for w in self.workspaces if w.analysis_id == analysis_id), None)
        if ws is not None:
            self._activate(ws)
            ws.session.select_rows(filas)

    def _refresh_tab(self, ws: Workspace) -> None:
        if ws in self.workspaces:
            i = self.workspaces.index(ws)
            self.tabs.bar.setTabText(i, ws.titulo())
            self.tabs.bar.setTabToolTip(i, ws.module.nombre)

    def _update_tabs(self) -> None:
        for ws in self.workspaces:
            self._refresh_tab(ws)
        self.tabs.bar.setTabsClosable(len(self.workspaces) > 1)
        if len(self.workspaces) > 1:  # la comparación no se cierra
            self.tabs.bar.setTabButton(len(self.workspaces), QTabBar.ButtonPosition.RightSide, None)
        self.tabs.setVisible(self.workspaces[0].session.dataset is not None and self.mode == MODO_ANALIZAR)

    def new_analysis(self, module_id: str) -> Workspace | None:
        """Análisis nuevo sobre los mismos datos. Copia los roles y las filas del análisis activo."""
        actual = self.workspace
        prep = actual.session.prep
        if prep is None or actual.session.dataset is None:
            return None
        dataset, _ = prep.dataset(actual.session.dataset)
        ws = self._add_workspace(self.modules[module_id])
        ws.session.adopt(prep, dataset)
        self._activate(ws)
        self.set_mode(MODO_ANALIZAR)
        self._structure_dirty = True
        self._update_tabs()
        self._update_title()
        return ws

    def close_analysis(self, index: int) -> bool:
        if len(self.workspaces) < 2 or index >= len(self.workspaces):
            return False
        ws = self.workspaces[index]
        if ws.session.estado.resultados.get("elegir_k") and not self._confirm_close(ws):
            return False
        activo = self.workspace is ws
        self._remove_workspace(ws)
        if activo:
            self._activate(self.workspaces[max(0, index - 1)])
        elif self.comparing:
            self.comparison.refresh()
        self._structure_dirty = True
        self._update_tabs()
        self._update_title()
        return True

    def _confirm_close(self, ws: Workspace) -> bool:
        answer = QMessageBox.question(self, S.CLOSE_ANALYSIS_TITLE, S.CLOSE_ANALYSIS_TEXT.format(name=ws.titulo()))
        return answer == QMessageBox.StandardButton.Yes

    def rename_analysis(self, index: int) -> None:
        if not 0 <= index < len(self.workspaces):
            return
        ws = self.workspaces[index]
        nombre, ok = self._ask_name(ws)
        if ok:
            ws.nombre = nombre.strip()
            self._structure_dirty = True
            self._refresh_tab(ws)
            self._update_title()

    def _ask_name(self, ws: Workspace) -> tuple[str, bool]:
        return QInputDialog.getText(self, S.RENAME_ANALYSIS_TITLE, S.RENAME_ANALYSIS_TEXT, text=ws.titulo())

    def _propagate_prep(self, origen: Workspace, datos: bool) -> None:
        """La preparación es compartida: lo que cambia en un análisis llega a los demás."""
        for ws in self.workspaces:
            if ws is not origen:
                if datos:
                    ws.session.sync_preparation()
                else:
                    ws.session.notify_preparation()

    # --- Datos -----------------------------------------------------------
    def open_data(self) -> None:
        if not self.maybe_save():
            return
        start = str(settings().value(SETTINGS_LAST_DIR, ""))
        filtro = f"{S.OPEN_DIALOG_FILTER};;{S.SESSION_FILTER}"
        path, _ = QFileDialog.getOpenFileName(self, S.OPEN_DIALOG_TITLE, start, filtro)
        if path:
            self.load_path(path)

    def load_path(self, path: str) -> bool:
        """Abre datos o, si es un .statlab, una sesión."""
        if Path(path).suffix.lower() == ses.SUFIJO:
            return self.open_session_path(path)
        try:
            from statlab.core.prep.preparacion import Preparacion
            from statlab.ui.session import _leyendo

            raw = Path(path).read_bytes()
            prep = _leyendo(lambda: Preparacion.desde_archivo(Path(path).name, raw))
        except (ErrorUsuario, OSError) as e:
            name = Path(path).name
            QMessageBox.warning(self, S.READ_ERROR_TITLE, S.READ_ERROR.format(name=name, reason=e))
            return False
        self._keep_only_first().session._set_prep(prep)
        settings().setValue(SETTINGS_LAST_DIR, str(Path(path).parent))
        self.set_mode(MODO_PREPARAR)  # un archivo nuevo empieza por revisar y preparar los datos
        return True

    def load_example(self) -> None:
        if self.maybe_save():
            self._keep_only_first().session.load_example()
            self.set_mode(MODO_ANALIZAR)  # los datos de ejemplo ya están limpios

    # --- Modo ------------------------------------------------------------
    def set_mode(self, modo: str) -> None:
        self.mode = modo
        for ws in self.workspaces:
            ws.set_mode(modo)
        if modo == MODO_PREPARAR and self.comparing:
            self._activate(self._current)
        self.header.mode_buttons[modo].setChecked(True)
        self._update_tabs()

    def edit_dictionary(self) -> None:
        if self.session.prep is not None:
            DiccionarioDialog(self.session, self).exec()

    def my_formulas(self) -> None:
        if self.session.prep is not None:
            MisFormulasDialog(self.session, self).exec()

    # --- Sesiones --------------------------------------------------------
    @property
    def dirty(self) -> bool:
        return self._structure_dirty or any(ws.session.dirty for ws in self.workspaces)

    def open_session(self) -> None:
        if not self.maybe_save():
            return
        start = str(settings().value(SETTINGS_LAST_DIR, ""))
        path, _ = QFileDialog.getOpenFileName(self, S.SESSION_OPEN, start, S.SESSION_FILTER)
        if path:
            self.open_session_path(path)

    def open_session_path(self, path: str) -> bool:
        try:
            proyecto = ses.abrir_proyecto(path, {mid: m.crear_estado for mid, m in self.modules.items()})
        except (ErrorUsuario, OSError) as e:
            QMessageBox.warning(self, S.SESSION_OPEN_ERROR_TITLE, str(e))
            return False
        # Nuevas pestañas, una por análisis; la primera reutiliza la ventana vacía si es del mismo módulo
        for ws in list(self.workspaces):
            ws.session.shutdown()
        viejos = list(self.workspaces)
        nuevos = []
        for a in proyecto.analisis:
            ws = self._add_workspace(self.modules[a.modulo], a.id)
            ws.nombre = a.nombre
            ws.session.restore(a.estado, Path(path))
            nuevos.append(ws)
        for ws in viejos:
            self._remove_workspace(ws)
        activo = next((ws for ws in nuevos if ws.analysis_id == proyecto.activo), nuevos[0])
        self._activate(activo)
        self.comparison.load(proyecto.extra.get("comparacion"))
        self._structure_dirty = False
        settings().setValue(SETTINGS_LAST_DIR, str(Path(path).parent))
        self.set_mode(MODO_ANALIZAR)
        self._update_tabs()
        self._update_title()
        return True

    def _save_project(self, path: str | Path) -> Path:
        """Guarda todos los análisis (lo llama el controlador del análisis activo)."""
        proyecto = ses.Proyecto(
            [ses.AnalisisGuardado(ws.analysis_id, ws.module.id, ws.nombre, ws.session.estado)
             for ws in self.workspaces],
            activo=self.workspace.analysis_id,
            preparacion=self.workspaces[0].session.prep,
            extra={"comparacion": self.comparison.to_dict()},
        )
        guardado = ses.guardar_proyecto(path, proyecto)
        for ws in self.workspaces:
            ws.session.saved_as(guardado)
        self._structure_dirty = False
        return guardado

    def save_session(self, save_as: bool = False) -> bool:
        if self.session.dataset is None:
            return False
        path = self.session.session_path
        if save_as or path is None:
            start = Path(str(settings().value(SETTINGS_LAST_DIR, "")) or Path.home())
            name = Path(self.session.dataset.fuente).stem + ses.SUFIJO
            chosen, _ = QFileDialog.getSaveFileName(self, S.SESSION_SAVE, str(start / name), S.SESSION_FILTER)
            if not chosen:
                return False
            path = Path(chosen)
        try:
            saved = self.session.save_session(path)
        except (ErrorUsuario, OSError) as e:
            QMessageBox.warning(self, S.SESSION_SAVE_ERROR_TITLE, str(e))
            return False
        settings().setValue(SETTINGS_LAST_DIR, str(saved.parent))
        self._update_title()
        return True

    def maybe_save(self) -> bool:
        """Si hay cambios sin guardar, pregunta. Devuelve False si el usuario cancela."""
        if not self.dirty:
            return True
        answer = self._ask_unsaved()
        if answer == "save":
            return self.save_session()
        if answer == "discard":
            self._structure_dirty = False
            return True
        return False

    def _ask_unsaved(self) -> str:
        """«save», «discard» o «cancel»."""
        box = QMessageBox(QMessageBox.Icon.Question, S.UNSAVED_TITLE, S.UNSAVED_TEXT, parent=self)
        save = box.addButton(S.UNSAVED_SAVE, QMessageBox.ButtonRole.AcceptRole)
        discard = box.addButton(S.UNSAVED_DISCARD, QMessageBox.ButtonRole.DestructiveRole)
        box.addButton(S.UNSAVED_CANCEL, QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(save)
        box.exec()
        if box.clickedButton() is save:
            return "save"
        return "discard" if box.clickedButton() is discard else "cancel"

    def _update_title(self, *_args) -> None:
        if not self.workspaces:
            return
        path = self.session.session_path
        name = path.name if path else None
        base = f"{S.APP_NAME} · {self.module.nombre}"
        self.setWindowTitle(f"{base} — {name}[*]" if name else f"{base}[*]")
        self.setWindowModified(self.dirty)
        has_data = self.session.dataset is not None
        self.header.modes.setVisible(has_data)
        self.header.save_button.setEnabled(has_data)
        self.action_save.setEnabled(has_data)
        self.action_save_as.setEnabled(has_data)

    def _on_dataset(self, ws: Workspace) -> None:
        if ws is self.workspace:
            self._update_title()
        ws.show_data()
        self._update_tabs()

    # --- Menús -----------------------------------------------------------
    def _build_menus(self) -> None:
        bar = self.menuBar()
        file_menu = bar.addMenu(S.MENU_FILE)
        self.action_open = QAction(S.OPEN_DATA, self, shortcut=QKeySequence.StandardKey.Open)
        self.action_open.triggered.connect(self.open_data)
        self.action_example = QAction(S.TRY_EXAMPLE, self)
        self.action_example.triggered.connect(self.load_example)
        self.action_open_session = QAction(S.SESSION_OPEN, self)
        self.action_open_session.triggered.connect(self.open_session)
        self.action_save = QAction(S.SAVE_SESSION, self, shortcut=QKeySequence.StandardKey.Save)
        self.action_save.setEnabled(False)
        self.action_save.triggered.connect(lambda: self.save_session())
        self.action_save_as = QAction(S.SESSION_SAVE_AS, self, shortcut=QKeySequence.StandardKey.SaveAs)
        self.action_save_as.setEnabled(False)
        self.action_save_as.triggered.connect(lambda: self.save_session(save_as=True))
        action_quit = QAction(S.QUIT, self, shortcut=QKeySequence.StandardKey.Quit)
        action_quit.triggered.connect(self.close)
        file_menu.addActions([self.action_open, self.action_example])
        file_menu.addSeparator()
        file_menu.addActions([self.action_open_session, self.action_save, self.action_save_as])
        file_menu.addSeparator()
        file_menu.addAction(action_quit)

        view_menu = bar.addMenu(S.MENU_VIEW)
        theme_menu = view_menu.addMenu(S.MENU_THEME)
        group = QActionGroup(self)
        self.theme_actions: dict[ThemeMode, QAction] = {}
        current = self.theme_mode()
        for mode, label in (
            (ThemeMode.SYSTEM, S.THEME_SYSTEM),
            (ThemeMode.LIGHT, S.THEME_LIGHT),
            (ThemeMode.DARK, S.THEME_DARK),
        ):
            action = QAction(label, self, checkable=True)
            action.setChecked(mode == current)
            action.triggered.connect(lambda _=False, m=mode: self.set_theme_mode(m))
            group.addAction(action)
            theme_menu.addAction(action)
            self.theme_actions[mode] = action

        help_menu = bar.addMenu(S.MENU_HELP)
        about = QAction(S.ABOUT, self)
        about.triggered.connect(self._about)
        help_menu.addAction(about)

    # --- Tema ------------------------------------------------------------
    @staticmethod
    def theme_mode() -> ThemeMode:
        value = settings().value(SETTINGS_THEME, ThemeMode.SYSTEM.value)
        try:
            return ThemeMode(value)
        except ValueError:
            return ThemeMode.SYSTEM

    def set_theme_mode(self, mode: ThemeMode) -> None:
        settings().setValue(SETTINGS_THEME, mode.value)
        self.theme_actions[mode].setChecked(True)
        self._apply_theme(mode)

    def _apply_theme(self, mode: ThemeMode) -> None:
        theme.apply_theme(QApplication.instance(), mode)
        self.header.refresh_icons()
        for ws in self.workspaces:
            ws.refresh_theme()

    def _on_system_scheme(self, *_args) -> None:
        if self.theme_mode() == ThemeMode.SYSTEM:
            self._apply_theme(ThemeMode.SYSTEM)

    def closeEvent(self, event) -> None:
        if not self.maybe_save():
            event.ignore()
            return
        for ws in self.workspaces:
            ws.session.shutdown()
        super().closeEvent(event)

    def _about(self) -> None:
        QMessageBox.about(self, S.ABOUT, S.ABOUT_TEXT.format(version=__version__, qt=qVersion()))
