"""Contenido de los exportes del módulo k-means (sin Qt)."""
from __future__ import annotations

from datetime import datetime

from statlab import __version__
from statlab import strings_es as S
from statlab.core import fmt
from statlab.core import kmeans as km
from statlab.core.dataset import Rol
from statlab.core.errors import ErrorUsuario
from statlab.core.estado import EstadoSesion, serializable
from statlab.core.prep.preparacion import diagrama_flujo
from statlab.core.report import exports as ex
from statlab.core.report import figures as fig
from statlab.core.report.document import Figura, Parrafo, SaltoPagina, Tabla, Titulo
from statlab.modules.base import Exportacion

FIGURAS = [  # nombre de archivo, función, pie
    ("01_codo", lambda e, k: fig.elbow(e.resultados["elegir_k"], k), S.FIG_ELBOW),
    ("02_silueta_por_k", lambda e, k: fig.silhouette_by_k(e.resultados["elegir_k"], k), S.FIG_SIL_K),
    ("03_pca", lambda e, k: fig.pca(e.resultados["modelo_final"]), S.FIG_PCA),
    ("04_mapa_de_calor", lambda e, k: fig.heatmap(e.resultados["modelo_final"], etiquetas(e)[0]), S.FIG_HEATMAP),
    ("05_silueta_por_observacion", lambda e, k: fig.silhouette_obs(e.resultados["modelo_final"]), S.FIG_SIL_OBS),
    ("06_jaccard", lambda e, k: fig.jaccard(e.resultados["modelo_final"]), S.FIG_JACCARD),
    ("07_histograma_bootstrap", lambda e, k: fig.boot_histogram(e.resultados["modelo_final"]), S.FIG_HIST),
]


def etiquetas(estado: EstadoSesion):
    """(nombre de variable → etiqueta del diccionario, (variable, nivel) → etiqueta del nivel)."""
    dic = estado.preparacion.diccionario if estado.preparacion else None

    def nombre(col: str) -> str:
        return dic.etiqueta(col) if dic else col

    def nivel(col: str, valor: str) -> str:
        e = dic.get(col) if dic else None
        return e.categorias.get(valor, valor) if e else valor

    return nombre, nivel


def _parametros(estado: EstadoSesion) -> list[list[str]]:
    ds = estado.dataset
    nombre, _ = etiquetas(estado)
    prep = estado.params("preprocesado")
    sweep = estado.params("elegir_k")
    final = estado.resultados["modelo_final"]
    perdidos = (S.MISSING_KNN_LONG.format(k=prep["vecinos"]) if prep["imputacion"] == "knn"
                else S.MISSING_SHORT[prep["imputacion"]])
    return [
        [S.P_MODEL_VARS, ", ".join(map(nombre, ds.con_rol(Rol.MODELO)))],
        [S.P_LOG, ", ".join(map(nombre, sorted(ds.log))) or S.NONE],
        [S.P_DESCR, ", ".join(map(nombre, ds.con_rol(Rol.DESCRIPTIVA))) or S.NONE],
        [S.P_ID, nombre(ds.identificador) if ds.identificador else S.NONE],
        [S.P_ROWS, f"{final['n']} de {ds.n_filas}"],
        [S.P_MISSING, perdidos],
        [S.P_SCALING, S.SCALING_SHORT[prep["escalado"]]],
        [S.P_RANGE, f"{sweep['k_min']}–{sweep['k_max']}"],
        [S.P_NINIT, str(sweep["n_init"])],
        [S.P_SEED, str(sweep["semilla"])],
        [S.P_SWEEP_BOOT, S.YES_B.format(b=sweep["B"]) if sweep["bootstrap"] else S.NO],
        [S.P_K, str(final["k"])],
        [S.P_FINAL_B, str(final["boot"]["B"])],
    ]


def _tabla_indices(sweep: dict) -> Tabla:
    boot = sweep.get("boot")
    filas = []
    for i, k in enumerate(sweep["ks"]):
        ic = f"{fmt.num(boot['ic_inf'][i], 3)} – {fmt.num(boot['ic_sup'][i], 3)}" if boot else "—"
        filas.append([str(k), fmt.num(sweep["inercia"][i], 1), fmt.num(sweep["silueta"][i], 3), ic,
                      fmt.num(sweep["ch"][i], 1), fmt.num(sweep["db"][i], 3), str(sweep["tam_min"][i])])
    m = sweep["mejor"]
    pie = (f"{S.INDEX_TABLE_NOTE} " + " · ".join([S.BEST_K_SIL.format(k=m["silueta"]), S.BEST_K_CH.format(k=m["ch"]),
                                                   S.BEST_K_DB.format(k=m["db"]), S.BEST_K_ELBOW.format(k=m["codo"])]))
    return Tabla(list(S.INDEX_TABLE_HEAD), filas, pie=pie, izquierda=set())


