"""Formato numérico en español (coma decimal), común a interfaz, gráficos y exportes."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

MAX_DECIMALS = 4


def num(value: float, decimals: int = 2) -> str:
    """12.5 → "12,50". NA → "NA". El signo menos es el tipográfico (−)."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "NA"
    text = f"{value:.{decimals}f}".replace(".", ",")
    return text.replace("-", "−")


def pct(value: float, decimals: int = 1) -> str:
    return f"{num(value, decimals)} %"


def column_decimals(series: pd.Series, max_decimals: int = MAX_DECIMALS) -> int:
    """Decimales necesarios para mostrar todos los valores de una columna sin perder
    precisión (hasta `max_decimals`). Así una columna se lee con un formato uniforme."""
    values = pd.to_numeric(series, errors="coerce").dropna().to_numpy(dtype=float)
    if values.size == 0:
        return 0
    values = values[np.isfinite(values)]
    for d in range(max_decimals + 1):
        if np.allclose(np.round(values, d), values, rtol=0, atol=10 ** -(d + 6)):
            return d
    return max_decimals
