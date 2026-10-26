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
from statlab.core import session as ses
from statlab.core.dataset import Cambio, Dataset, Rol
from statlab.core.errors import ErrorUsuario
from statlab.core.estado import EstadoSesion
from statlab.core.flow import EstadoPaso
from statlab.modules.base import AnalysisModule
from statlab.workers import Tarea, cancelar_todo, lanzar

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
    dirty_changed = Signal(bool)  # hay cambios sin guardar
    focus_requested = Signal(str)  # llevar la vista a un paso de la barra lateral
    rows_selection_requested = Signal(list)  # seleccionar estas filas en la tabla (desde un gráfico)

    def __init__(self, module: AnalysisModule, parent: QObject | None = None):
        super().__init__(parent)
        self.module = module
        self.estado: EstadoSesion = module.crear_estado()
        self._tareas: dict[str, Tarea] = {}
        self._vivas: set[Tarea] = set()  # incluye las canceladas que aún no han terminado
        # Pasos hechos que se han reabierto para editarlos → ¿se ha cambiado algo desde entonces?
        self._reabiertos: dict[str, bool] = {}
        self.session_path: Path | None = None
        self.dirty = False
        self._restoring = False
        for signal in (self.dataset_changed, self.roles_changed, self.rows_changed, self.flow_changed):
            signal.connect(self._mark_dirty)
        self.step_updated.connect(self._mark_dirty)
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
        self._reabiertos.clear()
        self.session_path = None
        self.estado.dataset = dataset
        self.flujo.completar("datos")
        self.dataset_changed.emit()
        self.flow_changed.emit()

    # --- Sesiones -------------------------------------------------------
    def _mark_dirty(self, *_args) -> None:
        if not self._restoring and self.estado.dataset is not None:
            self._set_dirty(True)

    def _set_dirty(self, dirty: bool) -> None:
        if dirty != self.dirty:
            self.dirty = dirty
            self.dirty_changed.emit(dirty)

    def save_session(self, path: str | Path) -> Path:
        """Guarda todo en un archivo .statlab. Lanza ErrorUsuario/OSError si no se puede."""
        guardado = ses.guardar(path, self.estado, self.module.id)
        self.session_path = guardado
        self._set_dirty(False)
        self.message.emit(S.SESSION_SAVED.format(name=guardado.name))
        return guardado

    def open_session(self, path: str | Path) -> None:
        """Restaura una sesión sin recalcular nada."""
        estado = ses.abrir(path, self.module.crear_estado, self.module.id)
        for paso in list(self._tareas):
            self.cancel(paso)
        self._restoring = True
        try:
            self.estado = estado
            self._reabiertos.clear()
            self.session_path = Path(path)
            self.dataset_changed.emit()
            for paso in self.flujo.ids:
                self.step_updated.emit(paso)
            self.flow_changed.emit()
        finally:
            self._restoring = False
        self._set_dirty(False)

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
        for p in [paso, *flujo.posteriores(paso)]:
            if self.running(p) and not self.module.paso(p).automatico:
                self.cancel(p)  # su resultado ya no correspondería a las entradas
        flujo.invalidar_despues(paso)
        if paso in self._reabiertos:
            self._reabiertos[paso] = True
        definicion = self.module.paso(paso)
        if flujo[paso] == EstadoPaso.HECHO and self.validate(paso):
            flujo.abrir(paso)
        elif flujo[paso] == EstadoPaso.HECHO and definicion.calcula and not definicion.automatico:
            flujo.desactualizar(paso)  # su propio resultado ya no corresponde a los parámetros
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
        self._reabiertos.pop(paso, None)
        siguiente = self.flujo.completar(paso)
        if siguiente and self.module.paso(siguiente).automatico and siguiente not in self.estado.resultados:
            self._schedule(siguiente)
        self.flow_changed.emit()
        return True

    def shutdown(self) -> None:
        """Cancela los cálculos en curso y espera a que terminen (al cerrar la ventana)."""
        for timer in self._timers.values():
            timer.stop()
        cancelar_todo(self._vivas)

    def export(self, tipo: str, destino: str | Path) -> None:
        """Exporta en segundo plano (paso «exportar»). Al terminar, el paso queda hecho."""
        self.estado.params("exportar").update(tipo=tipo, destino=str(destino))
        self.run("exportar", on_success=self._exported)

    def _exported(self) -> None:
        r = self.estado.resultados.get("exportar", {})
        if "error" in r:
            self.message.emit(r["error"])
            return
        nombres = [Path(a).name for a in r["archivos"]]
        texto = ", ".join(nombres) if len(nombres) <= 2 else S.EXPORT_DONE_MORE.format(
            first=nombres[0], n=len(nombres) - 1, folder=Path(r["archivos"][0]).parent.name)
        self.message.emit(S.EXPORT_DONE.format(names=texto))
        if self.flujo["exportar"] == EstadoPaso.ACTIVO:
            self.flujo.completar("exportar")
            self.flow_changed.emit()

    def select_rows(self, rows: list[int]) -> None:
        self.rows_selection_requested.emit(list(rows))

    def focus_step(self, paso: str) -> None:
        self.focus_requested.emit(paso)

    def primary(self, paso: str) -> None:
        """Botón principal de un paso: calcula y lo da por hecho, o solo lo da por hecho."""
        definicion = self.module.paso(paso)
        if not (definicion.calcula and not definicion.automatico):
            self.complete(paso)
            return
        errores = self.validate(paso)
        if errores:
            self.message.emit("\n".join(errores))
            return
        self.run(paso, on_success=lambda: self._computed(paso))

    def _computed(self, paso: str) -> None:
        if "error" in self.estado.resultados.get(paso, {}):
            return
        estaba = self.flujo[paso]
        self._reabiertos.pop(paso, None)
        siguiente = self.flujo.completar(paso)
        if estaba == EstadoPaso.HECHO:
            self.flujo.invalidar_despues(paso)
        if siguiente and self.module.paso(siguiente).automatico and siguiente not in self.estado.resultados:
            self._schedule(siguiente)
        self.flow_changed.emit()

    def reopen(self, paso: str) -> None:
        estaba = self.flujo[paso]
        if self.flujo.activo == paso:
            return
        self._leave_active()
        if estaba in (EstadoPaso.HECHO, EstadoPaso.DESACTUALIZADO):
            self._reabiertos[paso] = estaba == EstadoPaso.DESACTUALIZADO
        self.flujo.abrir(paso)
        sin_resultado = paso not in self.estado.resultados
        if self.module.paso(paso).automatico and (sin_resultado or estaba == EstadoPaso.DESACTUALIZADO):
            self._schedule(paso)
        self.flow_changed.emit()

    def _leave_active(self) -> None:
        """Al salir de un paso reabierto: vuelve a «hecho» si no se cambió nada (o si es un
        paso sin cálculo que sigue siendo válido); si se cambió y su resultado ya no vale,
        queda «desactualizado»."""
        activo = self.flujo.activo
        if activo is None or activo not in self._reabiertos:
            return
        cambiado = self._reabiertos.pop(activo)
        definicion = self.module.paso(activo)
        r = self.estado.resultados.get(activo, {})
        if self.validate(activo) and not definicion.calcula:
            return  # inválido: abrir() lo dejará pendiente
        if cambiado and definicion.calcula and not definicion.automatico:
            self.flujo.estados[activo] = EstadoPaso.DESACTUALIZADO
        elif "error" not in r and (r or not definicion.calcula):
            self.flujo.estados[activo] = EstadoPaso.HECHO

    def recalculate(self, paso: str) -> None:
        """Repite un paso desactualizado con las entradas actuales."""
        if self.flujo.activo in self.flujo.anteriores(paso):
            self._leave_active()
        pendiente = next((p for p in self.flujo.anteriores(paso) if self.flujo[p] != EstadoPaso.HECHO), None)
        if pendiente:
            self.message.emit(S.STALE_BLOCKED.format(step=self.module.paso(pendiente).titulo))
            return
        self.run(paso, on_success=lambda: self._recalculated(paso))

    def _recalculated(self, paso: str) -> None:
        if self.flujo[paso] == EstadoPaso.DESACTUALIZADO and "error" not in self.estado.resultados.get(paso, {}):
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
        if not self.module.paso(paso).automatico:  # la vista previa ya muestra su error en la tarjeta
            self.message.emit(self.estado.resultados[paso]["error"])
