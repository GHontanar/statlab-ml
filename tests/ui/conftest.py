import pytest
from PySide6.QtCore import QSettings

from statlab.app import create_app
from statlab.modules import available_modules
from statlab.ui import theme
from statlab.ui.main_window import MainWindow
from statlab.ui.theme import ThemeMode


@pytest.fixture
def window(qtbot, tmp_path, monkeypatch):
    # Sin diálogos modales en los tests: «No guardar» salvo que el test diga otra cosa.
    monkeypatch.setattr(MainWindow, "_ask_unsaved", lambda self: "discard")
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path))
    monkeypatch.setenv("STATLAB_MIS_FORMULAS", str(tmp_path / "mis_formulas.json"))
    app = create_app([])
    theme.apply_theme(app, ThemeMode.LIGHT)
    w = MainWindow(available_modules()[0])
    qtbot.addWidget(w)
    w.resize(1440, 900)
    w.show()
    qtbot.waitExposed(w)
    yield w
    theme.apply_theme(app, ThemeMode.LIGHT)
