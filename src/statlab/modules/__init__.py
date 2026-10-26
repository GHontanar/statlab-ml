"""Módulos de análisis enchufables."""
from __future__ import annotations

from statlab.modules.base import AnalysisModule


def available_modules() -> list[AnalysisModule]:
    from statlab.modules.kmeans.module import KMeansModule

    return [KMeansModule()]
