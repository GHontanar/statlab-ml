"""Módulo de clustering k-means sobre `statlab.core.kmeans`."""
from __future__ import annotations

from typing import Any

import numpy as np

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
SWEEP_DEFAULTS = {"k_min": 2, "k_max": 8, "n_init": 20, "semilla": 2026, "bootstrap": True, "B": 50}
FINAL_DEFAULTS = {"k": None, "B": 200}
K_MAX = 8  # la paleta tiene 8 colores y nunca se cicla


def _widget_preprocesado(controlador: Any):
    from statlab.modules.kmeans.steps import PreprocessWidget

    return PreprocessWidget(controlador)


def _widget_barrido(controlador: Any):
    from statlab.modules.kmeans.steps import SweepWidget

    return SweepWidget(controlador)


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


def validar_barrido(estado: EstadoSesion) -> list[str]:
    prep = estado.resultados.get("preprocesado")
    if not prep or "error" in prep:
        return [S.VAL_NEED_PREP]
    k_max = int(estado.params("elegir_k")["k_max"])
    if prep["n_analizadas"] <= k_max:
        return [S.VAL_N_VS_KMAX.format(n=prep["n_analizadas"], k=k_max)]
    return []


def resumen_barrido(estado: EstadoSesion) -> str:
    p = estado.params("elegir_k")
    lineas = [S.SWEEP_SUMMARY.format(lo=p["k_min"], hi=p["k_max"], ninit=p["n_init"], seed=p["semilla"])]
    if p["bootstrap"]:
        lineas.append(S.SWEEP_SUMMARY_BOOT.format(b=p["B"]))
    k = k_elegido(estado)
    if k is not None:
        lineas.append(S.SWEEP_SUMMARY_K.format(k=k))
    return "\n".join(lineas)


def k_elegido(estado: EstadoSesion) -> int | None:
    """k del modelo final: el que eligió el usuario o, si no, el de mejor silueta."""
    r = estado.resultados.get("elegir_k")
    if not r or "error" in r:
        return None
    k = estado.params("modelo_final").get("k")
    return int(k) if k in r["ks"] else int(r["mejor"]["silueta"])


def _matriz(estado: EstadoSesion):
    """Matriz preparada del paso 3 (o se recalcula si no está en memoria, p. ej. al abrir una sesión)."""
    prep = estado.resultados.get("preprocesado", {})
    return prep["_preparado"].X if "_preparado" in prep else preprocesar(estado)["_preparado"].X


def barrer(estado: EstadoSesion, progreso: Progreso, cancelar: Cancelar) -> Resultado:
    p = estado.params("elegir_k")
    X = _matriz(estado)
    ks = list(range(int(p["k_min"]), int(p["k_max"]) + 1))
    peso = 0.25 if p["bootstrap"] else 1.0  # el bootstrap es lo que más tarda
    sw = km.sweep_k(X, ks, int(p["n_init"]), int(p["semilla"]), lambda f: progreso(peso * f), cancelar)
    boot = None
    if p["bootstrap"]:
        bk = km.sweep_k_bootstrap(X, ks, int(p["B"]), seed=int(p["semilla"]),
                                  progress=lambda f: progreso(peso + (1 - peso) * f), should_cancel=cancelar)
        boot = {"media": bk["Silueta media boot"].tolist(), "ic_inf": bk["IC95 inf"].tolist(),
                "ic_sup": bk["IC95 sup"].tolist(), "B": int(p["B"])}
    progreso(1.0)
    sil, ch, db = sw["Silueta"].tolist(), sw["Calinski-Harabasz"].tolist(), sw["Davies-Bouldin"].tolist()
    return {
        "ks": ks,
        "n": int(len(X)),
        "inercia": sw["Inercia"].tolist(),
        "silueta": sil,
        "ch": ch,
        "db": db,
        "tam_min": [int(v) for v in sw["Tamaño mínimo"]],
        "boot": boot,
        "mejor": {
            "silueta": ks[int(np.nanargmax(sil))],
            "ch": ks[int(np.nanargmax(ch))],
            "db": ks[int(np.nanargmin(db))],
            "codo": km.elbow_k(ks, sw["Inercia"]),
        },
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
            Paso(
                "elegir_k",
                S.STEP_CHOOSE_K,
                calcula=True,
                boton=S.SWEEP_RUN,
                parametros=dict(SWEEP_DEFAULTS),
                crear_widget=_widget_barrido,
                resumen=resumen_barrido,
                validar=validar_barrido,
            ),
            Paso(
                "modelo_final",
                S.STEP_FINAL_MODEL,
                calcula=True,
                parametros=dict(FINAL_DEFAULTS),
                crear_widget=_widget_proximamente,
            ),
        ]

    def roles_admitidos(self) -> set[Rol]:
        return {Rol.MODELO, Rol.DESCRIPTIVA, Rol.IDENTIFICADOR, Rol.LOG}

    def ejecutar(self, paso: str, estado: EstadoSesion, progreso: Progreso, cancelar: Cancelar) -> Resultado:
        if paso == "preprocesado":
            resultado = preprocesar(estado)
            progreso(1.0)
            return resultado
        if paso == "elegir_k":
            return barrer(estado, progreso, cancelar)
        raise NotImplementedError(f"Paso «{paso}» todavía no implementado")

    def paneles(self, paso: str, resultado: Resultado, controlador: Any) -> list:
        if paso == "elegir_k":
            from statlab.modules.kmeans.panels import SweepPanel

            return [SweepPanel(resultado, controlador)]
        return []

    def exportar(self, resultados: dict[str, Resultado]) -> Exportacion:
        return Exportacion()
