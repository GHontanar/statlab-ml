"""Módulos de análisis enchufables."""
from __future__ import annotations

from statlab.modules.base import AnalysisModule


def available_modules() -> list[AnalysisModule]:
    """El primero es el de las sesiones nuevas."""
    from statlab.modules.kmeans.module import GMMModule, JerarquicoModule, KMeansModule

    return [KMeansModule(), GMMModule(), JerarquicoModule()]
