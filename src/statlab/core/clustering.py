"""Algoritmos de clustering con una interfaz común (sin Qt).

k-means, mezclas gaussianas (GMM) y jerárquico aglomerativo comparten el mismo
flujo: barrido de k con índices internos, ajuste final, estabilidad por
bootstrap (Jaccard por cluster, Hennig 2007), sensibilidad a la imputación y
texto de métodos. Lo propio de cada algoritmo (opciones, criterio de selección
como la inercia o el BIC, dendrograma, probabilidades de pertenencia) vive en su
clase `Algoritmo`.

Las etiquetas siempre se renumeran por tamaño (el cluster 1 es el más grande).
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import sklearn
from scipy.cluster.hierarchy import dendrogram, fcluster, linkage
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, calinski_harabasz_score, davies_bouldin_score
from sklearn.mixture import GaussianMixture

from statlab.core import fmt
from statlab.core import kmeans as km
from statlab.core.errors import ErrorUsuario
from statlab.core.kmeans import BootstrapResult, Progress, ShouldCancel, _check_cancel, _silhouette

COVARIANZAS = {
    "full": "Completa (cada cluster con su forma)",
    "tied": "Compartida (misma forma para todos)",
    "diag": "Diagonal (sin correlaciones)",
    "spherical": "Esférica (como k-means)",
}
ENLACES = {
    "ward": "Ward (grupos compactos)",
    "average": "Promedio (UPGMA)",
    "complete": "Completo (máxima distancia)",
}
MAX_N_JERARQUICO = 10_000  # la matriz de distancias crece con n²


@dataclass
class Ajuste:
    labels: np.ndarray  # 0…k−1, el 0 es el cluster más grande
    centros: np.ndarray  # (k, p): centroides (k-means) o medias de cada cluster
    probabilidades: np.ndarray | None = None  # (n, k), solo GMM
    modelo: Any = None


def _ordenar(labels: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    return km.relabel_by_size(labels, k)


def _medias(X: np.ndarray, labels: np.ndarray, k: int) -> np.ndarray:
    return np.vstack([X[labels == c].mean(axis=0) if np.any(labels == c) else np.full(X.shape[1], np.nan)
                      for c in range(k)])


def _cercano(centros: np.ndarray, X: np.ndarray) -> np.ndarray:
    d = ((X[:, None, :] - centros[None, :, :]) ** 2).sum(axis=2)
    d = np.where(np.isnan(d), np.inf, d)
    return d.argmin(axis=1)


class Algoritmo:
    id = ""
    nombre = ""
    criterio = ""  # nombre del criterio propio del barrido (inercia, BIC, altura…)
    criterio_menor_mejor = True
    usa_n_init = True
    n_init_boot = 5  # inicializaciones en cada remuestra bootstrap (el coste se multiplica por B)

    def opciones_defecto(self) -> dict[str, Any]:
        return {}

    def ajustar(self, X: np.ndarray, k: int, op: dict[str, Any], seed: int) -> Ajuste:
        raise NotImplementedError

    def predecir(self, aj: Ajuste, X: np.ndarray) -> np.ndarray:
        """Asigna puntos nuevos (para el bootstrap): por defecto, al centro más próximo."""
        return _cercano(aj.centros, X)

    def criterio_k(self, aj: Ajuste, X: np.ndarray) -> float:
        return float("nan")

    def barrido(self, X: np.ndarray, ks: list[int], op: dict[str, Any], seed: int,
                should_cancel: ShouldCancel | None = None, progress: Progress | None = None):
        """(k, Ajuste) para cada k. Se puede sobrescribir si hay un atajo (jerárquico)."""
        for i, k in enumerate(ks):
            _check_cancel(should_cancel)
            yield k, self.ajustar(X, k, op, seed)
            if progress:
                progress((i + 1) / len(ks))

    def extra_barrido(self, X: np.ndarray, ks: list[int], op: dict[str, Any], seed: int) -> dict[str, Any]:
        """Datos propios del algoritmo para el panel del barrido (BIC por covarianza, dendrograma…)."""
        return {}

    def texto_metodo(self, op: dict[str, Any], n_init: int, seed: int) -> str:
        raise NotImplementedError


class KMeansAlg(Algoritmo):
    id = "kmeans"
    nombre = "k-means"
    criterio = "inercia"

    def ajustar(self, X, k, op, seed):
        n_init = int(op.get("n_init", 10))
        m = KMeans(n_clusters=k, n_init=n_init, random_state=seed).fit(X)
        labels, mapa = _ordenar(m.labels_, k)
        centros = np.empty_like(m.cluster_centers_)
        centros[mapa] = m.cluster_centers_
        return Ajuste(labels, centros, modelo=m)

    def criterio_k(self, aj, X):
        return float(aj.modelo.inertia_)

    def texto_metodo(self, op, n_init, seed):
        return (f"un análisis de conglomerados k-means (scikit-learn {sklearn.__version__}; {n_init} "
                f"inicializaciones k-means++, semilla {seed})")


class GMMAlg(Algoritmo):
    id = "gmm"
    nombre = "mezclas gaussianas"
    criterio = "bic"
    n_init_boot = 1

    def opciones_defecto(self):
        return {"covarianza": "full"}

    def _modelo(self, X, k, cov, n_init, seed) -> GaussianMixture:
        return GaussianMixture(n_components=k, covariance_type=cov, n_init=n_init, random_state=seed,
                               reg_covar=1e-5, max_iter=300).fit(X)

    def ajustar(self, X, k, op, seed):
        cov = op.get("covarianza", "full")
        if cov not in COVARIANZAS:
            raise ErrorUsuario(f"Covarianza desconocida: {cov}")
        m = self._modelo(X, k, cov, int(op.get("n_init", 5)), seed)
        prob = m.predict_proba(X)
        labels, mapa = _ordenar(prob.argmax(axis=1), k)
        p = np.empty_like(prob)
        p[:, mapa] = prob
        return Ajuste(labels, _medias(X, labels, k), probabilidades=p, modelo=(m, mapa))

    def predecir(self, aj, X):
        m, mapa = aj.modelo
        return mapa[m.predict(X)]

    def criterio_k(self, aj, X):
        return float(aj.modelo[0].bic(X))

    def extra_barrido(self, X, ks, op, seed):
        """BIC y AIC de los cuatro tipos de covarianza: ayudan a elegir la forma de los clusters."""
        n_init = int(op.get("n_init", 5))
        bic: dict[str, list[float | None]] = {}
        aic: dict[str, list[float | None]] = {}
        for cov in COVARIANZAS:
            bic[cov], aic[cov] = [], []
            for k in ks:
                try:
                    m = self._modelo(X, k, cov, max(1, min(n_init, 3)), seed)
                    bic[cov].append(float(m.bic(X)))
                    aic[cov].append(float(m.aic(X)))
                except ValueError:  # covarianza singular con pocos datos
                    bic[cov].append(None)
                    aic[cov].append(None)
        return {"bic_covarianzas": bic, "aic_covarianzas": aic}

    def texto_metodo(self, op, n_init, seed):
        cov = {"full": "completa", "tied": "compartida", "diag": "diagonal", "spherical": "esférica"}[
            op.get("covarianza", "full")]
        return (f"un modelo de mezclas gaussianas (scikit-learn {sklearn.__version__}; matriz de covarianza "
                f"{cov}, {n_init} inicializaciones, semilla {seed}); cada observación se asignó al componente "
                f"de mayor probabilidad a posteriori")


class JerarquicoAlg(Algoritmo):
    id = "jerarquico"
    nombre = "jerárquico"
    criterio = "altura"
    usa_n_init = False

    def opciones_defecto(self):
        return {"enlace": "ward"}

    def _linkage(self, X, op) -> np.ndarray:
        enlace = op.get("enlace", "ward")
        if enlace not in ENLACES:
            raise ErrorUsuario(f"Enlace desconocido: {enlace}")
        if len(X) > MAX_N_JERARQUICO:
            raise ErrorUsuario(f"El clustering jerárquico admite hasta {MAX_N_JERARQUICO} filas.")
        return linkage(X, method=enlace, metric="euclidean")

    def _cortar(self, Z, X, k) -> Ajuste:
        raw = fcluster(Z, t=k, criterion="maxclust") - 1
        kk = int(raw.max()) + 1
        labels, _ = _ordenar(raw, max(kk, k))
        aj = Ajuste(labels, _medias(X, labels, k), modelo=Z)
        return aj

    def ajustar(self, X, k, op, seed):
        return self._cortar(self._linkage(X, op), X, k)

    def barrido(self, X, ks, op, seed, should_cancel=None, progress=None):
        Z = self._linkage(X, op)  # un solo árbol: cada k es un corte distinto
        for i, k in enumerate(ks):
            _check_cancel(should_cancel)
            yield k, self._cortar(Z, X, k)
            if progress:
                progress((i + 1) / len(ks))

    def criterio_k(self, aj, X):
        """Altura de la fusión que se deshace al pasar de k−1 a k grupos."""
        Z = aj.modelo
        k = int(aj.labels.max()) + 1
        return float(Z[-(k - 1), 2]) if k >= 2 else float("nan")

    def extra_barrido(self, X, ks, op, seed):
        return {"dendrograma": dendrograma(self._linkage(X, op))}

    def texto_metodo(self, op, n_init, seed):
        enlace = {"ward": "de Ward", "average": "promedio (UPGMA)", "complete": "completo"}[op.get("enlace", "ward")]
        return (f"un análisis de conglomerados jerárquico aglomerativo (SciPy; distancia euclídea, enlace "
                f"{enlace}), cortando el árbol en el número de grupos elegido")


def dendrograma(Z: np.ndarray, p: int = 40) -> dict[str, Any]:
    """Coordenadas para dibujar el dendrograma (truncado a las últimas `p` fusiones) y las
    alturas de corte de cada k."""
    d = dendrogram(Z, truncate_mode="lastp", p=p, no_plot=True, no_labels=True)
    alturas = Z[:, 2]
    cortes = {}
    for k in range(2, min(len(Z) + 1, 21)):
        alto, bajo = alturas[-(k - 1)], alturas[-k] if k <= len(Z) else 0.0
        cortes[str(k)] = float((alto + bajo) / 2)
    return {"icoord": d["icoord"], "dcoord": d["dcoord"], "cortes": cortes, "altura_max": float(alturas[-1])}


ALGORITMOS: dict[str, Algoritmo] = {a.id: a for a in (KMeansAlg(), GMMAlg(), JerarquicoAlg())}


def algoritmo(id_: str) -> Algoritmo:
    try:
        return ALGORITMOS[id_]
    except KeyError as e:
        raise ErrorUsuario(f"Algoritmo desconocido: {id_}") from e


# ---------------------------------------------------------------------------
# Barrido de k
# ---------------------------------------------------------------------------
def sweep(alg: Algoritmo, X: np.ndarray, ks: Iterable[int], op: dict[str, Any], seed: int = 0,
          progress: Progress | None = None, should_cancel: ShouldCancel | None = None) -> pd.DataFrame:
    ks = list(ks)
    filas = []
    for k, aj in alg.barrido(X, ks, op, seed, should_cancel, progress):
        lab = aj.labels
        unicos = len(np.unique(lab))
        filas.append({
            "k": k,
            "criterio": alg.criterio_k(aj, X),
            "Silueta": _silhouette(X, lab, seed),
            "Calinski-Harabasz": calinski_harabasz_score(X, lab) if unicos > 1 else np.nan,
            "Davies-Bouldin": davies_bouldin_score(X, lab) if unicos > 1 else np.nan,
            "Tamaño mínimo": int(np.bincount(lab, minlength=k).min()),
        })
    return pd.DataFrame(filas)


def sweep_bootstrap(alg: Algoritmo, X: np.ndarray, ks: Iterable[int], op: dict[str, Any], B: int = 50,
                    seed: int = 0, progress: Progress | None = None,
                    should_cancel: ShouldCancel | None = None) -> pd.DataFrame:
    """IC bootstrap de la silueta para cada k (ajuste en la remuestra, silueta en los datos originales)."""
    ks = list(ks)
    filas = []
    op_boot = {**op, "n_init": min(int(op.get("n_init", 5)), alg.n_init_boot)}
    for i, k in enumerate(ks):
        rng = np.random.default_rng(seed + 1000 * k)
        sil = np.full(B, np.nan)
        for b in range(B):
            _check_cancel(should_cancel)
            idx = rng.integers(0, len(X), len(X))
            aj = alg.ajustar(X[idx], k, op_boot, int(rng.integers(2**31 - 1)))
            sil[b] = _silhouette(X, alg.predecir(aj, X), seed + b)
            if progress:
                progress((i + (b + 1) / B) / len(ks))
        lo, hi = np.nanpercentile(sil, [2.5, 97.5])
        filas.append({"k": k, "Silueta media boot": np.nanmean(sil), "IC95 inf": lo, "IC95 sup": hi})
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# Estabilidad del modelo final
# ---------------------------------------------------------------------------
def bootstrap_validate(alg: Algoritmo, X: np.ndarray, k: int, ref_labels: np.ndarray, op: dict[str, Any],
                       B: int = 200, seed: int = 0, progress: Progress | None = None,
                       should_cancel: ShouldCancel | None = None) -> BootstrapResult:
    """Clusterboot (Hennig 2007) para cualquier algoritmo: ajuste en cada remuestra,
    asignación de todos los puntos originales, Jaccard por cluster en los puntos de la
    remuestra, silueta y ARI sobre los datos originales."""
    rng = np.random.default_rng(seed)
    n = len(X)
    op_boot = {**op, "n_init": min(int(op.get("n_init", 5)), alg.n_init_boot)}
    sil = np.full(B, np.nan)
    jac = np.full((B, k), np.nan)
    ari = np.full(B, np.nan)
    for b in range(B):
        _check_cancel(should_cancel)
        idx = rng.integers(0, n, n)
        uniq = np.unique(idx)
        aj = alg.ajustar(X[idx], k, op_boot, int(rng.integers(2**31 - 1)))
        lab_full = alg.predecir(aj, X)
        sil[b] = _silhouette(X, lab_full, seed + b)
        ari[b] = adjusted_rand_score(ref_labels, lab_full)
        ref_u, lab_u = ref_labels[uniq], lab_full[uniq]
        grupos = [lab_u == d for d in np.unique(lab_u)]
        for c in range(k):
            A = ref_u == c
            if A.any():
                jac[b, c] = max((A & G).sum() / (A | G).sum() for G in grupos)
        if progress:
            progress((b + 1) / B)
    lo, hi = np.nanpercentile(sil, [2.5, 97.5])
    j_ci = np.vstack([np.nanpercentile(jac[:, c], [2.5, 97.5]) if np.any(~np.isnan(jac[:, c]))
                      else [np.nan, np.nan] for c in range(k)])
    with np.errstate(invalid="ignore"):
        disuelto = 100 * np.nanmean(np.where(np.isnan(jac), np.nan, jac < 0.5), axis=0)
        media = np.nanmean(jac, axis=0)
    return BootstrapResult(B=B, silhouettes=sil, silhouette_ci=(float(lo), float(hi)), jaccard=jac,
                           jaccard_mean=media, jaccard_ci=j_ci, dissolved_pct=disuelto, ari=ari)


# ---------------------------------------------------------------------------
# Sensibilidad a la imputación
# ---------------------------------------------------------------------------
def imputation_sensitivity(alg: Algoritmo, df: pd.DataFrame, cols: list[str], k: int, scaling: str,
                           knn_neighbors: int, op: dict[str, Any], seed: int = 0,
                           methods: Iterable[str] = ("complete", "mean", "median", "knn"),
                           log_cols: Iterable[str] = (), progress: Progress | None = None,
                           should_cancel: ShouldCancel | None = None) -> tuple[pd.DataFrame, dict[str, int]]:
    """ARI entre las particiones obtenidas con cada método de imputación (filas comunes)."""
    partes: dict[str, pd.Series] = {}
    n_filas: dict[str, int] = {}
    methods = list(methods)
    for i, m in enumerate(methods):
        _check_cancel(should_cancel)
        if progress:
            progress(i / len(methods))
        try:
            p = km.prepare(df, cols, m, scaling, knn_neighbors, log_cols)
        except (ValueError, ErrorUsuario):
            continue
        if len(p.X) <= k:
            continue
        partes[m] = pd.Series(alg.ajustar(p.X, k, op, seed).labels, index=p.row_index)
        n_filas[m] = len(p.X)
    if progress:
        progress(1.0)
    nombres = list(partes)
    etiquetas = [km.IMPUTATION_METHODS[m] for m in nombres]
    mat = pd.DataFrame(np.nan, index=etiquetas, columns=etiquetas)
    for a in nombres:
        for b in nombres:
            comunes = partes[a].index.intersection(partes[b].index)
            if len(comunes) > 1:
                mat.loc[km.IMPUTATION_METHODS[a], km.IMPUTATION_METHODS[b]] = adjusted_rand_score(
                    partes[a].loc[comunes], partes[b].loc[comunes])
    return mat, n_filas


# ---------------------------------------------------------------------------
# Texto de métodos
# ---------------------------------------------------------------------------
def methods_text(alg: Algoritmo, prep: km.Prepared, k: int, op: dict[str, Any], n_init: int, seed: int,
                 ks: tuple[int, int], sil: float, boot: BootstrapResult | None) -> str:
    if alg.id == "kmeans":
        return km.methods_text(prep, k, n_init, seed, ks, sil, boot)
    base = km.methods_text(prep, k, n_init, seed, ks, sil, boot)
    # Mismo texto de preparación y validación; cambia la frase del algoritmo y el criterio de selección.
    inicio = base.index("sobre ")
    texto = f"Se aplicó {alg.texto_metodo(op, n_init, seed)} " + base[inicio:]
    criterio = {"gmm": "el criterio de información bayesiano (BIC) y el coeficiente de silueta medio",
                "jerarquico": "el dendrograma y el coeficiente de silueta medio"}[alg.id]
    return texto.replace("mediante el método del codo y el coeficiente de silueta medio", f"mediante {criterio}")


def describe_probabilidades(prob: np.ndarray, umbral: float = 0.8) -> dict[str, Any]:
    """Resumen de la probabilidad de pertenencia (GMM): máxima por paciente y frontera."""
    pmax = prob.max(axis=1)
    return {
        "p_max": pmax,
        "umbral": umbral,
        "n_frontera": int(np.sum(pmax < umbral)),
        "media": float(np.mean(pmax)),
        "texto": f"{int(np.sum(pmax < umbral))} pacientes con probabilidad máxima < {fmt.num(umbral, 1)}",
    }
