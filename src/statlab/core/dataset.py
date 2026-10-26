"""Estado de los datos cargados: roles de columna, log y filas del análisis (sin Qt).

Las filas se identifican por su posición en la tabla tal como se cargó
(0…n−1), que es estable aunque la vista se ordene.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np
import pandas as pd

from statlab import strings_es as S
from statlab.core import fmt


class Rol(StrEnum):
    """Roles que puede tener una columna de la tabla."""

    MODELO = "modelo"
    DESCRIPTIVA = "descriptiva"
    IDENTIFICADOR = "identificador"
    LOG = "log"  # transformación log(1+x); solo como marca de una columna MODELO


@dataclass
class Cambio:
    """Resultado de una operación sobre columnas: qué se aplicó y qué no (y por qué)."""

    aplicadas: list[str] = field(default_factory=list)
    rechazadas: dict[str, str] = field(default_factory=dict)  # columna → motivo

    @property
    def mensaje(self) -> str:
        return "\n".join(self.rechazadas.values())


def is_numeric(series: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)


@dataclass
class Dataset:
    df: pd.DataFrame
    fuente: str = ""
    roles: dict[str, Rol] = field(default_factory=dict)
    log: set[str] = field(default_factory=set)
    solo_filas: set[int] | None = None  # None = todas
    excluidas: set[int] = field(default_factory=set)
    subgrupos: dict[str, list[int]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.df = self.df.reset_index(drop=True)
        self.df.columns = [str(c) for c in self.df.columns]

    # --- Columnas --------------------------------------------------------
    @property
    def columnas(self) -> list[str]:
        return list(self.df.columns)

    @property
    def n_filas(self) -> int:
        return len(self.df)

    def numerica(self, col: str) -> bool:
        return is_numeric(self.df[col])

    def con_rol(self, rol: Rol) -> list[str]:
        """Columnas con ese rol, en el orden de la tabla."""
        if rol == Rol.LOG:
            return [c for c in self.columnas if c in self.log]
        return [c for c in self.columnas if self.roles.get(c) == rol]

    @property
    def identificador(self) -> str | None:
        ids = self.con_rol(Rol.IDENTIFICADOR)
        return ids[0] if ids else None

    def asignar_rol(self, cols: list[str], rol: Rol | None) -> Cambio:
        """Asigna un rol (o lo quita con None). Solo numéricas en el modelo y un único
        identificador; lo que no se puede aplicar vuelve en `rechazadas` con el motivo."""
        cambio = Cambio()
        if rol == Rol.LOG:
            return self.alternar_log(cols)
        if rol == Rol.IDENTIFICADOR and len(cols) > 1:
            for c in cols:
                cambio.rechazadas[c] = S.ROLE_ONE_ID
            return cambio
        for c in cols:
            if rol == Rol.MODELO and not self.numerica(c):
                cambio.rechazadas[c] = S.ROLE_NOT_NUMERIC.format(col=c)
                continue
            if rol == Rol.IDENTIFICADOR:
                for prev in self.con_rol(Rol.IDENTIFICADOR):
                    self.roles.pop(prev, None)
            if rol is None:
                self.roles.pop(c, None)
            else:
                self.roles[c] = rol
            if rol != Rol.MODELO:
                self.log.discard(c)
            cambio.aplicadas.append(c)
        return cambio

    def alternar_log(self, cols: list[str]) -> Cambio:
        """Activa log(1+x) en las columnas (y las pasa al modelo) o, si todas lo
        tenían ya, lo quita."""
        cambio = Cambio()
        validas = []
        for c in cols:
            if not self.numerica(c):
                cambio.rechazadas[c] = S.LOG_NOT_NUMERIC.format(col=c)
            elif (self.df[c] < 0).any():
                cambio.rechazadas[c] = S.LOG_NEGATIVE.format(col=c)
            else:
                validas.append(c)
        if not validas:
            return cambio
        quitar = all(c in self.log for c in validas)
        for c in validas:
            if quitar:
                self.log.discard(c)
            else:
                self.roles[c] = Rol.MODELO
                self.log.add(c)
            cambio.aplicadas.append(c)
        return cambio

    # --- Filas -----------------------------------------------------------
    def filas_activas(self) -> np.ndarray:
        """Posiciones de las filas que entran en el análisis, ordenadas."""
        base = range(self.n_filas) if self.solo_filas is None else self.solo_filas
        return np.array(sorted(set(base) - self.excluidas), dtype=int)

    def fila_activa(self, fila: int) -> bool:
        if fila in self.excluidas:
            return False
        return self.solo_filas is None or fila in self.solo_filas

    @property
    def filtro_filas_activo(self) -> bool:
        return self.solo_filas is not None or bool(self.excluidas)

    def analizar_solo(self, filas: list[int]) -> None:
        self.solo_filas = set(filas)
        self.excluidas -= self.solo_filas

    def excluir(self, filas: list[int]) -> None:
        self.excluidas |= set(filas)

    def usar_todas(self) -> None:
        self.solo_filas = None
        self.excluidas = set()

    def guardar_subgrupo(self, nombre: str, filas: list[int]) -> None:
        nombre = nombre.strip()
        if not nombre:
            raise ValueError(S.SUBGROUP_EMPTY_NAME)
        self.subgrupos[nombre] = sorted(set(filas))

    def resumen_filas(self) -> str:
        n = len(self.filas_activas())
        if not self.filtro_filas_activo:
            return S.ROWS_ALL.format(n=n)
        return S.ROWS_SOME.format(n=n, total=self.n_filas)


def column_summary(series: pd.Series) -> list[tuple[str, str]]:
    """Resumen de una columna para el diálogo «Ver resumen y NA»."""
    n = len(series)
    na = int(series.isna().sum())
    rows = [
        (S.SUM_TYPE, S.SUM_NUMERIC if is_numeric(series) else S.SUM_TEXT),
        (S.SUM_N, f"{n - na} {S.SUM_OF} {n}"),
        (S.SUM_NA, f"{na} ({fmt.pct(100 * na / max(n, 1))})"),
    ]
    present = series.dropna()
    if present.empty:
        return rows
    if is_numeric(series):
        d = min(fmt.column_decimals(present) + 1, fmt.MAX_DECIMALS)
        q1, med, q3 = present.quantile([0.25, 0.5, 0.75])
        rows += [
            (S.SUM_MEAN_SD, f"{fmt.num(present.mean(), d)} ({fmt.num(present.std(), d)})"),
            (S.SUM_MEDIAN_IQR, f"{fmt.num(med, d)} [{fmt.num(q1, d)}–{fmt.num(q3, d)}]"),
            (S.SUM_RANGE, f"{fmt.num(present.min(), d)} – {fmt.num(present.max(), d)}"),
            (S.SUM_DISTINCT, str(present.nunique())),
        ]
        if (present < 0).any():
            rows.append((S.SUM_NEGATIVE, str(int((present < 0).sum()))))
    else:
        counts = present.astype(str).value_counts()
        rows.append((S.SUM_DISTINCT, str(len(counts))))
        for level, count in counts.head(8).items():
            rows.append((f"  {level}", f"{count} ({fmt.pct(100 * count / n, 0)})"))
        if len(counts) > 8:
            rows.append(("  …", S.SUM_MORE_LEVELS.format(n=len(counts) - 8)))
    return rows
