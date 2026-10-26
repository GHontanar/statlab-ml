"""Módulo de clustering k-means sobre `statlab.core.kmeans`."""
from __future__ import annotations

from typing import Any

from statlab import strings_es as S
from statlab.core import kmeans as km
from statlab.core.dataset import Rol
from statlab.core.estado import EstadoSesion
from statlab.modules.base import (
    AnalysisModule,
    Cancelar,
    Exportacion,
    Paso,
    Progreso,
    Resultado,
)

PREP_DEFAULTS = {"imputacion": "knn", "vecinos": 5, "escalado": "standard"}


def _widget_preprocesado(controlador: Any):
    from statlab.modules.kmeans.steps import PreprocessWidget

    return PreprocessWidget(controlador)


def _widget_proximamente(controlador: Any):
    from PySide6.QtWidgets import QLabel

    label = QLabel(S.NEXT_MILESTONE)
    label.setObjectName("Hint")
    label.setWordWrap(True)
    return label


def resumen_preprocesado(estado: EstadoSesion) -> str:
    p = estado.params("preprocesado")
    r = estado.resultados.get("preprocesado", {})
    imp = r.get("celdas_imputadas", 0)
    if p["imputacion"] == "knn":
        linea = S.PREP_SUMMARY_MISSING_KNN.format(k=p["vecinos"], imp=imp)
    elif p["imputacion"] == "complete":
        linea = S.PREP_SUMMARY_COMPLETE.format(excl=r.get("n_excluidas", 0))
    else:
        linea = S.PREP_SUMMARY_MISSING.format(method=S.MISSING_SHORT[p["imputacion"]], imp=imp)
    lineas = [linea, S.PREP_SUMMARY_SCALING.format(method=S.SCALING_SHORT[p["escalado"]])]
    if r.get("log"):
        lineas.append(S.PREP_LOG.format(cols=", ".join(r["log"])))
    return "\n".join(lineas)


def validar_preprocesado(estado: EstadoSesion) -> list[str]:
    r = estado.resultados.get("preprocesado")
    if r is None:
        return [S.RUNNING]
    return [r["error"]] if "error" in r else []


def preprocesar(estado: EstadoSesion) -> Resultado:
    ds = estado.dataset
    p = estado.params("preprocesado")
    cols = ds.con_rol(Rol.MODELO)
    log = [c for c in cols if c in ds.log]
    df = ds.df.iloc[ds.filas_activas()]
    prep = km.prepare(df, cols, p["imputacion"], p["escalado"], int(p["vecinos"]), log)
    return {
        "n_entrada": prep.n_input,
        "n_analizadas": len(prep.X),
        "n_excluidas": prep.n_dropped,
        "celdas_imputadas": prep.n_imputed_cells,
        "avisos": list(prep.warnings),
        "columnas": list(prep.columns),
        "log": list(prep.log_cols),
        "filas": [int(i) for i in prep.row_index],  # posiciones en la tabla cargada
        "_preparado": prep,
    }


class KMeansModule(AnalysisModule):
    id = "kmeans"
    nombre = S.KMEANS_NAME
    icono = "logo"

    def pasos_propios(self) -> list[Paso]:
        return [
            Paso(
                "preprocesado",
                S.STEP_PREPROCESS,
                calcula=True,
                automatico=True,
                boton=S.CONTINUE,
                parametros=dict(PREP_DEFAULTS),
                crear_widget=_widget_preprocesado,
                resumen=resumen_preprocesado,
                validar=validar_preprocesado,
            ),
            Paso("elegir_k", S.STEP_CHOOSE_K, calcula=True, crear_widget=_widget_proximamente),
            Paso("modelo_final", S.STEP_FINAL_MODEL, calcula=True, crear_widget=_widget_proximamente),
        ]

    def roles_admitidos(self) -> set[Rol]:
        return {Rol.MODELO, Rol.DESCRIPTIVA, Rol.IDENTIFICADOR, Rol.LOG}

    def ejecutar(self, paso: str, estado: EstadoSesion, progreso: Progreso, cancelar: Cancelar) -> Resultado:
        if paso == "preprocesado":
            resultado = preprocesar(estado)
            progreso(1.0)
            return resultado
        raise NotImplementedError(f"Paso «{paso}» todavía no implementado")

    def paneles(self, paso: str, resultado: Resultado) -> list:
        return []

    def exportar(self, resultados: dict[str, Resultado]) -> Exportacion:
        return Exportacion()
