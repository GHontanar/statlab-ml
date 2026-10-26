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
from typing import TYPE_CHECKING, Any

from statlab import strings_es as S
from statlab.core.dataset import Rol, validar_variables
from statlab.core.estado import EstadoSesion
from statlab.core.flow import EstadoPaso, FlujoPasos

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

Progreso = Callable[[float], None]
Cancelar = Callable[[], bool]
# Resultado de un paso: tipos JSON; las claves «_…» son objetos de trabajo no serializables.
Resultado = dict[str, Any]

__all__ = ["AnalysisModule", "EstadoPaso", "Exportacion", "Paso", "Rol"]


def _sin_widget(controlador: Any) -> QWidget | None:
    return None


def _sin_resumen(estado: EstadoSesion) -> str:
    return ""


def _valido(estado: EstadoSesion) -> list[str]:
    return []


@dataclass
class Paso:
    """Un paso de la barra lateral.

    - `crear_widget(controlador)`: controles del paso (se muestran cuando está activo).
    - `resumen(estado)`: texto breve cuando está hecho o desactualizado.
    - `validar(estado)`: mensajes que impiden darlo por hecho (vacío = válido).
    - `calcula`: tiene un resultado que produce `AnalysisModule.ejecutar` en un worker.
    - `automatico`: el cálculo se repite solo al cambiar entradas (vista previa rápida);
      si no, lo lanza el botón.
    - `boton`: texto del botón principal; vacío si el paso se completa de otro modo.
    """

    id: str
    titulo: str
    calcula: bool = False
    automatico: bool = False
    boton: str = ""
    parametros: dict[str, Any] = field(default_factory=dict)
    crear_widget: Callable[[Any], QWidget | None] = field(default=_sin_widget, repr=False)
    resumen: Callable[[EstadoSesion], str] = field(default=_sin_resumen, repr=False)
    validar: Callable[[EstadoSesion], list[str]] = field(default=_valido, repr=False)


@dataclass
class Exportacion:
    """Lo que un módulo aporta a los exportes e informes."""

    secciones: list[tuple[str, str]] = field(default_factory=list)  # (título, texto)
    tablas: dict[str, Any] = field(default_factory=dict)  # nombre → DataFrame
    figuras: dict[str, Any] = field(default_factory=dict)  # nombre → Figure de matplotlib


def _resumen_datos(estado: EstadoSesion) -> str:
    ds = estado.dataset
    if ds is None:
        return S.STEP_DATA_HINT
    return S.DATA_SUMMARY.format(name=ds.fuente, rows=ds.n_filas, cols=len(ds.columnas))


def _validar_variables(estado: EstadoSesion) -> list[str]:
    return validar_variables(estado.dataset) if estado.dataset is not None else [S.STEP_DATA_HINT]


def _widget_variables(controlador: Any) -> QWidget:
    from statlab.ui.sidebar.variables import VariablesSummary

    return VariablesSummary(controlador)


def pasos_comunes_inicio() -> list[Paso]:
    return [
        Paso("datos", S.STEP_DATA, resumen=_resumen_datos),
        Paso(
            "variables",
            S.STEP_VARIABLES,
            boton=S.CONTINUE,
            crear_widget=_widget_variables,
            validar=_validar_variables,
        ),
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

    def paso(self, paso_id: str) -> Paso:
        return next(p for p in self.pasos() if p.id == paso_id)

    def crear_estado(self) -> EstadoSesion:
        """Estado vacío de una sesión: flujo al inicio y parámetros por defecto."""
        pasos = self.pasos()
        return EstadoSesion(
            flujo=FlujoPasos([p.id for p in pasos]),
            parametros={p.id: dict(p.parametros) for p in pasos},
        )

    @abstractmethod
    def roles_admitidos(self) -> set[Rol]:
        """Roles de columna que entiende el módulo."""

    @abstractmethod
    def ejecutar(self, paso: str, estado: EstadoSesion, progreso: Progreso, cancelar: Cancelar) -> Resultado:
        """Cálculo de un paso sobre una copia del estado. Corre en un worker y debe
        respetar `cancelar`. Un ErrorUsuario lleva un mensaje para mostrar tal cual."""

    @abstractmethod
    def paneles(self, paso: str, resultado: Resultado) -> list[QWidget]:
        """Widgets del panel de resultados para un paso calculado."""

    @abstractmethod
    def exportar(self, resultados: dict[str, Resultado]) -> Exportacion:
        """Secciones, tablas y figuras para los informes."""
