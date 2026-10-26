"""Tokens de diseño: colores, espaciados y radios.

Los modos claro y oscuro se generan de los mismos nombres de token; la QSS
(`style.qss`) y la paleta de Qt solo usan estos nombres.
"""
from __future__ import annotations

LIGHT: dict[str, str] = {
    # Superficies
    "bg": "#EEEDE9",
    "panel": "#FFFFFF",
    "sidebar": "#F7F6F3",
    "header_cell": "#FAFAF8",
    "border": "#E2E1DC",
    "border_strong": "#D2D1CB",
    "gridline": "#EFEEEA",
    # Textos
    "text": "#1C1C1A",
    "text_body": "#2B2B29",
    "text_secondary": "#55544F",
    "text_muted": "#6E6D68",
    "pending_ring": "#B9B8B1",
    # Estados
    "accent": "#1F63BA",
    "accent_hover": "#174F96",
    "accent_text": "#FFFFFF",
    "accent_soft": "#E3EDFB",
    "done": "#1F7A4D",
    "done_soft": "#E8F4EC",
    "stale": "#9A6700",
    "stale_soft": "#FDF3DC",
    "na_text": "#9A3B2E",
    "na_bg": "#FBF1EE",
    # Roles de columna
    "role_model_bg": "#DCE8FA",
    "role_model_fg": "#174F96",
    "role_model_tint": "#F1F6FD",
    "role_descr_bg": "#FBE7D8",
    "role_descr_fg": "#8A3D10",
    "role_id_bg": "#E6E5E1",
    "role_id_fg": "#3F3E3A",
    "role_log_bg": "#174F96",
    "role_log_fg": "#FFFFFF",
    # Barras flotantes
    "float_dark_bg": "#26262A",
    "float_dark_fg": "#FFFFFF",
    "float_rows_bg": "#FDF3DC",
    "float_rows_fg": "#5C3D00",
    "selection": "#CFE0F7",
    "toast_bg": "#FDF3DC",
    "toast_fg": "#5C3D00",
}

DARK: dict[str, str] = {
    "bg": "#161615",
    "panel": "#21211F",
    "sidebar": "#1C1C1A",
    "header_cell": "#262624",
    "border": "#383733",
    "border_strong": "#4A4944",
    "gridline": "#2C2B29",
    "text": "#EDECE7",
    "text_body": "#DCDBD5",
    "text_secondary": "#B3B1AA",
    "text_muted": "#929089",
    "pending_ring": "#5E5D58",
    "accent": "#4C8EE0",
    "accent_hover": "#6DA7EC",
    "accent_text": "#FFFFFF",
    "accent_soft": "#1E3150",
    "done": "#45B27C",
    "done_soft": "#183326",
    "stale": "#E3B341",
    "stale_soft": "#3A2E12",
    "na_text": "#F0A898",
    "na_bg": "#3A2420",
    "role_model_bg": "#1E3355",
    "role_model_fg": "#A9C8F5",
    "role_model_tint": "#1B2433",
    "role_descr_bg": "#4A2C17",
    "role_descr_fg": "#F5C29E",
    "role_id_bg": "#34332F",
    "role_id_fg": "#D4D2CB",
    "role_log_bg": "#A9C8F5",
    "role_log_fg": "#10233F",
    "float_dark_bg": "#3A3A3F",
    "float_dark_fg": "#FFFFFF",
    "float_rows_bg": "#3A2E12",
    "float_rows_fg": "#F5DFA8",
    "selection": "#2A4670",
    "toast_bg": "#3A2E12",
    "toast_fg": "#F5DFA8",
}

# Radios y espaciados (px)
METRICS: dict[str, int] = {
    "radius_card": 10,
    "radius_panel": 12,
    "radius_button": 8,
    "radius_field": 6,
    "radius_chip": 4,
    "sidebar_width": 320,
    "font_size": 13,
}

# Series de clusters: orden fijo, nunca cicladas (por eso k máx. = 8).
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
# El color nunca es el único canal: cada cluster lleva además su símbolo.
SYMBOLS = ["circle", "square", "diamond", "triangle-up", "x", "cross", "star", "triangle-down"]
MAX_CLUSTERS = len(SERIES)
DIVERGING = ["#1c5cab", "#6da7ec", "#f0efec", "#ec8a88", "#c43a3a"]
DIVERGING_WHITE_TEXT_ABS_Z = 1.1
MUTED_SERIES = "#898781"


def tokens(dark: bool) -> dict[str, str]:
    return DARK if dark else LIGHT
