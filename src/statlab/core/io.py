"""Lectura de datos tabulares y detección de formato (sin Qt).

CSV/TSV/Excel; detecta el separador y la coma decimal (formato español)
y reconoce los tokens habituales de valor perdido. En Excel, además: elegir la
hoja, cabecera que no está en la primera fila, cabeceras de dos filas (celdas
combinadas) y filas de totales o notas al final.
"""
from __future__ import annotations

import io
import re
from dataclasses import asdict, dataclass, field
from importlib import resources
from pathlib import Path

import pandas as pd

from statlab import strings_es as S
from statlab.core.errors import ErrorUsuario

EXCEL_SUFFIXES = (".xlsx", ".xls", ".xlsm")
NA_TOKENS = {"", "na", "nan", "n/a", "nd", "-", "."}
EXAMPLE_NAME = "datos_ejemplo.csv"


@dataclass
class OpcionesLectura:
    """Cómo se lee el archivo. None = detectar automáticamente."""

    hoja: str | None = None
    fila_cabecera: int | None = None  # 1 = primera fila del archivo
    filas_cabecera: int | None = None  # 1 o 2 (cabecera de dos filas)
    quitar_final: bool = True  # filas de totales o notas al final

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict | None) -> OpcionesLectura:
        return cls(**(d or {}))


@dataclass
class Lectura:
    df: pd.DataFrame
    opciones: OpcionesLectura  # con lo detectado ya rellenado
    hojas: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


def es_excel(name: str) -> bool:
    return name.lower().endswith(EXCEL_SUFFIXES)


def hojas_excel(raw: bytes) -> list[str]:
    with pd.ExcelFile(io.BytesIO(raw)) as x:
        return [str(h) for h in x.sheet_names]


def leer(name: str, raw: bytes, opciones: OpcionesLectura | None = None) -> Lectura:
    """Lee el archivo con las opciones dadas (o detectándolas) y devuelve también lo detectado."""
    opciones = OpcionesLectura(**asdict(opciones or OpcionesLectura()))
    if name.lower().endswith(".xls"):
        try:
            hojas_excel(raw)
        except ImportError as e:  # el formato antiguo necesita xlrd, que no incluimos
            raise ErrorUsuario(S.XLS_UNSUPPORTED) from e
    if es_excel(name):
        lectura = _leer_excel(raw, opciones)
    else:
        df = _leer_csv(raw, opciones)
        if df.shape[1] < 2 or df.empty:
            raise ErrorUsuario(S.READ_TOO_SMALL)
        lectura = Lectura(df=coerce_decimal_commas(df), opciones=opciones)
    if lectura.df.shape[1] < 2 or lectura.df.empty:
        raise ErrorUsuario(S.READ_TOO_SMALL)
    return lectura


def read_table(name: str, raw: bytes) -> pd.DataFrame:
    """Lee CSV/TSV/Excel. Detecta separador y coma decimal (formato español)."""
    return leer(name, raw).df


def _leer_csv(raw: bytes, opciones: OpcionesLectura) -> pd.DataFrame:
    saltar = (opciones.fila_cabecera or 1) - 1
    opciones.fila_cabecera = saltar + 1
    opciones.filas_cabecera = 1
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(io.BytesIO(raw), sep=None, engine="python", encoding=enc, skiprows=saltar)
        except UnicodeDecodeError:
            continue
    raise ErrorUsuario(S.READ_ENCODING)


_FINAL = re.compile(r"^\s*(total(es)?|suma|media|promedio|notas?|nota:|fuente|\*)", re.IGNORECASE)


def _es_texto(v) -> bool:
    if not isinstance(v, str):
        return False
    t = v.strip().replace(",", ".")
    try:
        float(t)
        return False
    except ValueError:
        return bool(t)


def _detectar_cabecera(grid: pd.DataFrame) -> tuple[int, int]:
    """(fila de la cabecera, 0-based; número de filas de cabecera)."""
    llenas = grid.notna().sum(axis=1).to_numpy()
    maximo = max(int(llenas.max()), 1)
    textos = grid.apply(lambda fila: sum(_es_texto(v) for v in fila), axis=1).to_numpy()
    limite = min(len(grid), 30)
    fila = 0
    for r in range(limite):
        if llenas[r] >= max(2, 0.5 * maximo) and textos[r] == llenas[r] and r + 1 < len(grid):
            fila = r
            break
    filas = 1
    r2 = fila + 1
    if (r2 + 1 < len(grid) and llenas[fila] < llenas[r2] and textos[r2] == llenas[r2]
            and llenas[r2] >= max(2, 0.5 * maximo) and textos[r2 + 1] < llenas[r2 + 1]):
        filas = 2  # fila superior con celdas combinadas («Analítica» sobre «Hb», «VCM»…)
    return fila, filas


