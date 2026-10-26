"""Contrato de los módulos de análisis de StatLab.

Cada análisis (k-means hoy; supervivencia, comparaciones… más adelante) es
un `AnalysisModule`. La base aporta los pasos comunes (Datos, Variables y
filas, Exportar) y el módulo intercala los suyos entre ellos. Los cálculos
de `ejecutar` corren en un worker, nunca en el hilo de la interfaz, y
devuelven resultados serializables (para guardarlos en la sesión).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from statlab import strings_es as S
from statlab.core.dataset import Rol

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

Progreso = Callable[[float], None]
Cancelar = Callable[[], bool]
# Resultado de un paso: solo tipos JSON (dict/list/str/números/None).
Resultado = dict[str, Any]

__all__ = ["AnalysisModule", "EstadoPaso", "Exportacion", "Paso", "Rol"]


class EstadoPaso(StrEnum):
    PENDIENTE = "pending"
    ACTIVO = "active"
    HECHO = "done"
    DESACTUALIZADO = "stale"


@dataclass
class Paso:
    """Un paso de la barra lateral.

    `crear_widget` devuelve los controles de parámetros del paso; `resumen`,
    la línea que se muestra cuando está hecho; `validar`, los mensajes que
    impiden continuar (vacío = válido).
    """

    id: str
    titulo: str
    calcula: bool = False  # si True, tiene botón de cálculo y llama a `ejecutar`
    ayuda: str = ""
    crear_widget: Callable[[Any], QWidget | None] = field(default=lambda contexto: None, repr=False)
    resumen: Callable[[Any], str] = field(default=lambda contexto: "", repr=False)
    validar: Callable[[Any], list[str]] = field(default=lambda contexto: [], repr=False)


@dataclass
class Exportacion:
    """Lo que un módulo aporta a los exportes e informes."""

    secciones: list[tuple[str, str]] = field(default_factory=list)  # (título, texto)
    tablas: dict[str, Any] = field(default_factory=dict)  # nombre → DataFrame
    figuras: dict[str, Any] = field(default_factory=dict)  # nombre → Figure de matplotlib


def pasos_comunes_inicio() -> list[Paso]:
    return [
        Paso("datos", S.STEP_DATA),
        Paso("variables", S.STEP_VARIABLES),
    ]


def pasos_comunes_fin() -> list[Paso]:
    return [Paso("exportar", S.STEP_EXPORT)]


class AnalysisModule(ABC):
    id: str
    nombre: str
    icono: str

    @abstractmethod
    def pasos_propios(self) -> list[Paso]:
        """Pasos del módulo, entre «Variables y filas» y «Exportar»."""

    def pasos(self) -> list[Paso]:
        return [*pasos_comunes_inicio(), *self.pasos_propios(), *pasos_comunes_fin()]

    @abstractmethod
    def roles_admitidos(self) -> set[Rol]:
        """Roles de columna que entiende el módulo."""

    @abstractmethod
    def ejecutar(self, paso: str, contexto: Any, progreso: Progreso, cancelar: Cancelar) -> Resultado:
        """Cálculo de un paso. Corre en un worker; debe respetar `cancelar`."""

    @abstractmethod
    def paneles(self, paso: str, resultado: Resultado) -> list[QWidget]:
        """Widgets del panel de resultados para un paso calculado."""

    @abstractmethod
    def exportar(self, resultados: dict[str, Resultado]) -> Exportacion:
        """Secciones, tablas y figuras para los informes."""