def _kpis(r: dict) -> Tabla:
    lo, hi = r["boot"]["silueta_ic"]
    sizes = " / ".join(f"C{c + 1}: {n} ({fmt.pct(100 * n / r['n'], 0)})" for c, n in enumerate(r["tamanos"]))
    return Tabla(list(S.REPORT_KPI_HEAD), [
        [S.KPI_SIL, fmt.num(r["silueta_media"])],
        [S.KPI_CI, f"{fmt.num(lo, 3)} – {fmt.num(hi, 3)} ({r['boot']['B']} remuestras)"],
        [S.KPI_ARI, fmt.num(r["boot"]["ari_media"])],
        [S.KPI_UNSTABLE, S.KPI_UNSTABLE_VALUE.format(n=r["inestables"], k=r["k"])],
        [S.SIZES, sizes],
    ], izquierda={0, 1})


def _perfiles(r: dict, nombre=str) -> Tabla:
    t = r["perfiles"]["tabla"]
    filas = []
    for fila in t["filas"]:
        celdas = []
        for v in fila:
            celdas.append(fmt.num(v, 1) if isinstance(v, float) else str(v))
        filas.append([f"C{celdas[0]}" if celdas[0].isdigit() else celdas[0], *celdas[1:]])
    cab = ["Cluster", "n", "%", *map(nombre, t["columnas"][3:])]
    return Tabla(cab, filas, pie=S.NO_TESTS_NOTE)


def _estabilidad(r: dict) -> Tabla:
    b = r["boot"]
    filas = [[f"C{c + 1}", str(r["tamanos"][c]), fmt.num(b["jaccard_media"][c]),
              f"{fmt.num(b['jaccard_ic'][c][0])} – {fmt.num(b['jaccard_ic'][c][1])}",
              fmt.num(b["disuelto_pct"][c], 1), b["interpretacion"][c]] for c in range(r["k"])]
    return Tabla(list(S.STABILITY_HEAD), filas, pie=S.STABILITY_NOTE, izquierda={0, 5})


def _sensibilidad(r: dict) -> Tabla:
    s = r["sensibilidad"]
    filas = [[m, *("—" if v is None else fmt.num(v) for v in fila)] for m, fila in zip(s["metodos"], s["ari"],
                                                                                         strict=True)]
    low = any(v is not None and v < 0.8 for i, f in enumerate(s["ari"]) for j, v in enumerate(f) if i != j)
    n = " · ".join(f"{m}: {v}" for m, v in s["n"].items())
    return Tabla(["", *s["metodos"]], filas, pie=f"{S.SENS_N.format(items=n)}. {S.SENS_WARN if low else S.SENS_OK}")


def _descriptivas(r: dict, nombre=str, nivel=lambda c, v: v) -> Tabla | None:
    d = r.get("descriptivas")
    if not d:
        return None
    k = r["k"]
    cab = [S.DESC_HEAD_VAR, S.DESC_HEAD_LEVEL, *[f"C{c + 1}" for c in range(k)], *d["columnas"][2 + k:]]
    filas = [["" if v is None else str(v) for v in fila] for fila in d["filas"]]
    filas = [[nombre(f[0]), nivel(f[0], f[1]), *f[2:]] if f and f[0] else f for f in filas]
    return Tabla(cab, filas, pie=S.DESC_NOTE, izquierda={0, 1})


def _receta(prep) -> Tabla:
    filas = [[str(i), p.descripcion] for i, p in enumerate((p for p in prep.receta.pasos if p.activo), start=1)]
    return Tabla(list(S.REPORT_PREP_HEAD), filas, izquierda={0, 1})


