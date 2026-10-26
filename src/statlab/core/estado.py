"""Estado completo de una sesión de análisis (sin Qt).

Es el único objeto de modelo: datos y roles, parámetros de cada paso,
resultados y estado del flujo. Lo que se guarde en un archivo .statlab sale
de aquí (M5). Las claves de un resultado que empiezan por «_» son objetos de
trabajo (matrices, modelos) que no se serializan y se pueden recalcular.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from statlab.core.dataset import Dataset
from statlab.core.flow import FlujoPasos


@dataclass
class EstadoSesion:
    flujo: FlujoPasos
    dataset: Dataset | None = None
    parametros: dict[str, dict[str, Any]] = field(default_factory=dict)
    resultados: dict[str, dict[str, Any]] = field(default_factory=dict)

    def snapshot(self) -> EstadoSesion:
        """Copia para un cálculo en segundo plano: la interfaz puede seguir cambiando
        roles y parámetros sin afectar al cálculo en curso. El DataFrame se comparte
        (nunca se modifica tras la carga)."""
        ds = None
        if self.dataset is not None:
            d = self.dataset
            ds = Dataset.__new__(Dataset)
            ds.df = d.df
            ds.fuente = d.fuente
            ds.roles = dict(d.roles)
            ds.log = set(d.log)
            ds.solo_filas = None if d.solo_filas is None else set(d.solo_filas)
            ds.excluidas = set(d.excluidas)
            ds.subgrupos = {k: list(v) for k, v in d.subgrupos.items()}
        return EstadoSesion(
            flujo=FlujoPasos.from_dict(self.flujo.ids, self.flujo.to_dict()),
            dataset=ds,
            parametros=copy.deepcopy(self.parametros),
            resultados=dict(self.resultados),
        )

    def params(self, paso: str) -> dict[str, Any]:
        return self.parametros.setdefault(paso, {})


def serializable(resultado: dict[str, Any]) -> dict[str, Any]:
    """Quita las claves de trabajo («_…») de un resultado."""
    return {k: v for k, v in resultado.items() if not k.startswith("_")}
