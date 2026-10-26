"""Controlador de la sesión: único dueño del `EstadoSesion` y emisor de los cambios.

La tabla y la barra lateral no se hablan entre sí: llaman a este objeto y
escuchan sus señales. Los cálculos de los pasos corren en un worker sobre una
copia del estado; si las entradas cambian mientras tanto, el resultado viejo
se descarta (cada lanzamiento lleva un número de turno).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal

from statlab import strings_es as S
from statlab.core import io as sio
from statlab.core.dataset import Cambio, Dataset, Rol
from statlab.core.errors import ErrorUsuario
from statlab.core.estado import EstadoSesion
from statlab.core.flow import EstadoPaso
from statlab.modules.base import AnalysisModule
from statlab.workers import Tarea, lanzar

PREVIEW_DELAY_MS = 150


class SessionController(QObject):
    dataset_changed = Signal()  # datos nuevos
    roles_changed = Signal()
    rows_changed = Signal()
    flow_changed = Signal()  # estados de los pasos
    step_updated = Signal(str)  # parámetros o resultado de un paso
    step_running = Signal(str, bool)
    step_progress = Signal(str, float)
    message = Signal(str)  # aviso para el usuario (rol rechazado, subgrupo guardado…)

    def __init__(self, module: AnalysisModule, parent: QObject | None = None):
        super().__init__(parent)
        self.module = module
        self.estado: EstadoSesion = module.crear_estado()
        self._tareas: dict[str, Tarea] = {}
        self._vivas: set[Tarea] = set()  # incluye las canceladas que aún no han terminado
        self._turnos: dict[str, int] = {}
        self._timers: dict[str, QTimer] = {}

    @property
    def dataset(self) -> Dataset | None:
        return self.estado.dataset

    @property
    def flujo(self):
        return self.estado.flujo

    def running(self, paso: str) -> bool:
        """Calculando o a punto de calcular (vista previa programada)."""
        timer = self._timers.get(paso)
        return paso in self._tareas or (timer is not None and timer.isActive())

    # --- Carga ----------------------------------------------------------
    def load_path(self, path: str | Path) -> None:
        """Lanza ErrorUsuario con un mensaje legible si no se puede leer."""
        path = Path(path)
        try:
            df = sio.read_path(path)
        except ErrorUsuario:
            raise
        except Exception as e:  # pandas/openpyxl lanzan muchos tipos distintos
            raise ErrorUsuario(S.READ_ERROR_GENERIC) from e
        self._set(Dataset(df, fuente=path.name))

    def load_example(self) -> None:
        self._set(Dataset(sio.read_example(), fuente=sio.EXAMPLE_NAME))

    def _set(self, dataset: Dataset) -> None:
        for paso in list(self._tareas):
            self.cancel(paso)
        self.estado = self.module.crear_estado()
        self.estado.dataset = dataset
        self.flujo.completar("datos")
        self.dataset_changed.emit()
        self.flow_changed.emit()

    # --- Columnas -------------------------------------------------------
    def set_role(self, cols: list[str], rol: Rol | None) -> Cambio:
        return self._after_roles(self.dataset.asignar_rol(cols, rol))

    def toggle_log(self, cols: list[str]) -> Cambio:
        return self._after_roles(self.dataset.alternar_log(cols))

    def _after_roles(self, cambio: Cambio) -> Cambio:
        if cambio.aplicadas:
            self.roles_changed.emit()
            self.inputs_changed("variables")
        if cambio.rechazadas:
            self.message.emit(cambio.mensaje)
        return cambio

    # --- Filas ----------------------------------------------------------
    def analyze_only(self, rows: list[int]) -> None:
        self.dataset.analizar_solo(rows)
        self._after_rows()

    def exclude(self, rows: list[int]) -> None:
        self.dataset.excluir(rows)
        self._after_rows()

    def use_all_rows(self) -> None:
        self.dataset.usar_todas()
        self._after_rows()

    def _after_rows(self) -> None:
        self.rows_changed.emit()
        self.inputs_changed("variables")

    def save_subgroup(self, name: str, rows: list[int]) -> None:
        self.dataset.guardar_subgrupo(name, rows)
        self.rows_changed.emit()
        self.message.emit(S.SUBGROUP_SAVED.format(name=name.strip(), n=len(set(rows))))

    # --- Parámetros y flujo --------------------------------------------
    def params(self, paso: str) -> dict[str, Any]:
        return self.estado.params(paso)

    def set_params(self, paso: str, **valores: Any) -> None:
        params = self.estado.params(paso)
        if all(params.get(k) == v for k, v in valores.items()):
            return
        params.update(valores)
        self.step_updated.emit(paso)
        self.inputs_changed(paso)

    def inputs_changed(self, paso: str) -> None:
        """Ha cambiado algo de `paso`: los posteriores hechos quedan desactualizados y
        las vistas previas abiertas se recalculan."""
        flujo = self.flujo
        flujo.invalidar_despues(paso)
        if flujo[paso] == EstadoPaso.HECHO and self.validate(paso):
            flujo.abrir(paso)
        for p in [paso, *flujo.posteriores(paso)]:
            if flujo[p] == EstadoPaso.ACTIVO and self.module.paso(p).automatico:
                self._schedule(p)
        self.flow_changed.emit()

    def validate(self, paso: str) -> list[str]:
        if self.estado.dataset is None:
            return [S.STEP_DATA_HINT]
        return self.module.paso(paso).validar(self.estado)

    def complete(self, paso: str) -> bool:
        errores = self.validate(paso)
        if errores or self.running(paso):
            if errores:
                self.message.emit("\n".join(errores))
            return False
        siguiente = self.flujo.completar(paso)
        if siguiente and self.module.paso(siguiente).automatico and siguiente not in self.estado.resultados:
            self._schedule(siguiente)
        self.flow_changed.emit()
        return True

    def reopen(self, paso: str) -> None:
        estaba = self.flujo[paso]
        self.flujo.abrir(paso)
        sin_resultado = paso not in self.estado.resultados
        if self.module.paso(paso).automatico and (sin_resultado or estaba == EstadoPaso.DESACTUALIZADO):
            self._schedule(paso)
        self.flow_changed.emit()

    def recalculate(self, paso: str) -> None:
        """Repite un paso desactualizado con las entradas actuales."""
        pendiente = next((p for p in self.flujo.anteriores(paso) if self.flujo[p] != EstadoPaso.HECHO), None)
        if pendiente:
            self.message.emit(S.STALE_BLOCKED.format(step=self.module.paso(pendiente).titulo))
            return
        self.run(paso, on_success=lambda: self._recalculated(paso))

    def _recalculated(self, paso: str) -> None:
        if self.flujo[paso] == EstadoPaso.DESACTUALIZADO and not self.validate(paso):
            self.flujo.completar(paso)
            self.flow_changed.emit()

    # --- Cálculos -------------------------------------------------------
    def _schedule(self, paso: str) -> None:
        timer = self._timers.get(paso)
        if timer is None:
            timer = self._timers[paso] = QTimer(self, singleShot=True, interval=PREVIEW_DELAY_MS)
            timer.timeout.connect(lambda p=paso: self.run(p))
        timer.start()
        self.step_running.emit(paso, True)

    def run(self, paso: str, on_success=None) -> None:
        self.cancel(paso)
        turno = self._turnos.get(paso, 0) + 1
        self._turnos[paso] = turno
        copia = self.estado.snapshot()
        tarea = Tarea(lambda progreso, cancelar: self.module.ejecutar(paso, copia, progreso, cancelar))
        s = tarea.senales
        s.progreso.connect(lambda f: self._if_current(paso, turno) and self.step_progress.emit(paso, f))
        s.terminado.connect(lambda r: self._done(paso, turno, r, on_success))
        s.fallido.connect(lambda msg, esperado: self._failed(paso, turno, msg, esperado))
        s.cancelado.connect(lambda: self._finished(paso, turno))
        for senal in (s.terminado, s.fallido, s.cancelado):
            senal.connect(lambda *_, t=tarea: self._vivas.discard(t))
        self._tareas[paso] = tarea
        self._vivas.add(tarea)
        self.step_running.emit(paso, True)
        lanzar(tarea)

    def cancel(self, paso: str) -> None:
        timer = self._timers.get(paso)
        if timer is not None and timer.isActive():
            timer.stop()
            self.step_running.emit(paso, False)
        tarea = self._tareas.pop(paso, None)
        if tarea is not None:
            tarea.cancelar()
            self._turnos[paso] = self._turnos.get(paso, 0) + 1  # su resultado ya no vale
            self.step_running.emit(paso, False)

    def _if_current(self, paso: str, turno: int) -> bool:
        return self._turnos.get(paso) == turno

    def _finished(self, paso: str, turno: int) -> bool:
        if not self._if_current(paso, turno):
            return False
        self._tareas.pop(paso, None)
        self.step_running.emit(paso, False)
        return True

    def _done(self, paso: str, turno: int, resultado: dict, on_success) -> None:
        if not self._finished(paso, turno):
            return
        self.estado.resultados[paso] = resultado
        self.step_updated.emit(paso)
        self.flow_changed.emit()
        if on_success:
            on_success()

    def _failed(self, paso: str, turno: int, mensaje: str, esperado: bool) -> None:
        if not self._finished(paso, turno):
            return
        titulo = self.module.paso(paso).titulo
        self.estado.resultados[paso] = {"error": mensaje if esperado else S.CALC_ERROR_DETAIL.format(step=titulo)}
        self.step_updated.emit(paso)
        self.flow_changed.emit()
