"""Ventana principal: cabecera + barra lateral + tabla (arriba) y resultados (abajo)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, Qt, Signal, qVersion
from PySide6.QtGui import QAction, QActionGroup, QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from statlab import __version__
from statlab import strings_es as S
from statlab.core.errors import ErrorUsuario
from statlab.modules.base import AnalysisModule
from statlab.ui import theme
from statlab.ui.data_table.panel import DataPanel
from statlab.ui.results_panel import ResultsPanel
from statlab.ui.session import SessionController
from statlab.ui.sidebar.sidebar import Sidebar
from statlab.ui.theme import ThemeMode, icons
from statlab.ui.theme import tokens as tk

SETTINGS_THEME = "ui/theme"
SETTINGS_LAST_DIR = "files/last_dir"


def settings() -> QSettings:
    # INI en todos los SO (sin registro de Windows): más fácil de inspeccionar y de aislar en tests.
    return QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, "StatLab", "StatLab")


def _panel(parent: QWidget | None = None) -> QFrame:
    frame = QFrame(parent)
    frame.setObjectName("Panel")
    return frame


class Header(QFrame):
    open_requested = Signal()
    save_requested = Signal()

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
        module = QLabel(module_name)
        module.setObjectName("ModuleName")
        for w in (self.logo, title, module):
            row.addWidget(w)
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


class MainWindow(QMainWindow):
    def __init__(self, module: AnalysisModule, parent: QWidget | None = None):
        super().__init__(parent)
        self.module = module
        self.setWindowTitle(f"{S.APP_NAME} · {module.nombre}")
        self.setMinimumSize(1100, 700)
        self.resize(1440, 900)

        self.session = SessionController(module, self)
        self.header = Header(module.nombre)
        self.sidebar = Sidebar(self.session)
        self.sidebar.setMinimumWidth(260)
        self.welcome = WelcomePanel()
        self.data_panel = DataPanel(self.session)
        self.data_stack = QStackedWidget()
        self.data_stack.addWidget(self.welcome)
        self.data_stack.addWidget(self.data_panel)
        self.results = ResultsPanel(self.session)

        self.work_splitter = QSplitter(Qt.Orientation.Vertical)
        self.work_splitter.setChildrenCollapsible(False)
        self.work_splitter.setHandleWidth(10)
        self.work_splitter.addWidget(self.data_stack)
        self.work_splitter.addWidget(self.results)
        self.work_splitter.setSizes([480, 320])

        work = QWidget()
        work_layout = QVBoxLayout(work)
        work_layout.setContentsMargins(16, 16, 16, 16)
        work_layout.addWidget(self.work_splitter)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(1)
        self.main_splitter.addWidget(self.sidebar)
        self.main_splitter.addWidget(work)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setSizes([tk.METRICS["sidebar_width"], 1120])

        central = QWidget()
        central.setObjectName("Central")
        col = QVBoxLayout(central)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)
        col.addWidget(self.header)
        col.addWidget(self.main_splitter, 1)
        self.setCentralWidget(central)

        self._build_menus()
        self.welcome.open_button.setFocus()

        self.header.open_requested.connect(self.open_data)
        self.welcome.open_requested.connect(self.open_data)
        self.welcome.example_requested.connect(self.load_example)
        self.sidebar.change_data_requested.connect(self.open_data)
        self.results.content_shown.connect(self._make_room_for_results)
        self.session.dataset_changed.connect(self._on_dataset)
        QGuiApplication.styleHints().colorSchemeChanged.connect(self._on_system_scheme)

    # --- Datos -----------------------------------------------------------
    def open_data(self) -> None:
        start = str(settings().value(SETTINGS_LAST_DIR, ""))
        path, _ = QFileDialog.getOpenFileName(self, S.OPEN_DIALOG_TITLE, start, S.OPEN_DIALOG_FILTER)
        if path:
            self.load_path(path)

    def load_path(self, path: str) -> bool:
        try:
            self.session.load_path(path)
        except (ErrorUsuario, OSError) as e:
            name = Path(path).name
            QMessageBox.warning(self, S.READ_ERROR_TITLE, S.READ_ERROR.format(name=name, reason=e))
            return False
        settings().setValue(SETTINGS_LAST_DIR, str(Path(path).parent))
        return True

    def load_example(self) -> None:
        self.session.load_example()

    def _make_room_for_results(self) -> None:
        total = sum(self.work_splitter.sizes())
        self.work_splitter.setSizes([int(total * 0.35), total - int(total * 0.35)])

    def _on_dataset(self) -> None:
        self.data_stack.setCurrentWidget(self.data_panel)
        self.data_panel.table.setFocus()

    # --- Menús -----------------------------------------------------------
    def _build_menus(self) -> None:
        bar = self.menuBar()
        file_menu = bar.addMenu(S.MENU_FILE)
        self.action_open = QAction(S.OPEN_DATA, self, shortcut=QKeySequence.StandardKey.Open)
        self.action_open.triggered.connect(self.open_data)
        self.action_example = QAction(S.TRY_EXAMPLE, self)
        self.action_example.triggered.connect(self.load_example)
        self.action_save = QAction(S.SAVE_SESSION, self, shortcut=QKeySequence.StandardKey.Save)
        self.action_save.setEnabled(False)
        action_quit = QAction(S.QUIT, self, shortcut=QKeySequence.StandardKey.Quit)
        action_quit.triggered.connect(self.close)
        file_menu.addActions([self.action_open, self.action_example, self.action_save])
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
        self.data_panel.refresh_theme()
        self.results.refresh(force=True)

    def _on_system_scheme(self, *_args) -> None:
        if self.theme_mode() == ThemeMode.SYSTEM:
            self._apply_theme(ThemeMode.SYSTEM)

    def closeEvent(self, event) -> None:
        self.session.shutdown()
        super().closeEvent(event)

    def _about(self) -> None:
        QMessageBox.about(self, S.ABOUT, S.ABOUT_TEXT.format(version=__version__, qt=qVersion()))
