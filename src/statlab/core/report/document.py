"""Contenido de un informe como lista de bloques, independiente del formato (PDF o Word)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Titulo:
    texto: str
    nivel: int = 1  # 0 = título del documento


@dataclass
class Parrafo:
    texto: str
    nota: bool = False  # texto secundario (más pequeño, gris)


@dataclass
class Tabla:
    cabeceras: list[str]
    filas: list[list[str]]
    pie: str = ""
    izquierda: set[int] = field(default_factory=lambda: {0})  # columnas alineadas a la izquierda


@dataclass
class Figura:
    png: bytes
    pie: str = ""
    ancho_cm: float = 16.0


@dataclass
class SaltoPagina:
    pass


Bloque = Titulo | Parrafo | Tabla | Figura | SaltoPagina
