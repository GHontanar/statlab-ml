"""Preparación de una sesión: archivo original + opciones de lectura + receta +
diccionario → Dataset de análisis.

El archivo original se guarda tal cual (sus bytes) para poder cambiar las
opciones de lectura o la receta en cualquier momento sin volver a abrirlo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from statlab.core import io as sio
from statlab.core.dataset import Dataset, Rol, is_numeric
from statlab.core.prep.diccionario import Diccionario
from statlab.core.prep.receta import Preparado, Receta, aplicar


@dataclass
class Preparacion:
    nombre: str
    raw: bytes
    opciones: sio.OpcionesLectura = field(default_factory=sio.OpcionesLectura)
    receta: Receta = field(default_factory=Receta)
    diccionario: Diccionario = field(default_factory=Diccionario)
    _lectura: sio.Lectura | None = field(default=None, repr=False, compare=False)
    _clave: dict | None = field(default=None, repr=False, compare=False)

    @classmethod
    def desde_archivo(cls, nombre: str, raw: bytes, opciones: sio.OpcionesLectura | None = None) -> Preparacion:
        prep = cls(nombre=nombre, raw=raw, opciones=opciones or sio.OpcionesLectura())
        prep.leer()  # valida el archivo y rellena lo detectado
        return prep

    @classmethod
    def desde_dataframe(cls, nombre: str, df: pd.DataFrame) -> Preparacion:
        """Para datos que no vienen de un archivo propio (sesiones antiguas): el
        original es el propio CSV, ya leído tal cual."""
        prep = cls(nombre=nombre, raw=df.to_csv(index=False).encode("utf-8"))
        prep.opciones = sio.OpcionesLectura(fila_cabecera=1, filas_cabecera=1)
        prep._lectura = sio.Lectura(df=df.copy(), opciones=prep.opciones)
        prep._clave = prep.opciones.to_dict()
        return prep

    def leer(self) -> sio.Lectura:
        """Datos leídos con las opciones actuales (en caché mientras no cambien)."""
        clave = self.opciones.to_dict()
        if self._lectura is None or self._clave != clave:
            self._lectura = sio.leer(self.nombre, self.raw, self.opciones)
            self.opciones = self._lectura.opciones
            self._clave = self.opciones.to_dict()
        return self._lectura

    @property
    def leidos(self) -> pd.DataFrame:
        return self.leer().df

    def aplicar(self) -> Preparado:
        return aplicar(self.leidos, self.receta)

    def dataset(self, anterior: Dataset | None = None) -> tuple[Dataset, Preparado]:
        """Dataset de análisis. Conserva de `anterior` los roles de las columnas que
        siguen existiendo y, si el número de filas no ha cambiado, la selección de filas."""
        prep = self.aplicar()
        ds = Dataset(prep.df, fuente=self.nombre)
        ds.excluidas_receta = dict(prep.excluidas)
        if anterior is not None:
            for c, r in anterior.roles.items():
                if c in ds.columnas and (r != Rol.MODELO or is_numeric(ds.df[c])):
                    ds.roles[c] = r
            ds.log = {c for c in anterior.log if ds.roles.get(c) == Rol.MODELO}
            if anterior.n_filas == ds.n_filas:
                ds.solo_filas = None if anterior.solo_filas is None else set(anterior.solo_filas)
                ds.excluidas = set(anterior.excluidas)
                ds.subgrupos = {k: list(v) for k, v in anterior.subgrupos.items()}
        return ds, prep

    def to_dict(self) -> dict[str, Any]:
        return {
            "nombre": self.nombre,
            "opciones": self.opciones.to_dict(),
            "receta": self.receta.to_dict(),
            "diccionario": self.diccionario.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any], raw: bytes) -> Preparacion:
        return cls(
            nombre=d["nombre"],
            raw=raw,
            opciones=sio.OpcionesLectura.from_dict(d.get("opciones")),
            receta=Receta.from_dict(d.get("receta")),
            diccionario=Diccionario.from_dict(d.get("diccionario")),
        )


def de_ejemplo() -> Preparacion:
    return Preparacion.desde_archivo(sio.EXAMPLE_NAME, sio.example_bytes())
