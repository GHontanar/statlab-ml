"""Flujo de pasos de la barra lateral (sin Qt).

Estados: pendiente → activo → hecho, y desactualizado cuando cambia un paso
anterior a uno ya hecho (conserva el resultado, pero hay que recalcularlo).
Solo hay un paso activo (abierto para editar) a la vez.
"""
from __future__ import annotations

from enum import StrEnum


class EstadoPaso(StrEnum):
    PENDIENTE = "pending"
    ACTIVO = "active"
    HECHO = "done"
    DESACTUALIZADO = "stale"


class FlujoPasos:
    def __init__(self, ids: list[str]):
        if not ids:
            raise ValueError("Un flujo necesita al menos un paso.")
        self.ids = list(ids)
        self.estados: dict[str, EstadoPaso] = {}
        self.reiniciar()

    def reiniciar(self) -> None:
        self.estados = {i: EstadoPaso.PENDIENTE for i in self.ids}
        self.estados[self.ids[0]] = EstadoPaso.ACTIVO

    def __getitem__(self, paso: str) -> EstadoPaso:
        return self.estados[paso]

    def _pos(self, paso: str) -> int:
        return self.ids.index(paso)

    @property
    def activo(self) -> str | None:
        return next((i for i in self.ids if self.estados[i] == EstadoPaso.ACTIVO), None)

    def anteriores(self, paso: str) -> list[str]:
        return self.ids[: self._pos(paso)]

    def posteriores(self, paso: str) -> list[str]:
        return self.ids[self._pos(paso) + 1 :]

    def listo_para(self, paso: str) -> bool:
        """Todos los pasos anteriores están hechos (no pendientes ni desactualizados)."""
        return all(self.estados[i] == EstadoPaso.HECHO for i in self.anteriores(paso))

    def completar(self, paso: str) -> str | None:
        """Marca el paso como hecho y abre el siguiente que no esté hecho. Devuelve cuál."""
        self.estados[paso] = EstadoPaso.HECHO
        for siguiente in self.posteriores(paso):
            estado = self.estados[siguiente]
            if estado == EstadoPaso.HECHO:
                continue
            if estado == EstadoPaso.PENDIENTE:
                self.estados[siguiente] = EstadoPaso.ACTIVO
                return siguiente
            return None  # desactualizado o ya activo: el usuario decide
        return None

    def abrir(self, paso: str) -> None:
        """Reabre un paso hecho o desactualizado para editarlo. El paso que estuviera
        abierto sin terminar vuelve a pendiente."""
        if self.estados[paso] == EstadoPaso.PENDIENTE and not self.listo_para(paso):
            raise ValueError(f"El paso «{paso}» aún no está disponible.")
        for i in self.ids:
            if i != paso and self.estados[i] == EstadoPaso.ACTIVO:
                self.estados[i] = EstadoPaso.PENDIENTE
        self.estados[paso] = EstadoPaso.ACTIVO

    def invalidar_despues(self, paso: str) -> list[str]:
        """Un cambio en `paso` deja desactualizados los pasos posteriores ya hechos."""
        cambiados = []
        hay_desactualizado = False
        for i in self.posteriores(paso):
            if self.estados[i] == EstadoPaso.HECHO:
                self.estados[i] = EstadoPaso.DESACTUALIZADO
                cambiados.append(i)
            if self.estados[i] == EstadoPaso.DESACTUALIZADO:
                hay_desactualizado = True
            elif self.estados[i] == EstadoPaso.ACTIVO and hay_desactualizado:
                # No se puede seguir sobre un paso anterior desactualizado.
                self.estados[i] = EstadoPaso.PENDIENTE
        return cambiados

    def to_dict(self) -> dict[str, str]:
        return {i: e.value for i, e in self.estados.items()}

    @classmethod
    def from_dict(cls, ids: list[str], data: dict[str, str]) -> FlujoPasos:
        flujo = cls(ids)
        flujo.estados = {i: EstadoPaso(data.get(i, EstadoPaso.PENDIENTE)) for i in ids}
        return flujo