def _nombres(grid: pd.DataFrame, fila: int, filas: int) -> list[str]:
    arriba = grid.iloc[fila].copy()
    if filas == 2:
        arriba = arriba.ffill()  # una celda combinada solo tiene valor en la primera columna
        abajo = grid.iloc[fila + 1]
        nombres = []
        for a, b in zip(arriba, abajo, strict=True):
            partes = [str(x).strip() for x in (a, b) if isinstance(x, str) and x.strip()]
            nombres.append(" ".join(dict.fromkeys(partes)))
    else:
        nombres = ["" if pd.isna(v) else str(v).strip() for v in arriba]
    out, vistos = [], {}
    for i, n in enumerate(nombres):
        n = n or f"columna_{i + 1}"
        if n in vistos:
            vistos[n] += 1
            n = f"{n}_{vistos[n]}"
        else:
            vistos[n] = 1
        out.append(n)
    return out


def _leer_excel(raw: bytes, opciones: OpcionesLectura) -> Lectura:
    hojas = hojas_excel(raw)
    if opciones.hoja in hojas:
        return _leer_hoja(raw, opciones, hojas)
    # Sin hoja elegida: la primera que tenga una tabla (la primera suele ser de instrucciones)
    error: ErrorUsuario | None = None
    for hoja in hojas:
        intento = OpcionesLectura(**{**asdict(opciones), "hoja": hoja})
        try:
            lectura = _leer_hoja(raw, intento, hojas)
        except ErrorUsuario as e:
            error = error or e
            continue
        if lectura.df.shape[1] >= 2 and not lectura.df.empty:
            if hoja != hojas[0]:
                lectura.avisos.insert(0, S.READ_OTHER_SHEET.format(sheet=hoja))
            return lectura
    raise error or ErrorUsuario(S.READ_TOO_SMALL)


def _leer_hoja(raw: bytes, opciones: OpcionesLectura, hojas: list[str]) -> Lectura:
    hoja = opciones.hoja
    grid = pd.read_excel(io.BytesIO(raw), sheet_name=hoja, header=None, dtype=object)
    grid = grid.dropna(how="all").dropna(axis=1, how="all")
    original = grid.index.to_numpy()  # fila real del archivo (0-based), para informar y para elegirla a mano
    grid = grid.reset_index(drop=True)
    if grid.empty:
        raise ErrorUsuario(S.READ_TOO_SMALL)
    avisos = []
    fila, filas = _detectar_cabecera(grid)
    if opciones.fila_cabecera is not None:
        fila = int((original < opciones.fila_cabecera - 1).sum())  # primera fila no vacía desde la pedida
    if opciones.filas_cabecera is not None:
        filas = opciones.filas_cabecera
    fila = max(0, min(fila, len(grid) - 1))
    opciones.fila_cabecera, opciones.filas_cabecera = int(original[fila]) + 1, filas
    if original[fila] > 0:
        avisos.append(S.READ_HEADER_ROW.format(row=opciones.fila_cabecera))
    if filas == 2:
        avisos.append(S.READ_TWO_HEADERS)
    datos = grid.iloc[fila + filas:].reset_index(drop=True)
    datos.columns = _nombres(grid, fila, filas)
    if opciones.quitar_final:
        quitadas = 0
        ancho = datos.notna().sum(axis=1)
        tipico = float(ancho.median()) if len(ancho) else 0
        while len(datos) > 1 and quitadas < 10:
            ultima = datos.iloc[-1]
            primero = next((v for v in ultima if not pd.isna(v)), None)
            if ancho.iloc[-1] <= max(1, 0.34 * tipico) or (isinstance(primero, str) and _FINAL.match(primero)):
                datos, ancho = datos.iloc[:-1], ancho.iloc[:-1]
                quitadas += 1
            else:
                break
        if quitadas:
            avisos.append(S.READ_TRAILING_1 if quitadas == 1 else S.READ_TRAILING.format(n=quitadas))
    datos = datos.dropna(how="all").reset_index(drop=True).infer_objects()
    for c in datos.columns:  # columnas mixtas (número y texto) quedan como texto para revisarlas
        if datos[c].dtype == object:
            vals = datos[c].dropna()
            if vals.map(lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)).all() and len(vals):
                datos[c] = pd.to_numeric(datos[c])
            elif vals.map(lambda v: hasattr(v, "year")).all() and len(vals):
                datos[c] = pd.to_datetime(datos[c])
            else:
                datos[c] = datos[c].map(lambda v: v if pd.isna(v) else str(v))
    return Lectura(df=coerce_decimal_commas(datos), opciones=opciones, hojas=hojas, avisos=avisos)


def read_path(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    return read_table(path.name, path.read_bytes())


def leer_path(path: str | Path, opciones: OpcionesLectura | None = None) -> Lectura:
    path = Path(path)
    return leer(path.name, path.read_bytes(), opciones)


def coerce_decimal_commas(df: pd.DataFrame, threshold: float = 1.0) -> pd.DataFrame:
    """Convierte a numéricas las columnas de texto con coma decimal ("3,2").

    Solo si todos los valores son números: una columna con «<0,5» o «12 mg» se deja
    como texto para que la revisión de calidad lo proponga y avise de lo que no se
    puede leer (nada se convierte en perdido sin decirlo)."""
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