def construir(estado: EstadoSesion) -> Exportacion:
    r = estado.resultados.get("modelo_final")
    if not r or "error" in r:
        raise ErrorUsuario(S.FINAL_REQUIRED)
    ds = estado.dataset
    k = r["k"]
    figuras = {nombre: crear(estado, k) for nombre, crear, _ in FIGURAS}
    pies = {nombre: pie for nombre, _, pie in FIGURAS}
    png = {nombre: fig.png_bytes(f, dpi=200) for nombre, f in figuras.items()}
    ahora = datetime.now()

    bloques = [
        Titulo(S.REPORT_TITLE, 0),
        Parrafo(S.REPORT_COVER.format(fuente=ds.fuente, n=ds.n_filas, cols=len(ds.columnas), n_model=r["n"])),
        Parrafo(S.REPORT_DATE.format(fecha=ex.fecha_larga(ahora), version=__version__)),
        Parrafo(S.REPORT_PRIVACY, nota=True),
    ]
    flujo = diagrama_flujo(ds, estado.preparacion.receta if estado.preparacion else None)
    if flujo.exclusiones:
        figuras["00_flujo_pacientes"] = fig.flujo_pacientes(flujo)
        bloques += [Titulo(S.REPORT_FLOW, 1), Figura(fig.png_bytes(figuras["00_flujo_pacientes"], dpi=200),
                                                     S.REPORT_FLOW_CAPTION)]
    if estado.preparacion and estado.preparacion.receta.pasos:
        bloques += [Titulo(S.REPORT_PREP, 1), _receta(estado.preparacion)]
    bloques += [
        Titulo(S.REPORT_PARAMS, 1),
        Tabla(list(S.REPORT_PARAM_HEAD), _parametros(estado), izquierda={0, 1}),
        Titulo(S.REPORT_SWEEP, 1),
        _tabla_indices(estado.resultados["elegir_k"]),
        Figura(png["01_codo"], pies["01_codo"]),
        Figura(png["02_silueta_por_k"], pies["02_silueta_por_k"]),
        SaltoPagina(),
        Titulo(S.REPORT_FINAL, 1),
        _kpis(r),
        Titulo(S.REPORT_FIGURES, 1),
        *[Figura(png[n], pies[n]) for n in ("03_pca", "04_mapa_de_calor", "05_silueta_por_observacion",
                                            "06_jaccard", "07_histograma_bootstrap")],
        SaltoPagina(),
        Titulo(S.REPORT_TABLES, 1),
        Titulo(S.REPORT_PROFILES, 2),
        _perfiles(r, etiquetas(estado)[0]),
    ]
    desc = _descriptivas(r, *etiquetas(estado))
    if desc:
        bloques += [Titulo(S.TAB_DESCRIPTIVE, 2), desc]
    bloques += [
        Titulo(S.TAB_STABILITY, 2),
        _estabilidad(r),
        Titulo(S.REPORT_SENS, 1),
        _sensibilidad(r),
        Titulo(S.REPORT_METHODS, 1),
        Parrafo(r["metodos"]),
        Parrafo(S.REPORT_METHODS_NOTE, nota=True),
        Titulo(S.REPORT_VERSIONS, 1),
        Tabla(list(S.REPORT_VERSIONS_HEAD), [[a, b] for a, b in ex.versiones()], izquierda={0, 1}),
    ]

    tabla = ex.tabla_con_clusters(ds.df, r["filas"], r["etiquetas"], r["silueta_obs"])
    datos = {
        "app": "StatLab",
        "version": __version__,
        "fecha": ahora.isoformat(timespec="seconds"),
        "fuente": ds.fuente,
        "modulo": "kmeans",
        "roles": {c: rol.value for c, rol in ds.roles.items()},
        "log": sorted(ds.log),
        "filas_excluidas": sorted(ds.excluidas),
        "filas_excluidas_receta": {str(k): v for k, v in sorted(ds.excluidas_receta.items())},
        "preparacion": estado.preparacion.to_dict() if estado.preparacion else None,
        "solo_filas": None if ds.solo_filas is None else sorted(ds.solo_filas),
        "parametros": estado.parametros,
        "resultados": {p: serializable(v) for p, v in estado.resultados.items()},
        "metodos_imputacion": km.IMPUTATION_METHODS,
    }
    metodos = f"# {S.REPORT_METHODS}\n\n{r['metodos']}\n"
    return Exportacion(titulo=S.REPORT_TITLE, bloques=bloques, figuras=figuras, tabla=tabla, json=datos,
                       metodos=metodos)
