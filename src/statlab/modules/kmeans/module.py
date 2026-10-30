"""Módulos de clustering (k-means, mezclas gaussianas y jerárquico).

Comparten pasos, controles, paneles e informe; lo propio de cada algoritmo
(opciones, criterio del barrido, dendrograma, probabilidades) sale de
`statlab.core.clustering`.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from statlab import strings_es as S
from statlab.core import clustering as cl
from statlab.core import fmt
from statlab.core import kmeans as km
from statlab.core.dataset import Rol
from statlab.core.errors import ErrorUsuario
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
SWEEP_ALG_DEFAULTS = {"kmeans": {}, "gmm": {"n_init": 5, "covarianza": "full"}, "jerarquico": {"enlace": "ward"}}
FINAL_DEFAULTS = {"k": None, "B": 200}
K_MAX = 8  # la paleta tiene 8 colores y nunca se cicla


def _widget_preprocesado(controlador: Any):
    from statlab.modules.kmeans.steps import PreprocessWidget

    return PreprocessWidget(controlador)


def _widget_barrido(controlador: Any):
    from statlab.modules.kmeans.steps import SweepWidget

    return SweepWidget(controlador)


def _widget_final(controlador: Any):
    from statlab.modules.kmeans.steps import FinalWidget

    return FinalWidget(controlador)


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
    """k del modelo final: el que eligió el usuario o, si no, el de mejor silueta (en GMM, el de
    menor BIC)."""
    r = estado.resultados.get("elegir_k")
    if not r or "error" in r:
        return None
    k = estado.params("modelo_final").get("k")
    if k in r["ks"]:
        return int(k)
    return int(r["mejor"]["criterio"] if r.get("algoritmo") == "gmm" else r["mejor"]["silueta"])


def opciones(estado: EstadoSesion, alg: cl.Algoritmo) -> dict[str, Any]:
    """Opciones del algoritmo guardadas en los parámetros del barrido."""
    p = estado.params("elegir_k")
    op = {k: p[k] for k in alg.opciones_defecto() if k in p}
    op["n_init"] = int(p["n_init"])
    return op


def mejor_criterio(alg: cl.Algoritmo, ks: list[int], valores: list[float]) -> int:
    """k que sugiere el criterio propio: codo de la inercia, mínimo BIC o mayor salto de altura."""
    if alg.id == "kmeans":
        return km.elbow_k(ks, valores)
    v = np.asarray(valores, dtype=float)
    if alg.id == "gmm":
        return ks[int(np.nanargmin(v))]
    if len(v) < 2:
        return ks[0]
    saltos = v[:-1] - v[1:]  # altura que se gana al no fusionar los dos últimos grupos
    return ks[int(np.nanargmax(saltos))]


def _matriz(estado: EstadoSesion):
    """Matriz preparada del paso 3 (o se recalcula si no está en memoria, p. ej. al abrir una sesión)."""
    prep = estado.resultados.get("preprocesado", {})
    return prep["_preparado"].X if "_preparado" in prep else preprocesar(estado)["_preparado"].X


def barrer(estado: EstadoSesion, progreso: Progreso, cancelar: Cancelar, alg_id: str = "kmeans") -> Resultado:
    alg = cl.algoritmo(alg_id)
    p = estado.params("elegir_k")
    op = opciones(estado, alg)
    seed = int(p["semilla"])
    X = _matriz(estado)
    ks = list(range(int(p["k_min"]), int(p["k_max"]) + 1))
    peso = 0.25 if p["bootstrap"] else 0.8  # el bootstrap es lo que más tarda
    sw = cl.sweep(alg, X, ks, op, seed, lambda f: progreso(peso * f), cancelar)
    boot = None
    if p["bootstrap"]:
        if alg.id == "kmeans":  # el mismo cálculo de siempre (resultados idénticos a versiones anteriores)
            bk = km.sweep_k_bootstrap(X, ks, int(p["B"]), seed=seed,
                                      progress=lambda f: progreso(peso + 0.7 * f), should_cancel=cancelar)
        else:
            bk = cl.sweep_bootstrap(alg, X, ks, op, int(p["B"]), seed,
                                    progress=lambda f: progreso(peso + 0.7 * f), should_cancel=cancelar)
        boot = {"media": bk["Silueta media boot"].tolist(), "ic_inf": bk["IC95 inf"].tolist(),
                "ic_sup": bk["IC95 sup"].tolist(), "B": int(p["B"])}
    extra = alg.extra_barrido(X, ks, op, seed)
    progreso(1.0)
    sil, ch, db = sw["Silueta"].tolist(), sw["Calinski-Harabasz"].tolist(), sw["Davies-Bouldin"].tolist()
    crit = sw["criterio"].tolist()
    r = {
        "algoritmo": alg.id,
        "opciones": op,
        "ks": ks,
        "n": int(len(X)),
        "criterio": {"id": alg.criterio, "valores": crit},
        "silueta": sil,
        "ch": ch,
        "db": db,
        "tam_min": [int(v) for v in sw["Tamaño mínimo"]],
        "boot": boot,
        "mejor": {
            "silueta": ks[int(np.nanargmax(sil))],
            "ch": ks[int(np.nanargmax(ch))],
            "db": ks[int(np.nanargmin(db))],
            "criterio": mejor_criterio(alg, ks, crit),
        },
        **_json(extra),
    }
    if alg.id == "kmeans":  # nombres de siempre: los usan sesiones e informes anteriores
        r["inercia"] = crit
        r["mejor"]["codo"] = r["mejor"]["criterio"]
    return r


def _json(x):
    """Convierte arrays y NaN de numpy a tipos JSON (NaN → None)."""
    if isinstance(x, dict):
        return {k: _json(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_json(v) for v in x]
    if isinstance(x, np.ndarray):
        return _json(x.tolist())
    if isinstance(x, (np.floating, float)):
        return None if np.isnan(x) else float(x)
    if isinstance(x, np.integer):
        return int(x)
    return x


def _tabla(df) -> dict:
    """DataFrame → {"columnas": [...], "filas": [[...], ...]} (serializable)."""
    return {"columnas": [str(c) for c in df.columns], "filas": _json(df.astype(object).values.tolist())}


def validar_final(estado: EstadoSesion) -> list[str]:
    return [] if k_elegido(estado) is not None else [S.VAL_NEED_SWEEP]


def resumen_final(estado: EstadoSesion) -> str:
    k = k_elegido(estado)
    if k is None:
        return ""
    lineas = [S.FINAL_SUMMARY.format(k=k, b=estado.params("modelo_final")["B"])]
    r = estado.resultados.get("modelo_final")
    if r and "error" not in r:
        sizes = " / ".join(str(n) for n in r["tamanos"])
        lineas.append(S.FINAL_SUMMARY_RESULT.format(sil=fmt.num(r["silueta_media"]), sizes=sizes))
    return "\n".join(lineas)


def ajustar(estado: EstadoSesion, progreso: Progreso, cancelar: Cancelar, alg_id: str = "kmeans") -> Resultado:
    """Modelo final: ajuste, validación bootstrap, PCA, perfiles, descriptivas y sensibilidad."""
    alg = cl.algoritmo(alg_id)
    ds = estado.dataset
    prep_r = estado.resultados.get("preprocesado", {})
    prep = prep_r["_preparado"] if "_preparado" in prep_r else preprocesar(estado)["_preparado"]
    X = prep.X
    k = k_elegido(estado)
    sweep = estado.params("elegir_k")
    n_init, seed = int(sweep["n_init"]), int(sweep["semilla"])
    B = int(estado.params("modelo_final")["B"])
    op = opciones(estado, alg)

    aj = alg.ajustar(X, k, op, seed)
    labels = aj.labels
    sil_obs = km.silhouette_per_point(X, labels)
    progreso(0.05)
    if alg.id == "kmeans":  # el mismo cálculo de siempre (resultados idénticos a versiones anteriores)
        boot = km.bootstrap_validate(X, k, labels, B=B, seed=seed,
                                     progress=lambda f: progreso(0.05 + 0.75 * f), should_cancel=cancelar)
    else:
        boot = cl.bootstrap_validate(alg, X, k, labels, op, B=B, seed=seed,
                                     progress=lambda f: progreso(0.05 + 0.75 * f), should_cancel=cancelar)
    coords, centros, var = km.pca_2d(X, aj.centros)
    filas = ds.df.loc[prep.row_index]
    cols = list(prep.columns)
    desc, z = km.cluster_profiles(filas, cols, X, labels)
    descriptivas = ds.con_rol(Rol.DESCRIPTIVA)
    ext = km.describe_external(filas, descriptivas, labels) if descriptivas else None
    p = estado.params("preprocesado")
    sens, n_sens = cl.imputation_sensitivity(
        alg, ds.df.iloc[ds.filas_activas()], cols, k, p["escalado"], int(p["vecinos"]), op, seed,
        log_cols=prep.log_cols, progress=lambda f: progreso(0.8 + 0.18 * f), should_cancel=cancelar,
    )
    progreso(1.0)
    jaccard_ci = np.asarray(boot.jaccard_ci)
    extra = {}
    if aj.probabilidades is not None:
        extra["probabilidad"] = cl.describe_probabilidades(aj.probabilidades)
    return _json({
        "algoritmo": alg.id,
        "opciones": op,
        **extra,
        "k": k,
        "n": len(X),
        "filas": [int(i) for i in prep.row_index],
        "etiquetas": labels,
        "tamanos": np.bincount(labels, minlength=k),
        "silueta_obs": sil_obs,
        "silueta_media": float(np.mean(sil_obs)),
        "silueta_negativas_pct": float(100 * np.mean(sil_obs < 0)),
        "boot": {
            "B": B,
            "silueta": boot.silhouettes,
            "silueta_ic": list(boot.silhouette_ci),
            "jaccard_media": boot.jaccard_mean,
            "jaccard_ic": jaccard_ci,
            "disuelto_pct": boot.dissolved_pct,
            "ari_media": float(np.nanmean(boot.ari)),
            "interpretacion": [km.jaccard_label(j) for j in boot.jaccard_mean],
        },
        "inestables": int(np.sum(np.asarray(boot.jaccard_mean) < 0.75)),
        "pca": {"coords": coords, "centros": centros, "varianza": var},
        "perfiles": {"columnas": cols, "z": z.values, "tabla": _tabla(desc)},
        "descriptivas": _tabla(ext) if ext is not None and len(ext) else None,
        "sensibilidad": {"metodos": list(sens.index), "ari": sens.values,
                         "n": {km.IMPUTATION_METHODS[m]: n for m, n in n_sens.items()}},
        "metodos": cl.methods_text(alg, prep, k, op, n_init, seed, (int(sweep["k_min"]), int(sweep["k_max"])),
                                   float(np.mean(sil_obs)), boot),
    })


def exportar_archivos(modulo: AnalysisModule, estado: EstadoSesion, progreso: Progreso) -> Resultado:
    from pathlib import Path

    from statlab.core.report import exports as ex

    p = estado.params("exportar")
    contenido = modulo.exportar(estado)
    progreso(0.5)
    base = Path(estado.dataset.fuente).stem or "statlab"
    try:
        archivos = ex.escribir(p["tipo"], contenido, p["destino"], base=base)
    except OSError as e:
        raise ErrorUsuario(S.EXPORT_WRITE_ERROR.format(path=p["destino"])) from e
    progreso(1.0)
    return {"tipo": p["tipo"], "archivos": [str(a) for a in archivos]}


def resumen_exportar(estado: EstadoSesion) -> str:
    r = estado.resultados.get("exportar")
    if not r or "error" in r:
        return ""
    from pathlib import Path

    nombres = [Path(a).name for a in r["archivos"]]
    texto = nombres[0] if len(nombres) == 1 else S.EXPORT_DONE_MORE.format(
        first=nombres[0], n=len(nombres) - 1, folder=Path(r["archivos"][0]).parent.name)
    return S.EXPORT_LAST.format(names=texto)


def validar_exportar(estado: EstadoSesion) -> list[str]:
    r = estado.resultados.get("modelo_final")
    return [] if r and "error" not in r else [S.FINAL_REQUIRED]


def _widget_exportar(controlador: Any):
    from statlab.modules.kmeans.steps import ExportWidget

    return ExportWidget(controlador)


class ClusteringModule(AnalysisModule):
    """Base de los tres módulos: `id` es también el del algoritmo en `core.clustering`."""

    icono = "logo"
    descripcion = ""

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
                parametros={**SWEEP_DEFAULTS, **SWEEP_ALG_DEFAULTS[self.id]},
                crear_widget=_widget_barrido,
                resumen=resumen_barrido,
                validar=validar_barrido,
            ),
            Paso(
                "modelo_final",
                S.STEP_FINAL_MODEL,
                calcula=True,
                boton=S.FINAL_RUN,
                parametros=dict(FINAL_DEFAULTS),
                crear_widget=_widget_final,
                resumen=resumen_final,
                validar=validar_final,
            ),
        ]

    def pasos(self) -> list[Paso]:
        pasos = super().pasos()
        pasos[-1] = Paso("exportar", S.STEP_EXPORT, calcula=True, parametros={"tipo": "pdf", "destino": ""},
                         crear_widget=_widget_exportar, resumen=resumen_exportar, validar=validar_exportar)
        return pasos

    def roles_admitidos(self) -> set[Rol]:
        return {Rol.MODELO, Rol.DESCRIPTIVA, Rol.IDENTIFICADOR, Rol.LOG}

    def ejecutar(self, paso: str, estado: EstadoSesion, progreso: Progreso, cancelar: Cancelar) -> Resultado:
        if paso == "preprocesado":
            resultado = preprocesar(estado)
            progreso(1.0)
            return resultado
        if paso == "elegir_k":
            return barrer(estado, progreso, cancelar, self.id)
        if paso == "modelo_final":
            return ajustar(estado, progreso, cancelar, self.id)
        if paso == "exportar":
            return exportar_archivos(self, estado, progreso)
        raise NotImplementedError(f"Paso «{paso}» todavía no implementado")

    def tiene_panel(self, paso: str) -> bool:
        return paso in ("elegir_k", "modelo_final")

    def paneles(self, paso: str, resultado: Resultado, controlador: Any) -> list:
        if paso == "elegir_k":
            from statlab.modules.kmeans.panels import SweepPanel

            return [SweepPanel(resultado, controlador)]
        if paso == "modelo_final":
            from statlab.modules.kmeans.panels import FinalPanel

            return [FinalPanel(resultado, controlador)]
        return []

    def exportar(self, estado: EstadoSesion) -> Exportacion:
        from statlab.modules.kmeans.report import construir

        return construir(estado)


class KMeansModule(ClusteringModule):
    id = "kmeans"
    nombre = S.KMEANS_NAME
    descripcion = S.KMEANS_DESC


class GMMModule(ClusteringModule):
    id = "gmm"
    nombre = S.GMM_NAME
    descripcion = S.GMM_DESC


class JerarquicoModule(ClusteringModule):
    id = "jerarquico"
    nombre = S.HIER_NAME
    descripcion = S.HIER_DESC
