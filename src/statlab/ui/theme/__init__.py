"""Tema visual: fuente Inter empaquetada, paleta de Qt y hoja QSS.

Modo claro y oscuro desde los mismos tokens. Por defecto sigue al sistema;
el menú Ver permite forzarlo.
"""
from __future__ import annotations

from enum import StrEnum
from importlib import resources
from string import Template

from PySide6.QtCore import QDir, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication

from statlab.ui.theme import tokens as tk

FONT_FAMILY = "Inter"
_FONT_FILES = ("Inter-Regular.ttf", "Inter-Medium.ttf", "Inter-SemiBold.ttf", "Inter-Bold.ttf")


class ThemeMode(StrEnum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


def _theme_dir():
    return resources.files("statlab.ui.theme")


_loaded_family: str | None = None


def load_fonts() -> str:
    """Registra Inter (una sola vez) y devuelve la familia que se usará (Inter o la del sistema)."""
    global _loaded_family
    if _loaded_family:
        return _loaded_family
    family = None
    for name in _FONT_FILES:
        data = _theme_dir().joinpath("fonts", name).read_bytes()
        font_id = QFontDatabase.addApplicationFontFromData(data)
        if font_id >= 0 and family is None:
            family = QFontDatabase.applicationFontFamilies(font_id)[0]
    _loaded_family = family
    return family or QGuiApplication.font().family()


def tabular_font(base: QFont | None = None) -> QFont:
    """Fuente con cifras tabulares (todas del mismo ancho), para tablas."""
    font = QFont(base or QGuiApplication.font())
    font.setFeature(QFont.Tag("tnum"), 1)
    return font


def system_is_dark() -> bool:
    return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark


def resolve_dark(mode: ThemeMode) -> bool:
    if mode == ThemeMode.SYSTEM:
        return system_is_dark()
    return mode == ThemeMode.DARK


def stylesheet(dark: bool) -> str:
    template = Template(_theme_dir().joinpath("style.qss").read_text(encoding="utf-8"))
    values = {**tk.tokens(dark), **{k: str(v) for k, v in tk.METRICS.items()}, "mode": "dark" if dark else "light"}
    return template.substitute(values)


def palette(dark: bool) -> QPalette:
    t = tk.tokens(dark)
    pal = QPalette()
    roles = {
        QPalette.ColorRole.Window: t["bg"],
        QPalette.ColorRole.WindowText: t["text"],
        QPalette.ColorRole.Base: t["panel"],
        QPalette.ColorRole.AlternateBase: t["header_cell"],
        QPalette.ColorRole.Text: t["text_body"],
        QPalette.ColorRole.Button: t["panel"],
        QPalette.ColorRole.ButtonText: t["text"],
        QPalette.ColorRole.ToolTipBase: t["panel"],
        QPalette.ColorRole.ToolTipText: t["text"],
        QPalette.ColorRole.PlaceholderText: t["text_muted"],
        QPalette.ColorRole.Highlight: t["accent"],
        QPalette.ColorRole.HighlightedText: t["accent_text"],
        QPalette.ColorRole.Link: t["accent"],
        QPalette.ColorRole.Mid: t["border"],
        QPalette.ColorRole.Midlight: t["gridline"],
        QPalette.ColorRole.Dark: t["border_strong"],
    }
    for role, color in roles.items():
        pal.setColor(role, QColor(color))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText, QPalette.ColorRole.ButtonText):
        pal.setColor(QPalette.ColorGroup.Disabled, role, QColor(t["text_muted"]))
    return pal


def apply_theme(app: QApplication, mode: ThemeMode) -> bool:
    """Aplica el tema y devuelve si ha quedado en modo oscuro."""
    dark = resolve_dark(mode)
    app.setPalette(palette(dark))
    app.setStyleSheet(stylesheet(dark))
    app.setProperty("statlab_dark", dark)
    return dark


def is_dark(app: QApplication | None = None) -> bool:
    app = app or QApplication.instance()
    return bool(app and app.property("statlab_dark"))


def setup(app: QApplication, mode: ThemeMode = ThemeMode.SYSTEM) -> None:
    """Fusion + Inter + tema. Llamar una vez, antes de crear ventanas."""
    # La QSS referencia los iconos como «statlab:icons/…».
    QDir.setSearchPaths("statlab", [str(_theme_dir())])
    app.setStyle("Fusion")
    font = QFont(load_fonts())
    font.setPixelSize(tk.METRICS["font_size"])
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    app.setFont(font)
    apply_theme(app, mode)
