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
            resultado = self.fn(self.senales.progreso.emit, self._cancelar.is_set)
        except Cancelled:
            self.senales.cancelado.emit()
        except ErrorUsuario as e:
            self.senales.fallido.emit(str(e), True)
        except Exception as e:  # noqa: BLE001 - se informa sin traza al usuario
            log.exception("Error en un cálculo en segundo plano")
            self.senales.fallido.emit(repr(e), False)
        else:
            if self.cancelada:
                self.senales.cancelado.emit()
            else:
                self.senales.terminado.emit(resultado)


def lanzar(tarea: Tarea) -> Tarea:
    QThreadPool.globalInstance().start(tarea)
    return tarea
