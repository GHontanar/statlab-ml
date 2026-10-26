"""Página Streamlit: clustering k-means (StatLab ML, prueba de concepto).

Se integra en StatLab como página extra (ver pages/) o se ejecuta sola con app.py.
No llama a st.set_page_config: eso lo hace la app que la aloja.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
import streamlit as st

from . import kmeans_core as kc
from . import plots

EXAMPLE = Path(__file__).resolve().parent.parent / "ejemplo" / "datos_ejemplo.csv"
K_MIN, K_MAX = 2, plots.MAX_CLUSTERS


# ---------------------------------------------------------------------------
# Cálculos cacheados (se repiten al instante si no cambian los parámetros)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False, max_entries=10)
def _read(name: str, raw: bytes) -> pd.DataFrame:
    return kc.read_table(name, raw)


@st.cache_data(show_spinner=False, max_entries=20)
def _prepare(df, cols, imp, sc, knn, logs):
    return kc.prepare(df, list(cols), imp, sc, knn, list(logs))


@st.cache_data(show_spinner=False, max_entries=20)
def _sweep(X, k_lo, k_hi, n_init, seed):
    return kc.sweep_k(X, range(k_lo, k_hi + 1), n_init, seed)


@st.cache_data(show_spinner=False, max_entries=20)
def _sweep_boot(X, k_lo, k_hi, B, seed):
    return kc.sweep_k_bootstrap(X, range(k_lo, k_hi + 1), B=B, n_init=3, seed=seed)


@st.cache_data(show_spinner=False, max_entries=20)
def _fit(X, k, n_init, seed):
    km, labels = kc.fit_kmeans(X, k, n_init, seed)
    return km.cluster_centers_, labels


@st.cache_data(show_spinner=False, max_entries=10)
def _boot(X, k, labels, B, seed):
    return kc.bootstrap_validate(X, k, labels, B=B, n_init=3, seed=seed)


@st.cache_data(show_spinner=False, max_entries=10)
def _sensitivity(df, cols, k, sc, knn, n_init, seed, logs):
    return kc.imputation_sensitivity(df, list(cols), k, sc, knn, n_init, seed, log_cols=list(logs))


def _chart(fig, key=None):
    st.plotly_chart(fig, width="stretch", key=key, config={"displaylogo": False})


# ---------------------------------------------------------------------------
# Página
# ---------------------------------------------------------------------------
def render() -> None:
    st.title("Clustering k-means")
    st.caption(
        "StatLab ML · prueba de concepto. Todo se calcula en este equipo: "
        "los datos se quedan en memoria y no se guardan en disco ni se envían fuera."
    )

    # ---------------- 1 · Datos ----------------
    with st.sidebar:
        st.header("1 · Datos")
        up = st.file_uploader("CSV, TSV o Excel", type=["csv", "tsv", "txt", "xlsx", "xls"])
        use_example = st.toggle("Usar datos de ejemplo (sintéticos)", value=up is None and EXAMPLE.exists())

    if up is not None:
        try:
            df = _read(up.name, up.getvalue())
        except Exception as e:  # noqa: BLE001
            st.error(f"No he podido leer el archivo: {e}")
            return
        source = up.name
    elif use_example:
        df = _read(EXAMPLE.name, EXAMPLE.read_bytes())
        source = "datos de ejemplo (sintéticos)"
    else:
        st.info("Carga un archivo en la barra lateral para empezar.")
        return

    st.subheader("Datos")
    st.caption(
        f"{source} · {len(df)} filas × {df.shape[1]} columnas. "
        "Puedes seleccionar filas en la tabla (casilla de la izquierda) para analizar solo ese subgrupo."
    )
    event = st.dataframe(
        df, height=260, width="stretch", on_select="rerun", selection_mode="multi-row", key="tabla_datos"
    )
    selected = list(getattr(getattr(event, "selection", None), "rows", []) or [])
    only_sel = False
    if selected:
        only_sel = st.toggle(f"Analizar solo las {len(selected)} filas seleccionadas", value=True)
    work = df.iloc[sorted(selected)] if only_sel else df

    # ---------------- 2–4 · Parámetros ----------------
    with st.sidebar:
        st.header("2 · Variables")
        id_col = st.selectbox("Columna identificador (opcional)", ["(ninguna)"] + list(df.columns))
        id_col = None if id_col == "(ninguna)" else id_col
        num = [c for c in kc.numeric_columns(df) if c != id_col]
        cols = st.multiselect("Variables para el clustering", num, help="Solo numéricas, al menos 2.")
        logs = st.multiselect(
            "Transformar con log(1+x)", cols,
            help="Útil para variables muy asimétricas (ferritina, LDH, PCR…).",
        )
        others = [c for c in df.columns if c not in cols and c != id_col]
        ext = st.multiselect(
            "Variables descriptivas (no entran en el modelo)", others,
            help="Se describen por cluster: edad, sexo, desenlaces…",
        )

        st.header("3 · Preprocesado")
        imp = st.selectbox("Valores perdidos", list(kc.IMPUTATION_METHODS),
                           index=3, format_func=kc.IMPUTATION_METHODS.get)
        knn = st.slider("Vecinos para KNN", 1, 15, 5) if imp == "knn" else 5
        sc = st.selectbox("Escalado", list(kc.SCALING_METHODS), format_func=kc.SCALING_METHODS.get)

        st.header("4 · Búsqueda de k")
        k_lo, k_hi = st.slider("Rango de k", K_MIN, K_MAX, (K_MIN, K_MAX))
        n_init = st.number_input("Inicializaciones de k-means", 5, 100, 20, step=5)
        seed = int(st.number_input("Semilla", 0, 10**6, 2026))
        boot_k = st.toggle("IC bootstrap de la silueta para cada k", value=False,
                           help="Más lento: ajusta k-means B veces por cada k.")
        B_k = st.slider("Remuestras por k", 20, 200, 50, step=10) if boot_k else 0

    if len(cols) < 2:
        st.info("Elige al menos dos variables numéricas para el clustering en la barra lateral (paso 2).")
        return

    # ---------------- Preparación ----------------
    try:
        prep = _prepare(work, tuple(cols), imp, sc, knn, tuple(logs))
    except ValueError as e:
        st.error(str(e))
        return
    X = prep.X
    rows = work.loc[prep.row_index]

    st.subheader("Preparación")
    m1, m2, m3 = st.columns(3)
    m1.metric("Observaciones analizadas", len(X))
    m2.metric("Excluidas", prep.n_dropped)
    m3.metric("Celdas imputadas", prep.n_imputed_cells)
    for w in prep.warnings:
        st.warning(w)
    with st.expander("Valores perdidos por variable"):
        st.dataframe(kc.missing_summary(work, cols), hide_index=True, width="stretch")

    if len(X) <= k_hi:
        st.error(f"Hay {len(X)} observaciones: necesitas más que el k máximo ({k_hi}).")
        return

    # ---------------- Elegir k ----------------
    st.subheader("Elegir el número de clusters")
    data_sig = (source, tuple(sorted(selected)) if only_sel else None)
    sig_prep = (data_sig, tuple(cols), tuple(logs), imp, knn, sc)
    sig_sweep = sig_prep + (k_lo, k_hi, int(n_init), seed, B_k)

    if st.button("Calcular barrido de k", type="primary"):
        st.session_state["sweep_sig"] = sig_sweep
    if st.session_state.get("sweep_sig") != sig_sweep:
        st.caption("Pulsa el botón para comparar k entre "
                   f"{k_lo} y {k_hi} (inercia, silueta y otros índices).")
        return

    with st.spinner("Ajustando k-means para cada k…"):
        sweep = _sweep(X, k_lo, k_hi, int(n_init), seed)
        bk = _sweep_boot(X, k_lo, k_hi, B_k, seed) if boot_k else None
    k_sug = int(sweep.loc[sweep["Silueta"].idxmax(), "k"])
    k_ch = int(sweep.loc[sweep["Calinski-Harabasz"].idxmax(), "k"])
    k_db = int(sweep.loc[sweep["Davies-Bouldin"].idxmin(), "k"])

    c1, c2 = st.columns(2)
    with c1:
        _chart(plots.elbow(sweep, k_sug), "codo")
    with c2:
        _chart(plots.silhouette_by_k(sweep, bk, k_sug), "silk")
    st.caption(
        f"Mejor k según cada índice: silueta **{k_sug}** · Calinski-Harabasz **{k_ch}** · "
        f"Davies-Bouldin **{k_db}**. Es orientativo: combina el codo, estos índices, la estabilidad "
        "y si los clusters tienen sentido clínico."
    )
    with st.expander("Tabla de índices por k"):
        show = sweep.copy()
        if bk is not None:
            show = show.merge(bk, on="k")
        st.dataframe(
            show.style.format({c: "{:.3f}" for c in show.columns if c not in ("k", "Tamaño mínimo")}),
            hide_index=True, width="stretch",
        )
        st.caption("Silueta y Calinski-Harabasz: mayor es mejor. Davies-Bouldin: menor es mejor.")

    # ---------------- Modelo final ----------------
    st.subheader("Modelo final y validación")
    f1, f2 = st.columns(2)
    ks = list(range(k_lo, k_hi + 1))
    k = f1.selectbox("k elegido", ks, index=ks.index(k_sug))
    B = f2.select_slider("Remuestras bootstrap", [50, 100, 200, 500, 1000], value=200)
    sig_final = sig_sweep + (k, B)
    if st.button("Ajustar y validar", type="primary"):
        st.session_state["final_sig"] = sig_final
    if st.session_state.get("final_sig") != sig_final:
        st.caption(f"Ajusta k-means con k = {k} y valida con {B} remuestras bootstrap "
                   "(IC95% de la silueta, estabilidad de Jaccard por cluster).")
        return

    with st.spinner(f"Ajustando y remuestreando {B} veces…"):
        centers, labels = _fit(X, k, int(n_init), seed)
        boot = _boot(X, k, labels, B, seed)
        sil_pts = kc.silhouette_per_point(X, labels)
    sil = float(sil_pts.mean())
    lo, hi = boot.silhouette_ci
    sizes = np.bincount(labels, minlength=k)
    unstable = [f"C{c + 1}" for c in range(k) if boot.jaccard_mean[c] < 0.75]

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Silueta media", f"{sil:.2f}", help="De −1 a 1. >0,5 estructura razonable; >0,7 fuerte.")
    r2.metric("IC95% bootstrap", f"{lo:.2f} – {hi:.2f}")
    r3.metric("ARI medio vs bootstrap", f"{np.nanmean(boot.ari):.2f}",
              help="Concordancia global de la partición con la obtenida en cada remuestra.")
    r4.metric("Clusters poco estables", ", ".join(unstable) if unstable else "ninguno",
              help="Jaccard medio < 0,75 (Hennig, 2007).")
    st.caption("Tamaño de los clusters: " + " · ".join(f"C{c + 1} n={n}" for c, n in enumerate(sizes)))

    t_sil, t_pca, t_prof, t_stab, t_imp, t_exp = st.tabs(
        ["Silueta", "PCA", "Perfiles", "Estabilidad", "Sensibilidad imputación", "Exportar"]
    )
    ids = rows[id_col].astype(str).to_numpy() if id_col else (rows.index.to_numpy() + 1)

    with t_sil:
        _chart(plots.silhouette_plot(sil_pts, labels), "silplot")
        neg = 100 * (sil_pts < 0).mean()
        st.caption(
            f"{neg:.0f}% de las observaciones tienen silueta negativa (están más cerca de otro cluster que del suyo)."
        )

    with t_pca:
        coords, c2, evr = kc.pca_2d(X, centers)
        _chart(plots.pca_scatter(coords, labels, c2, evr, ids, sil_pts), "pca")
        st.caption(f"Las dos componentes explican el {100 * evr.sum():.0f}% de la varianza: "
                   "si es bajo, el solapamiento visual no implica solapamiento real.")

    with t_prof:
        desc, zmat = kc.cluster_profiles(rows, cols, X, labels)
        _chart(plots.profile_heatmap(zmat), "heat")
        st.markdown("**Variables del modelo** · media (DE) en la escala original, antes de imputar")
        st.dataframe(desc, hide_index=True, width="stretch")
        if ext:
            st.markdown("**Variables descriptivas** (no usadas para formar los clusters)")
            st.dataframe(kc.describe_external(rows, ext, labels), hide_index=True, width="stretch")
        st.info(
            "No compares con contrastes de hipótesis las variables usadas para crear los clusters: "
            "difieren por construcción y los p-valores no son válidos. Los contrastes tienen sentido "
            "con variables externas (desenlaces, variables no incluidas)."
        )

    with t_stab:
        s1, s2 = st.columns(2)
        with s1:
            _chart(plots.jaccard_bars(boot.jaccard_mean, boot.jaccard_ci), "jac")
        with s2:
            _chart(plots.bootstrap_hist(boot.silhouettes, boot.silhouette_ci, sil), "bhist")
        st.dataframe(
            pd.DataFrame({
                "Cluster": [f"C{c + 1}" for c in range(k)],
                "n": sizes,
                "Jaccard medio": boot.jaccard_mean.round(2),
                "IC95%": [f"{a:.2f}–{b:.2f}" for a, b in boot.jaccard_ci],
                "Se disuelve (%)": boot.dissolved_pct.round(1),
                "Interpretación": [kc.jaccard_label(j) for j in boot.jaccard_mean],
            }),
            hide_index=True, width="stretch",
        )
        st.caption(
            "Estabilidad tipo clusterboot: en cada remuestra se reajusta k-means y se busca, para cada cluster "
            "original, el cluster más parecido (índice de Jaccard). «Se disuelve» = % de remuestras con Jaccard < 0,5."
        )

    with t_imp:
        st.caption("¿Cambian los clusters según cómo se imputen los valores perdidos? "
                   "Índice de Rand ajustado entre particiones (1 = idénticas, 0 = como al azar), "
                   "calculado sobre las filas comunes.")
        if prep.n_imputed_cells == 0 and work[cols].isna().sum().sum() == 0:
            st.success("No hay valores perdidos en estas variables: la imputación no influye.")
        else:
            with st.spinner("Reajustando con cada método…"):
                mat, n_rows = _sensitivity(work, tuple(cols), k, sc, knn, int(n_init), seed, tuple(logs))
            st.dataframe(mat.style.format("{:.2f}", na_rep="—"), width="stretch")
            st.caption(" · ".join(f"{kc.IMPUTATION_METHODS[m]}: n={n}" for m, n in n_rows.items()))
            off = mat.values[~np.eye(len(mat), dtype=bool)]
            if off.size and np.nanmin(off) < 0.8:
                st.warning("Algún par de métodos da particiones bastante distintas (ARI < 0,8): "
                           "los clusters dependen de la imputación.")

    with t_exp:
        out = rows.copy()
        out["cluster"] = labels + 1
        out["silueta"] = sil_pts.round(4)
        stamp = datetime.now().strftime("%Y%m%d-%H%M")
        st.download_button("Datos con cluster asignado (CSV)", out.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                           f"kmeans_k{k}_{stamp}.csv", "text/csv")
        params = {
            "fecha": datetime.now().isoformat(timespec="seconds"),
            "fuente": source, "filas_seleccionadas": len(selected) if only_sel else None,
            "variables": cols, "log1p": prep.log_cols, "imputacion": imp, "knn_vecinos": knn if imp == "knn" else None,
            "escalado": sc, "rango_k": [k_lo, k_hi], "k": k, "n_init": int(n_init), "semilla": seed,
            "bootstrap_B": B, "n_analizadas": len(X), "n_excluidas": prep.n_dropped,
            "celdas_imputadas": prep.n_imputed_cells,
            "silueta_media": round(sil, 4), "silueta_ic95": [round(lo, 4), round(hi, 4)],
            "ari_medio": round(float(np.nanmean(boot.ari)), 4),
            "jaccard_medio": {f"C{c + 1}": round(float(j), 4) for c, j in enumerate(boot.jaccard_mean)},
            "tamanos": {f"C{c + 1}": int(n) for c, n in enumerate(sizes)},
            "barrido": sweep.round(4).to_dict(orient="records"),
            "versiones": {"scikit-learn": sklearn.__version__, "pandas": pd.__version__, "numpy": np.__version__},
        }
        st.download_button("Parámetros y resultados (JSON)", json.dumps(params, ensure_ascii=False, indent=2),
                           f"kmeans_k{k}_{stamp}.json", "application/json")
        text = kc.methods_text(prep, k, int(n_init), seed, (k_lo, k_hi), sil, boot)
        st.markdown("**Texto de métodos** (borrador para adaptar)")
        st.text_area("Métodos", text, height=220, label_visibility="collapsed")
        st.download_button("Texto de métodos (.md)", text, f"kmeans_metodos_{stamp}.md", "text/markdown")
