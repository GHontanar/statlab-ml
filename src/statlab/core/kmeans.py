"""Motor de clustering k-means de StatLab.

Funciones puras (sin Qt) para poder testearlas y reutilizarlas:
preparación (imputación + escalado), barrido de k, ajuste final,
bootstrap (IC de la silueta, estabilidad de Jaccard por cluster, ARI),
PCA, perfiles y sensibilidad a la imputación.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import sklearn
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.impute import KNNImputer, SimpleImputer
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_samples,
    silhouette_score,
)
from sklearn.preprocessing import RobustScaler, StandardScaler

from statlab.core.errors import ErrorUsuario

IMPUTATION_METHODS = {
    "complete": "Casos completos (excluir filas con NA)",
    "mean": "Media",
    "median": "Mediana",
    "knn": "KNN (vecinos más próximos)",
}
SCALING_METHODS = {
    "standard": "Estandarizar (z-score)",
    "robust": "Robusto (mediana / IQR)",
    "none": "Sin escalar",
}

# Por encima de este tamaño la silueta se estima sobre una submuestra
# (su coste es O(n²)).
SILHOUETTE_MAX_N = 5000

Progress = Callable[[float], None]
ShouldCancel = Callable[[], bool]


class Cancelled(Exception):
    """El usuario ha cancelado un cálculo largo."""


def _check_cancel(should_cancel: ShouldCancel | None) -> None:
    if should_cancel is not None and should_cancel():
        raise Cancelled


# ---------------------------------------------------------------------------
# Inspección de datos
# ---------------------------------------------------------------------------
def numeric_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c])]


def missing_summary(df: pd.DataFrame, cols: Iterable[str]) -> pd.DataFrame:
    cols = list(cols)
    n = len(df)
    miss = df[cols].isna().sum()
    return pd.DataFrame(
        {"Variable": cols, "NA (n)": miss.values, "NA (%)": (100 * miss / max(n, 1)).round(1).values}
    )


# ---------------------------------------------------------------------------
# Preparación
# ---------------------------------------------------------------------------
@dataclass
class Prepared:
    X: np.ndarray                 # matriz final (imputada y escalada)
    row_index: pd.Index           # índices del DataFrame original usados
    columns: list[str]
    imputation: str
    scaling: str
    knn_neighbors: int
    log_cols: list[str]
    n_input: int
    n_dropped: int
    n_imputed_cells: int
    warnings: list[str] = field(default_factory=list)


def _scaler(kind: str):
    if kind == "standard":
        return StandardScaler()
    if kind == "robust":
        return RobustScaler()
    if kind == "none":
        return None
    raise ErrorUsuario(f"Escalado desconocido: {kind}")


def prepare(
    df: pd.DataFrame,
    cols: list[str],
    imputation: str = "knn",
    scaling: str = "standard",
    knn_neighbors: int = 5,
    log_cols: Iterable[str] = (),
) -> Prepared:
    """Imputa y escala las variables de clustering.

    Orden de operaciones:
      - media/mediana: imputar → escalar.
      - KNN: escalar → imputar → re-escalar, para que la distancia entre
        vecinos no esté dominada por la variable con mayor rango.
    """
    if len(cols) < 2:
        raise ErrorUsuario("Selecciona al menos 2 variables numéricas.")
    if imputation not in IMPUTATION_METHODS:
        raise ErrorUsuario(f"Imputación desconocida: {imputation}")

    warnings: list[str] = []
    data = df[cols].apply(pd.to_numeric, errors="coerce")
    n_input = len(data)

    all_na = [c for c in cols if data[c].isna().all()]
    if all_na:
        raise ErrorUsuario(f"Variables sin ningún valor: {', '.join(all_na)}")

    applied_log: list[str] = []
    for c in log_cols:
        if c not in data:
            continue
        if (data[c] < 0).any():
            warnings.append(f"{c}: tiene valores negativos, no se ha aplicado log.")
            continue
        data[c] = np.log1p(data[c])
        applied_log.append(c)

    if imputation == "complete":
        data = data.dropna()
    else:
        data = data.dropna(how="all")
    n_dropped = n_input - len(data)
    if len(data) < 10:
        raise ErrorUsuario(f"Solo quedan {len(data)} filas tras la preparación; son muy pocas para clustering.")
    n_imputed = 0 if imputation == "complete" else int(data.isna().sum().sum())

    constant = [c for c in cols if data[c].nunique(dropna=True) <= 1]
    if constant:
        warnings.append(f"Variables constantes (no aportan información): {', '.join(constant)}")

    arr = data.to_numpy(dtype=float)
    if imputation == "knn":
        if scaling == "none":
            warnings.append(
                "KNN sin escalar: la distancia entre vecinos la dominará la variable de mayor rango."
            )
            arr = KNNImputer(n_neighbors=knn_neighbors).fit_transform(arr)
        else:
            arr = _scaler(scaling).fit_transform(arr)          # ignora NaN al ajustar
            arr = KNNImputer(n_neighbors=knn_neighbors).fit_transform(arr)
            arr = _scaler(scaling).fit_transform(arr)
    else:
        if imputation in ("mean", "median"):
            arr = SimpleImputer(strategy=imputation).fit_transform(arr)
        sc = _scaler(scaling)
        if sc is not None:
            arr = sc.fit_transform(arr)

    if scaling == "none":
        warnings.append("Sin escalar: k-means usa distancia euclídea y las variables con más rango pesarán más.")
    pct_imp = 100 * n_imputed / max(arr.size, 1)
    if pct_imp > 20:
        warnings.append(f"Se ha imputado el {pct_imp:.0f}% de las celdas: interpreta los clusters con cautela.")

    return Prepared(
        X=arr,
        row_index=data.index,
        columns=list(cols),
        imputation=imputation,
        scaling=scaling,
        knn_neighbors=knn_neighbors,
        log_cols=applied_log,
        n_input=n_input,
        n_dropped=n_dropped,
        n_imputed_cells=n_imputed,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Métricas y ajuste
# ---------------------------------------------------------------------------
def _silhouette(X: np.ndarray, labels: np.ndarray, seed: int = 0) -> float:
    if len(np.unique(labels)) < 2:
        return float("nan")
    if len(X) > SILHOUETTE_MAX_N:
        return float(silhouette_score(X, labels, sample_size=SILHOUETTE_MAX_N, random_state=seed))
    return float(silhouette_score(X, labels))


def relabel_by_size(labels: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    """Renumera para que el cluster 0 sea el más grande. Devuelve (labels, mapa viejo→nuevo)."""
    counts = np.bincount(labels, minlength=k)
    order = np.argsort(-counts, kind="stable")
    mapping = np.empty(k, dtype=int)
    mapping[order] = np.arange(k)
    return mapping[labels], mapping


def fit_kmeans(X: np.ndarray, k: int, n_init: int = 20, seed: int = 0) -> tuple[KMeans, np.ndarray]:
    km = KMeans(n_clusters=k, n_init=n_init, random_state=seed).fit(X)
    labels, mapping = relabel_by_size(km.labels_, k)
    centers = np.empty_like(km.cluster_centers_)
    centers[mapping] = km.cluster_centers_
    km.cluster_centers_ = centers
    km.labels_ = labels
    return km, labels


def sweep_k(
    X: np.ndarray, ks: Iterable[int], n_init: int = 10, seed: int = 0,
    progress: Progress | None = None, should_cancel: ShouldCancel | None = None,
) -> pd.DataFrame:
    ks = list(ks)
    rows = []
    for i, k in enumerate(ks):
        _check_cancel(should_cancel)
        km = KMeans(n_clusters=k, n_init=n_init, random_state=seed).fit(X)
        lab = km.labels_
        rows.append(
            {
                "k": k,
                "Inercia": km.inertia_,
                "Silueta": _silhouette(X, lab, seed),
                "Calinski-Harabasz": calinski_harabasz_score(X, lab),
                "Davies-Bouldin": davies_bouldin_score(X, lab),
                "Tamaño mínimo": int(np.bincount(lab).min()),
            }
        )
        if progress:
            progress((i + 1) / len(ks))
    return pd.DataFrame(rows)


def elbow_k(ks: Iterable[int], inertia: Iterable[float]) -> int:
    """k del «codo»: el punto más alejado (por debajo) de la recta que une el primer y
    el último punto de la curva de inercia normalizada. Es orientativo."""
    ks = np.asarray(list(ks), dtype=float)
    y = np.asarray(list(inertia), dtype=float)
    if len(ks) < 3:
        return int(ks[0])
    x = (ks - ks[0]) / (ks[-1] - ks[0])
    rango = np.ptp(y)
    yn = (y - y.min()) / (rango if rango > 0 else 1)
    return int(ks[int(np.argmax((1 - x) - yn))])


def _boot_silhouettes(
    X: np.ndarray, k: int, B: int, n_init: int, seed: int,
    progress: Progress | None = None, should_cancel: ShouldCancel | None = None,
) -> np.ndarray:
    """Ajusta k-means en remuestras bootstrap y evalúa la silueta sobre
    los datos originales (evita el sesgo de los puntos duplicados)."""
    rng = np.random.default_rng(seed)
    n = len(X)
    out = np.full(B, np.nan)
    for b in range(B):
        _check_cancel(should_cancel)
        idx = rng.integers(0, n, n)
        km = KMeans(n_clusters=k, n_init=n_init, random_state=int(rng.integers(2**31 - 1))).fit(X[idx])
        out[b] = _silhouette(X, km.predict(X), seed + b)
        if progress:
            progress((b + 1) / B)
    return out


def sweep_k_bootstrap(
    X: np.ndarray, ks: Iterable[int], B: int = 50, n_init: int = 5, seed: int = 0,
    progress: Progress | None = None, should_cancel: ShouldCancel | None = None,
) -> pd.DataFrame:
    ks = list(ks)
    rows = []
    for i, k in enumerate(ks):
        inner = (lambda f, i=i: progress((i + f) / len(ks))) if progress else None
        sil = _boot_silhouettes(X, k, B, n_init, seed + 1000 * k, inner, should_cancel)
        lo, hi = np.nanpercentile(sil, [2.5, 97.5])
        rows.append({"k": k, "Silueta media boot": np.nanmean(sil), "IC95 inf": lo, "IC95 sup": hi})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Validación por bootstrap del modelo final
# ---------------------------------------------------------------------------
@dataclass
class BootstrapResult:
    B: int
    silhouettes: np.ndarray        # (B,)
    silhouette_ci: tuple[float, float]
    jaccard: np.ndarray            # (B, k) – NaN si el cluster no aparece en la remuestra
    jaccard_mean: np.ndarray       # (k,)
    jaccard_ci: np.ndarray         # (k, 2)
    dissolved_pct: np.ndarray      # (k,) % de remuestras con Jaccard < 0.5
    ari: np.ndarray                # (B,)


def jaccard_label(j: float) -> str:
    """Interpretación de Hennig (2007) para clusterboot."""
    if np.isnan(j):
        return "—"
    if j >= 0.85:
        return "Muy estable"
    if j >= 0.75:
        return "Estable"
    if j >= 0.60:
        return "Indica un patrón, pero dudoso"
    return "Inestable"


def bootstrap_validate(
    X: np.ndarray, k: int, ref_labels: np.ndarray, B: int = 200, n_init: int = 5, seed: int = 0,
    progress: Progress | None = None, should_cancel: ShouldCancel | None = None,
) -> BootstrapResult:
    """Estabilidad tipo clusterboot (Hennig 2007) + IC bootstrap de la silueta.

    En cada remuestra: se ajusta k-means, se asignan todos los puntos
    originales al centroide más próximo, y
      - silueta: sobre los datos originales;
      - Jaccard: para cada cluster original, máxima similitud con algún
        cluster bootstrap, evaluada en los puntos presentes en la remuestra;
      - ARI: concordancia global con la partición de referencia.
    """
    rng = np.random.default_rng(seed)
    n = len(X)
    sil = np.full(B, np.nan)
    jac = np.full((B, k), np.nan)
    ari = np.full(B, np.nan)
    for b in range(B):
        _check_cancel(should_cancel)
        idx = rng.integers(0, n, n)
        uniq = np.unique(idx)
        km = KMeans(n_clusters=k, n_init=n_init, random_state=int(rng.integers(2**31 - 1))).fit(X[idx])
        lab_full = km.predict(X)
        sil[b] = _silhouette(X, lab_full, seed + b)
        ari[b] = adjusted_rand_score(ref_labels, lab_full)
        ref_u, lab_u = ref_labels[uniq], lab_full[uniq]
        boot_sets = [lab_u == d for d in np.unique(lab_u)]
        for c in range(k):
            A = ref_u == c
            if not A.any():
                continue
            jac[b, c] = max((A & Bm).sum() / (A | Bm).sum() for Bm in boot_sets)
        if progress:
            progress((b + 1) / B)

    lo, hi = np.nanpercentile(sil, [2.5, 97.5])
    j_ci = np.vstack([np.nanpercentile(jac[:, c], [2.5, 97.5]) for c in range(k)])
    dissolved = 100 * np.nanmean(np.where(np.isnan(jac), np.nan, jac < 0.5), axis=0)
    return BootstrapResult(
        B=B,
        silhouettes=sil,
        silhouette_ci=(float(lo), float(hi)),
        jaccard=jac,
        jaccard_mean=np.nanmean(jac, axis=0),
        jaccard_ci=j_ci,
        dissolved_pct=dissolved,
        ari=ari,
    )


# ---------------------------------------------------------------------------
# Descripción de los clusters
# ---------------------------------------------------------------------------
def silhouette_per_point(X: np.ndarray, labels: np.ndarray) -> np.ndarray:
    return silhouette_samples(X, labels)


def pca_2d(X: np.ndarray, centers: np.ndarray | None = None):
    pca = PCA(n_components=2, random_state=0).fit(X)
    coords = pca.transform(X)
    c2 = pca.transform(centers) if centers is not None else None
    return coords, c2, pca.explained_variance_ratio_


def cluster_profiles(
    df_rows: pd.DataFrame, cols: list[str], X: np.ndarray, labels: np.ndarray
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (tabla descriptiva con valores originales, matriz de medias en z)."""
    k = labels.max() + 1
    raw = df_rows[cols].apply(pd.to_numeric, errors="coerce")
    rows = []
    for c in range(k):
        m = labels == c
        r = {"Cluster": c + 1, "n": int(m.sum()), "%": round(100 * m.mean(), 1)}
        for col in cols:
            v = raw.loc[m, col]
            r[col] = f"{v.mean():.2f} ({v.std():.2f})" if v.notna().any() else "—"
        rows.append(r)
    total = {"Cluster": "Total", "n": len(labels), "%": 100.0}
    for col in cols:
        v = raw[col]
        total[col] = f"{v.mean():.2f} ({v.std():.2f})"
    rows.append(total)
    desc = pd.DataFrame(rows)

    Xz = (X - X.mean(axis=0)) / np.where(X.std(axis=0) == 0, 1, X.std(axis=0))
    zmat = pd.DataFrame(
        [Xz[labels == c].mean(axis=0) for c in range(k)],
        index=[f"Cluster {c + 1}" for c in range(k)],
        columns=cols,
    )
    return desc, zmat


