from PySide6.QtGui import QFontInfo
from ui_helpers import capture

from statlab.modules.base import EstadoPaso
from statlab.ui import theme
from statlab.ui.main_window import MainWindow
from statlab.ui.theme import ThemeMode


def test_window_layout(window):
    assert window.windowTitle().startswith("StatLab · Clustering k-means")
    assert not window.header.save_button.isEnabled()
    assert QFontInfo(window.font()).family() == "Inter"
    titles = [c.title.text() for c in window.sidebar.cards.values()]
    assert titles == ["Datos", "Variables y filas", "Preprocesado", "Elegir k", "Modelo final", "Exportar"]
    states = [c.state for c in window.sidebar.cards.values()]
    assert states[0] == EstadoPaso.ACTIVO
    assert all(s == EstadoPaso.PENDIENTE for s in states[1:])
    datos = window.sidebar.cards["datos"]
    assert datos.summary.isVisible() and not datos.errors.isVisible()
    assert window.sidebar.width() >= 260


def test_theme_switch_persists(window):
    window.set_theme_mode(ThemeMode.LIGHT)
    assert not theme.is_dark()
    capture(window, "m0-ventana-claro")
    window.set_theme_mode(ThemeMode.DARK)
    assert theme.is_dark()
    assert MainWindow.theme_mode() == ThemeMode.DARK
    assert window.theme_actions[ThemeMode.DARK].isChecked()
    capture(window, "m0-ventana-oscuro")


def test_stylesheet_has_no_unfilled_tokens():
    for dark in (False, True):
        assert "${" not in theme.stylesheet(dark)
