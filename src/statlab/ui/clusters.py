"""Color y símbolo de cada cluster: el mismo en gráficos, tabla y textos.

El color nunca es el único canal: cada cluster lleva además su símbolo.
"""
from __future__ import annotations

from statlab.ui.theme import tokens as tk

_PG_SYMBOL = {"circle": "o", "square": "s", "diamond": "d", "triangle-up": "t1", "x": "x", "cross": "+",
              "star": "star", "triangle-down": "t"}
_GLYPH = {"circle": "●", "square": "■", "diamond": "◆", "triangle-up": "▲", "x": "✕", "cross": "✚",
          "star": "★", "triangle-down": "▼"}


def color(c: int) -> str:
    return tk.SERIES[c]  # nunca se cicla: k ≤ 8


def pg_symbol(c: int) -> str:
    return _PG_SYMBOL[tk.SYMBOLS[c]]


def glyph(c: int) -> str:
    return _GLYPH[tk.SYMBOLS[c]]


def name(c: int) -> str:
    return f"C{c + 1}"


def html_label(c: int, text: str = "") -> str:
    return f'<span style="color:{color(c)}">{glyph(c)}</span> {name(c)}{text}'
