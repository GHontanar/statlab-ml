"""Controlador de la sesión: único dueño del `Dataset` y emisor de los cambios.

La tabla y la barra lateral no se hablan entre sí: llaman a este objeto y
escuchan sus señales.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from statlab import strings_es as S
from statlab.core import io as sio
from statlab.core.dataset import Cambio, Dataset, Rol


class SessionController(QObject):
    dataset_changed = Signal()  # datos nuevos
    roles_changed = Signal()
    rows_changed = Signal()
    message = Signal(str)  # aviso para el usuario (rol rechazado, subgrupo guardado…)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.dataset: Dataset | None = None

    # --- Carga ----------------------------------------------------------
    def load_path(self, path: str | Path) -> None:
        """Lanza ValueError con un mensaje legible si no se puede leer."""
        path = Path(path)
        try:
            df = sio.read_path(path)
        except ValueError:
            raise
        except Exception as e:  # pandas/openpyxl lanzan muchos tipos distintos
            raise ValueError(S.READ_ERROR_GENERIC) from e
        self._set(Dataset(df, fuente=path.name))

    def load_example(self) -> None:
        self._set(Dataset(sio.read_example(), fuente=sio.EXAMPLE_NAME))

    def _set(self, dataset: Dataset) -> None:
        self.dataset = dataset
        self.dataset_changed.emit()

    # --- Columnas -------------------------------------------------------
    def set_role(self, cols: list[str], rol: Rol | None) -> Cambio:
        cambio = self.dataset.asignar_rol(cols, rol)
        self._after_roles(cambio)
        return cambio

    def toggle_log(self, cols: list[str]) -> Cambio:
        cambio = self.dataset.alternar_log(cols)
        self._after_roles(cambio)
        return cambio

    def _after_roles(self, cambio: Cambio) -> None:
        if cambio.aplicadas:
            self.roles_changed.emit()
        if cambio.rechazadas:
            self.message.emit(cambio.mensaje)

    # --- Filas ----------------------------------------------------------
    def analyze_only(self, rows: list[int]) -> None:
        self.dataset.analizar_solo(rows)
        self.rows_changed.emit()

    def exclude(self, rows: list[int]) -> None:
        self.dataset.excluir(rows)
        self.rows_changed.emit()

    def use_all_rows(self) -> None:
        self.dataset.usar_todas()
        self.rows_changed.emit()

    def save_subgroup(self, name: str, rows: list[int]) -> None:
        self.dataset.guardar_subgrupo(name, rows)
        self.rows_changed.emit()
        self.message.emit(S.SUBGROUP_SAVED.format(name=name.strip(), n=len(set(rows))))
