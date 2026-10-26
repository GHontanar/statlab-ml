"""Cálculos en segundo plano: la interfaz nunca se bloquea.

`Tarea` envuelve una función `fn(progreso, cancelar) -> resultado` y la ejecuta
en el `QThreadPool` global. Las señales llegan al hilo de la interfaz.
"""
from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from statlab.core.errors import ErrorUsuario
from statlab.core.kmeans import Cancelled

log = logging.getLogger(__name__)

Funcion = Callable[[Callable[[float], None], Callable[[], bool]], Any]


class _Senales(QObject):
    progreso = Signal(float)
    terminado = Signal(object)
    fallido = Signal(str, bool)  # mensaje, es_error_de_usuario (texto pensado para mostrarse)
    cancelado = Signal()


class Tarea(QRunnable):
    def __init__(self, fn: Funcion):
        super().__init__()
        self.fn = fn
        self.senales = _Senales()
        self._cancelar = threading.Event()
        self.setAutoDelete(False)  # la referencia la guarda quien la lanza

    def cancelar(self) -> None:
        self._cancelar.set()

    @property
    def cancelada(self) -> bool:
        return self._cancelar.is_set()

    def run(self) -> None:
        try:
            resultado = self.fn(self._progreso, self._cancelar.is_set)
        except Cancelled:
            self._emitir(self.senales.cancelado)
        except ErrorUsuario as e:
            self._emitir(self.senales.fallido, str(e), True)
        except _InterfazCerrada:
            pass
        except Exception as e:  # noqa: BLE001 - se informa sin traza al usuario
            log.exception("Error en un cálculo en segundo plano")
            self._emitir(self.senales.fallido, repr(e), False)
        else:
            if self.cancelada:
                self._emitir(self.senales.cancelado)
            else:
                self._emitir(self.senales.terminado, resultado)

    def _progreso(self, fraccion: float) -> None:
        try:
            self.senales.progreso.emit(fraccion)
        except RuntimeError as e:  # la ventana se ha cerrado durante el cálculo
            raise _InterfazCerrada from e

    @staticmethod
    def _emitir(senal, *args) -> None:
        try:
            senal.emit(*args)
        except RuntimeError:
            pass  # la ventana se ha cerrado: nadie espera ya el resultado


class _InterfazCerrada(Exception):
    pass


def cancelar_todo(tareas, espera_ms: int = 5000) -> None:
    """Cancela las tareas y espera a que el pool se vacíe (al cerrar la aplicación)."""
    for tarea in list(tareas):
        tarea.cancelar()
    QThreadPool.globalInstance().waitForDone(espera_ms)


def lanzar(tarea: Tarea) -> Tarea:
    QThreadPool.globalInstance().start(tarea)
    return tarea