def describe_external(
    df_rows: pd.DataFrame, variables: list[str], labels: np.ndarray, max_levels: int = 6
) -> pd.DataFrame:
    """Variables no usadas en el clustering, descritas por cluster.
    Numéricas: mediana [RIC]; categóricas: n (%) por nivel."""
    k = labels.max() + 1
    out = []
    for var in variables:
        s = df_rows[var]
        if pd.api.types.is_numeric_dtype(s) and s.nunique() > max_levels:
            r = {"Variable": var, "Nivel": "mediana [RIC]"}
            for c in range(k):
                v = s[labels == c].dropna()
                r[f"Cluster {c + 1}"] = (
                    f"{v.median():.2f} [{v.quantile(.25):.2f}–{v.quantile(.75):.2f}]" if len(v) else "—"
                )
            r["NA"] = int(s.isna().sum())
            out.append(r)
        else:
            levels = s.astype("string").fillna("NA").value_counts().index[:max_levels]
            for lev in levels:
                r = {"Variable": var, "Nivel": str(lev)}
                for c in range(k):
                    sc = s[labels == c].astype("string").fillna("NA")
                    n_l = int((sc == lev).sum())
                    r[f"Cluster {c + 1}"] = f"{n_l} ({100 * n_l / max(len(sc), 1):.0f}%)"
                r["NA"] = ""
                out.append(r)
    return pd.DataFrame(out)


