import os
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QFontInfo

from statlab.app import create_app
from statlab.modules import available_modules
from statlab.modules.base import EstadoPaso
from statlab.ui import theme
from statlab.ui.main_window import MainWindow
from statlab.ui.theme import ThemeMode


@pytest.fixture
def window(qtbot, tmp_path):
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path))
    app = create_app([])
    w = MainWindow(available_modules()[0])
    qtbot.addWidget(w)
    w.resize(1440, 900)
    w.show()
    qtbot.waitExposed(w)
    yield w
    theme.apply_theme(app, ThemeMode.LIGHT)


def _capture(widget, name: str) -> None:
    """Guarda una captura si STATLAB_CAPTURAS apunta a una carpeta."""
    folder = os.environ.get("STATLAB_CAPTURAS")
    if folder:
        Path(folder).mkdir(parents=True, exist_ok=True)
        assert widget.grab().save(str(Path(folder) / f"{name}.png"))


def test_window_layout(window):
    assert window.windowTitle() == "StatLab · Clustering k-means"
    assert QFontInfo(window.font()).family() == "Inter"
    titles = [c.title.text() for c in window.sidebar.cards.values()]
    assert titles == ["Datos", "Variables y filas", "Preprocesado", "Elegir k", "Modelo final", "Exportar"]
    states = [c.state for c in window.sidebar.cards.values()]
    assert states[0] == EstadoPaso.ACTIVO
    assert all(s == EstadoPaso.PENDIENTE for s in states[1:])
    assert window.sidebar.width() >= 260


def test_theme_switch_persists(window):
    window.set_theme_mode(ThemeMode.LIGHT)
    assert not theme.is_dark()
    _capture(window, "m0-ventana-claro")
    window.set_theme_mode(ThemeMode.DARK)
    assert theme.is_dark()
    assert MainWindow.theme_mode() == ThemeMode.DARK
    assert window.theme_actions[ThemeMode.DARK].isChecked()
    _capture(window, "m0-ventana-oscuro")


def test_stylesheet_has_no_unfilled_tokens():
    for dark in (False, True):
        assert "${" not in theme.stylesheet(dark)
