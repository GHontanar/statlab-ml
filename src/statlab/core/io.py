"""Lectura de datos tabulares y detección de formato (sin Qt).

CSV/TSV/Excel; detecta el separador y la coma decimal (formato español)
y reconoce los tokens habituales de valor perdido.
"""
from __future__ import annotations

import io
from importlib import resources
from pathlib import Path

import pandas as pd

EXCEL_SUFFIXES = (".xlsx", ".xls", ".xlsm")
NA_TOKENS = {"", "na", "nan", "n/a", "nd", "-", "."}
EXAMPLE_NAME = "datos_ejemplo.csv"


def read_table(name: str, raw: bytes) -> pd.DataFrame:
    """Lee CSV/TSV/Excel. Detecta separador y coma decimal (formato español)."""
    lower = name.lower()
    if lower.endswith(EXCEL_SUFFIXES):
        df = pd.read_excel(io.BytesIO(raw))
    else:
        df = None
        for enc in ("utf-8-sig", "latin-1"):
            try:
                df = pd.read_csv(io.BytesIO(raw), sep=None, engine="python", encoding=enc)
                break
            except UnicodeDecodeError:
                continue
        if df is None:
            raise ValueError("No se pudo leer el archivo (codificación desconocida).")
    return coerce_decimal_commas(df)


def read_path(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    return read_table(path.name, path.read_bytes())


def coerce_decimal_commas(df: pd.DataFrame, threshold: float = 0.9) -> pd.DataFrame:
    """Convierte a numéricas las columnas de texto con coma decimal ("3,2")."""
    out = df.copy()
    for col in out.columns:
        s = out[col]
        if pd.api.types.is_numeric_dtype(s) or pd.api.types.is_datetime64_any_dtype(s):
            continue
        txt = s.astype("string").str.strip()
        txt = txt.mask(txt.str.lower().isin(NA_TOKENS))
        present = txt.dropna()
        if present.empty:
            continue
        num = pd.to_numeric(txt.str.replace(",", ".", regex=False), errors="coerce")
        if num[present.index].notna().mean() >= threshold:
            out[col] = num.astype(float)
    return out


def example_bytes() -> bytes:
    """Datos de ejemplo integrados (240 filas sintéticas)."""
    return resources.files("statlab.data").joinpath(EXAMPLE_NAME).read_bytes()


def read_example() -> pd.DataFrame:
    return read_table(EXAMPLE_NAME, example_bytes())