# ---------------------------------------------------------------------------
# Sensibilidad a la imputación
# ---------------------------------------------------------------------------
def imputation_sensitivity(
    df: pd.DataFrame, cols: list[str], k: int, scaling: str, knn_neighbors: int,
    n_init: int = 20, seed: int = 0, methods: Iterable[str] = ("complete", "mean", "median", "knn"),
    log_cols: Iterable[str] = (),
    progress: Progress | None = None, should_cancel: ShouldCancel | None = None,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """ARI entre las particiones obtenidas con cada método de imputación,
    calculado sobre las filas que comparten."""
    parts: dict[str, pd.Series] = {}
    n_rows: dict[str, int] = {}
    methods = list(methods)
    for i, m in enumerate(methods):
        _check_cancel(should_cancel)
        if progress:
            progress(i / len(methods))
        try:
            p = prepare(df, cols, m, scaling, knn_neighbors, log_cols)
        except ValueError:
            continue
        if len(p.X) <= k:
            continue
        _, lab = fit_kmeans(p.X, k, n_init, seed)
        parts[m] = pd.Series(lab, index=p.row_index)
        n_rows[m] = len(lab)
    if progress:
        progress(1.0)
    names = list(parts)
    labels = [IMPUTATION_METHODS[m] for m in names]
    mat = pd.DataFrame(np.nan, index=labels, columns=labels)
    for a in names:
        for b in names:
            common = parts[a].index.intersection(parts[b].index)
            if len(common) > 1:
                mat.loc[IMPUTATION_METHODS[a], IMPUTATION_METHODS[b]] = adjusted_rand_score(
                    parts[a].loc[common], parts[b].loc[common]
                )
    return mat, n_rows


# ---------------------------------------------------------------------------
# Reproducibilidad
# ---------------------------------------------------------------------------
def methods_text(
    prep: Prepared, k: int, n_init: int, seed: int, ks: tuple[int, int],
    sil: float, boot: BootstrapResult | None,
) -> str:
    """Párrafo de métodos/resultados listo para adaptar en un manuscrito."""
    imp = {
        "complete": "Se excluyeron las observaciones con algún valor perdido (análisis de casos completos)",
        "mean": "Los valores perdidos se imputaron con la media de cada variable",
        "median": "Los valores perdidos se imputaron con la mediana de cada variable",
        "knn": (
            "Los valores perdidos se imputaron mediante k vecinos más próximos "
            f"(k = {prep.knn_neighbors}) sobre las variables estandarizadas"
        ),
    }[prep.imputation]
    sc = {
        "standard": "Las variables se estandarizaron (media 0, desviación típica 1)",
        "robust": "Las variables se escalaron de forma robusta (mediana y rango intercuartílico)",
        "none": "Las variables se usaron sin escalar",
    }[prep.scaling]
    if prep.log_cols:
        sc = f"Se aplicó la transformación log(1+x) a {', '.join(prep.log_cols)}. " + sc
    txt = (
        f"Se aplicó un análisis de conglomerados k-means (scikit-learn {sklearn.__version__}; "
        f"{n_init} inicializaciones k-means++, semilla {seed}) sobre {len(prep.columns)} variables "
        f"({', '.join(prep.columns)}). {imp}; en total se imputaron {prep.n_imputed_cells} celdas "
        f"y se excluyeron {prep.n_dropped} de {prep.n_input} observaciones. {sc}. "
        f"El número de conglomerados se exploró entre k = {ks[0]} y k = {ks[1]} mediante el método del codo "
        f"y el coeficiente de silueta medio, seleccionándose k = {k} (silueta media {sil:.2f}"
    )
    if boot is not None:
        lo, hi = boot.silhouette_ci
        j = ", ".join(f"C{c + 1}: {v:.2f}" for c, v in enumerate(boot.jaccard_mean))
        txt += (
            f"; IC95% bootstrap {lo:.2f}–{hi:.2f}, {boot.B} remuestras). La estabilidad de cada "
            f"conglomerado se evaluó mediante remuestreo bootstrap con el índice de Jaccard medio "
            f"(Hennig, 2007), considerando estables valores ≥ 0,75 ({j}); el índice de Rand ajustado "
            f"medio respecto a la partición original fue {np.nanmean(boot.ari):.2f}."
        )
    else:
        txt += ")."
    return txt
