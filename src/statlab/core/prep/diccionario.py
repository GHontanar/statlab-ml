"""Diccionario de variables del proyecto: etiqueta, unidad, límites, códigos de
perdido y etiquetas de las categorías. Lo usan la revisión de calidad, la tabla
y los informes («Hemoglobina (g/dL)» en lugar de `hb_gdl`).

Se importa y exporta como CSV o Excel con una fila por variable:

    variable;etiqueta;unidad;descripcion;minimo;maximo;perdidos;categorias
    hb;Hemoglobina;g/dL;;3;25;999;
    sexo;Sexo;;;;;;1=Hombre|2=Mujer
"""
from __future__ import annotations

import io
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from statlab import strings_es as S
from statlab.core.errors import ErrorUsuario

COLUMNAS = ("variable", "etiqueta", "unidad", "descripcion", "minimo", "maximo", "perdidos", "categorias")


@dataclass
class Entrada:
    etiqueta: str = ""
    unidad: str = ""
    descripcion: str = ""
    minimo: float | None = None
    maximo: float | None = None
    perdidos: list[str] = field(default_factory=list)  # códigos que significan «perdido»
    categorias: dict[str, str] = field(default_factory=dict)  # valor → etiqueta

    @property
    def vacia(self) -> bool:
        return self == Entrada()


@dataclass
class Diccionario:
    entradas: dict[str, Entrada] = field(default_factory=dict)

    def get(self, col: str) -> Entrada | None:
        return self.entradas.get(col)

    def entrada(self, col: str) -> Entrada:
        return self.entradas.setdefault(col, Entrada())

    def etiqueta(self, col: str) -> str:
        """«Hemoglobina (g/dL)»; si no hay nada definido, el nombre de la columna."""
        e = self.entradas.get(col)
        if e is None:
            return col
        nombre = e.etiqueta or col
        return f"{nombre} ({e.unidad})" if e.unidad else nombre

    def to_dict(self) -> dict[str, Any]:
        return {c: asdict(e) for c, e in self.entradas.items() if not e.vacia}

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> Diccionario:
        return cls({c: Entrada(**v) for c, v in (d or {}).items()})

    def renombrar(self, viejo: str, nuevo: str) -> None:
        if viejo in self.entradas:
            self.entradas[nuevo] = self.entradas.pop(viejo)

    # --- Importar / exportar ----------------------------------------------
    def a_tabla(self, columnas: list[str] | None = None) -> pd.DataFrame:
        nombres = columnas if columnas is not None else list(self.entradas)
        filas = []
        for c in nombres:
            e = self.entradas.get(c, Entrada())
            filas.append({
                "variable": c, "etiqueta": e.etiqueta, "unidad": e.unidad, "descripcion": e.descripcion,
                "minimo": e.minimo, "maximo": e.maximo, "perdidos": "|".join(e.perdidos),
                "categorias": "|".join(f"{k}={v}" for k, v in e.categorias.items()),
            })
        return pd.DataFrame(filas, columns=list(COLUMNAS))

    def exportar(self, path: str | Path, columnas: list[str] | None = None) -> Path:
        path = Path(path)
        tabla = self.a_tabla(columnas)
        if path.suffix.lower() in (".xlsx", ".xlsm"):
            tabla.to_excel(path, index=False)
        else:
            tabla.to_csv(path, sep=";", decimal=",", index=False, encoding="utf-8-sig")
        return path

    @classmethod
    def importar(cls, path: str | Path) -> Diccionario:
        from statlab.core import io as sio

        path = Path(path)
        try:
            tabla = sio.read_table(path.name, path.read_bytes())
        except ErrorUsuario:
            raise
        except Exception as e:  # noqa: BLE001 - cualquier fallo de lectura es un archivo no válido
            raise ErrorUsuario(S.DICT_INVALID) from e
        return cls.desde_tabla(tabla)

    @classmethod
    def desde_tabla(cls, tabla: pd.DataFrame) -> Diccionario:
        tabla = tabla.rename(columns={c: str(c).strip().lower() for c in tabla.columns})
        if "variable" not in tabla.columns:
            raise ErrorUsuario(S.DICT_NO_VARIABLE)
        out = cls()
        for _, fila in tabla.iterrows():
            var = _txt(fila.get("variable"))
            if not var:
                continue
            e = Entrada(
                etiqueta=_txt(fila.get("etiqueta")),
                unidad=_txt(fila.get("unidad")),
                descripcion=_txt(fila.get("descripcion")),
                minimo=_float(fila.get("minimo")),
                maximo=_float(fila.get("maximo")),
                perdidos=[p.strip() for p in _txt(fila.get("perdidos")).split("|") if p.strip()],
                categorias=_categorias(_txt(fila.get("categorias"))),
            )
            if not e.vacia:
                out.entradas[var] = e
        return out


def _txt(v: Any) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)) or v is pd.NA:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def _float(v: Any) -> float | None:
    t = _txt(v).replace(",", ".")
    if not t:
        return None
    try:
        return float(t)
    except ValueError as e:
        raise ErrorUsuario(S.DICT_BAD_NUMBER.format(value=t)) from e


def _categorias(texto: str) -> dict[str, str]:
    out = {}
    for parte in texto.split("|"):
        if "=" in parte:
            k, v = parte.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def leer_csv(texto: str) -> Diccionario:  # pragma: no cover - atajo para tests y consola
    return Diccionario.desde_tabla(pd.read_csv(io.StringIO(texto), sep=";", dtype=str))
