"""Módulo de clustering k-means.

M0: solo declara sus pasos y roles. El cálculo y los paneles llegan en
M2–M4 sobre `statlab.core.kmeans`.
"""
from __future__ import annotations

from typing import Any

from statlab import strings_es as S
from statlab.modules.base import (
    AnalysisModule,
    Cancelar,
    Exportacion,
    Paso,
    Progreso,
    Resultado,
    Rol,
)


class KMeansModule(AnalysisModule):
    id = "kmeans"
    nombre = S.KMEANS_NAME
    icono = "logo"

    def pasos_propios(self) -> list[Paso]:
        return [
            Paso("preprocesado", S.STEP_PREPROCESS),
            Paso("elegir_k", S.STEP_CHOOSE_K, calcula=True),
            Paso("modelo_final", S.STEP_FINAL_MODEL, calcula=True),
        ]

    def roles_admitidos(self) -> set[Rol]:
        return {Rol.MODELO, Rol.DESCRIPTIVA, Rol.IDENTIFICADOR, Rol.LOG}

    def ejecutar(self, paso: str, contexto: Any, progreso: Progreso, cancelar: Cancelar) -> Resultado:
        raise NotImplementedError(f"Paso «{paso}» todavía no implementado")

    def paneles(self, paso: str, resultado: Resultado) -> list:
        return []

    def exportar(self, resultados: dict[str, Resultado]) -> Exportacion:
        return Exportacion()
