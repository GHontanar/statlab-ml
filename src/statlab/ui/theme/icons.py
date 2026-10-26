"""Iconos SVG empaquetados, coloreados con los tokens del tema."""
from __future__ import annotations

from importlib import resources

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer


def svg_text(name: str, **colors: str) -> str:
    text = resources.files("statlab.ui.theme").joinpath("icons", f"{name}.svg").read_text(encoding="utf-8")
    for key, value in colors.items():
        text = text.replace("{" + key + "}", value)
    return text


def pixmap(name: str, size: int, device_pixel_ratio: float = 2.0, **colors: str) -> QPixmap:
    renderer = QSvgRenderer(QByteArray(svg_text(name, **colors).encode("utf-8")))
    px = QPixmap(QSize(size, size) * device_pixel_ratio)
    px.fill(Qt.GlobalColor.transparent)
    painter = QPainter(px)
    renderer.render(painter)
    painter.end()
    px.setDevicePixelRatio(device_pixel_ratio)
    return px


def icon(name: str, size: int = 64, **colors: str) -> QIcon:
    return QIcon(pixmap(name, size, 1.0, **colors))
