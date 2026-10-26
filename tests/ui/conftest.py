import pytest
from PySide6.QtCore import QSettings

from statlab.app import create_app
from statlab.modules import available_modules
from statlab.ui import theme
from statlab.ui.main_window import MainWindow
from statlab.ui.theme import ThemeMode


@pytest.fixture
def window(qtbot, tmp_path):
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path))
    app = create_app([])
    theme.apply_theme(app, ThemeMode.LIGHT)
    w = MainWindow(available_modules()[0])
    qtbot.addWidget(w)
    w.resize(1440, 900)
    w.show()
    qtbot.waitExposed(w)
    yield w
    theme.apply_theme(app, ThemeMode.LIGHT)
