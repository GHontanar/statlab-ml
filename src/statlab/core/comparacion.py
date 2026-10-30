"""Comparación de dos soluciones de clustering (sin Qt).

Una «solución» es la lista paciente → cluster de un análisis. Puede venir de un
análisis de esta sesión, de otra sesión .statlab o de un CSV `id;cluster` hecho
fuera de StatLab; en los dos últimos casos se guarda como copia congelada.

Para comparar hay que emparejar a los pacientes:
- por identificador, si las dos tienen (es lo normal);
- por posición de fila, si vienen del mismo archivo (misma huella) y no hay ID.
Se compara en la intersección y se informa de los que solo están en una.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import adjusted_rand_score

from statlab import strings_es as S
from statlab.core.errors import ErrorUsuario


def huella(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()[:16]


@dataclass
class Solucion:
    nombre: str
    etiquetas: list[int]  # 0…k−1
    filas: list[int]  # posición de cada paciente en su tabla de origen
    ids: list[str] | None = None  # identificador de cada paciente (si lo hay)
    huella: str = ""  # del archivo de datos de origen
    origen: str = ""  # «analisis:a1», «sesion:archivo.statlab», «csv:archivo.csv»
    fecha: str = ""
    k: int = 0
    probabilidad: list[float] | None = None  # GMM: probabilidad máxima de cada paciente

    def __post_init__(self) -> None:
        if not self.k:
            self.k = int(max(self.etiquetas)) + 1 if self.etiquetas else 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Solucion:
        return cls(**d)

    def serie(self, por: str) -> pd.Series:
        """Etiquetas indexadas por identificador («id») o por fila («fila»)."""
        indice = self.ids if por == "id" else self.filas
        return pd.Series(self.etiquetas, index=pd.Index(indice))


def desde_resultado(nombre: str, r: dict[str, Any], df: pd.DataFrame, id_col: str | None, raw: bytes | None,
                    origen: str = "") -> Solucion:
    """Solución a partir del resultado «modelo_final» de un análisis."""
    filas = [int(f) for f in r["filas"]]
    ids = [str(v) for v in df[id_col].iloc[filas]] if id_col and id_col in df.columns else None
    prob = r.get("probabilidad", {}).get("p_max") if r.get("probabilidad") else None
    return Solucion(nombre=nombre, etiquetas=[int(e) for e in r["etiquetas"]], filas=filas, ids=ids,
                    huella=huella(raw) if raw else "", origen=origen, k=int(r["k"]), probabilidad=prob,
                    fecha=datetime.now().strftime("%d/%m/%Y"))


def desde_csv(path: str | Path) -> Solucion:
    """CSV o Excel con una columna de identificador y otra de cluster (la primera y la segunda,
    o las llamadas «id» y «cluster»)."""
    from statlab.core import io as sio

    path = Path(path)
    df = sio.read_table(path.name, path.read_bytes())
    cols = {str(c).strip().lower(): c for c in df.columns}
    id_col = cols.get("id", df.columns[0])
    cl_col = cols.get("cluster", df.columns[1] if df.columns[0] == id_col else df.columns[0])
    datos = df[[id_col, cl_col]].dropna()
    if datos.empty:
        raise ErrorUsuario(S.CMP_CSV_EMPTY)
    ids = datos[id_col].map(_id_texto).tolist()
    if len(set(ids)) != len(ids):
        raise ErrorUsuario(S.CMP_DUP_IDS.format(name=path.name))
    niveles = sorted(datos[cl_col].astype(str).unique(), key=_orden_natural)
    mapa = {v: i for i, v in enumerate(niveles)}
    etiquetas = [mapa[str(v)] for v in datos[cl_col].astype(str)]
    return Solucion(nombre=path.stem, etiquetas=etiquetas, filas=list(range(len(etiquetas))), ids=ids,
                    origen=f"csv:{path.name}", fecha=datetime.now().strftime("%d/%m/%Y"))


def _id_texto(v: Any) -> str:
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def _orden_natural(v: str):
    try:
        return (0, float(v.replace(",", ".")))
    except ValueError:
        return (1, v)


def steinley(ari: float) -> str:
    """Interpretación del ARI (Steinley, 2004)."""
    if np.isnan(ari):
        return "—"
    if ari >= 0.90:
        return S.ARI_EXCELLENT
    if ari >= 0.80:
        return S.ARI_GOOD
    if ari >= 0.65:
        return S.ARI_MODERATE
    if ari > 0:
        return S.ARI_POOR
    return S.ARI_CHANCE


def emparejar(a: Solucion, b: Solucion) -> tuple[pd.DataFrame, str, dict[str, int]]:
    """Tabla con las etiquetas de A y B de los pacientes comunes, cómo se han emparejado y
    cuántos hay solo en A y solo en B."""
    if a.ids is not None and b.ids is not None:
        for s in (a, b):
            if len(set(s.ids)) != len(s.ids):
                raise ErrorUsuario(S.CMP_DUP_IDS.format(name=s.nombre))
        por = "id"
    elif a.huella and a.huella == b.huella:
        por = "fila"
    else:
        raise ErrorUsuario(S.CMP_CANNOT_MATCH)
    sa, sb = a.serie(por), b.serie(por)
    comunes = sa.index.intersection(sb.index)
    tabla = pd.DataFrame({"a": sa.loc[comunes], "b": sb.loc[comunes]})
    if a.filas and por == "id":
        tabla["fila_a"] = pd.Series(a.filas, index=pd.Index(a.ids)).loc[comunes]
    else:
        tabla["fila_a"] = comunes if por == "fila" else -1
    return tabla, por, {"comunes": len(comunes), "solo_a": len(sa) - len(comunes), "solo_b": len(sb) - len(comunes)}


def comparar(a: Solucion, b: Solucion, B: int = 1000, seed: int = 0) -> dict[str, Any]:
    tabla, por, n = emparejar(a, b)
    if n["comunes"] < 3:
        raise ErrorUsuario(S.CMP_TOO_FEW.format(n=n["comunes"]))
    ea, eb = tabla["a"].to_numpy(dtype=int), tabla["b"].to_numpy(dtype=int)
    ari = float(adjusted_rand_score(ea, eb))
    # IC del acuerdo: bootstrap de pacientes con sus etiquetas (no se reajusta nada)
    rng = np.random.default_rng(seed)
    boot = np.empty(B)
    for i in range(B):
        idx = rng.integers(0, len(ea), len(ea))
        boot[i] = adjusted_rand_score(ea[idx], eb[idx])
    lo, hi = np.nanpercentile(boot, [2.5, 97.5])

    cruzada = pd.crosstab(pd.Series(ea, name="a"), pd.Series(eb, name="b")).reindex(
        index=range(a.k), columns=range(b.k), fill_value=0)
    # Emparejamiento húngaro: qué cluster de B corresponde a cada uno de A (máxima coincidencia)
    filas_h, cols_h = linear_sum_assignment(-cruzada.to_numpy())
    pareja = {int(r): int(c) for r, c in zip(filas_h, cols_h, strict=True)}
    orden_b = [pareja[r] for r in range(a.k) if r in pareja] + [c for c in range(b.k) if c not in pareja.values()]
    concordantes = np.array([pareja.get(int(x)) == int(y) for x, y in zip(ea, eb, strict=True)])
    mismo_k = a.k == b.k
    filas_disc = tabla.loc[~concordantes, "fila_a"].astype(int).tolist()
    ids_disc = [str(i) for i in tabla.index[~concordantes]] if por == "id" else None
    fila_a = tabla["fila_a"].astype(int).to_numpy()
    flujos = [{"a": int(i), "b": int(j), "n": int(cruzada.iat[i, j]),
               "filas_a": fila_a[(ea == i) & (eb == j)].tolist()}
              for i in range(a.k) for j in range(b.k) if cruzada.iat[i, j] > 0]
    out = {
        "a": a.nombre, "b": b.nombre, "por": por, **n,
        "ari": ari, "ari_ic": [float(lo), float(hi)], "B": B, "interpretacion": steinley(ari),
        "k_a": a.k, "k_b": b.k, "mismo_k": mismo_k,
        "cruzada": cruzada.to_numpy().tolist(), "orden_b": orden_b, "pareja": pareja,
        "concordancia_pct": float(100 * concordantes.mean()) if mismo_k else None,
        "n_discordantes": int((~concordantes).sum()),
        "discordantes": {"fila_a": filas_disc, "ids": ids_disc,
                         "a": tabla.loc[~concordantes, "a"].astype(int).tolist(),
                         "b": tabla.loc[~concordantes, "b"].astype(int).tolist()},
        "flujos": flujos,
        "tamanos_a": np.bincount(ea, minlength=a.k).tolist(),
        "tamanos_b": np.bincount(eb, minlength=b.k).tolist(),
    }
    for nombre, s in (("prob_a", a), ("prob_b", b)):
        if s.probabilidad is not None:
            serie = pd.Series(s.probabilidad, index=pd.Index(s.ids if por == "id" else s.filas))
            p = serie.loc[tabla.index].to_numpy(dtype=float)
            out[nombre] = {"discordantes": float(np.mean(p[~concordantes])) if (~concordantes).any() else None,
                           "concordantes": float(np.mean(p[concordantes])) if concordantes.any() else None,
                           "por_discordante": p[~concordantes].tolist()}
    return out


@dataclass
class SesionConSoluciones:
    """Soluciones disponibles en otra sesión .statlab (para importarlas)."""

    nombre_archivo: str
    soluciones: list[Solucion] = field(default_factory=list)


def desde_sesion(path: str | Path) -> SesionConSoluciones:
    """Todas las soluciones (modelos finales) de otra sesión .statlab."""
    from statlab.core import session as ses
    from statlab.modules import available_modules

    path = Path(path)
    modulos = {m.id: m for m in available_modules()}
    proyecto = ses.abrir_proyecto(path, {mid: m.crear_estado for mid, m in modulos.items()})
    raw = proyecto.preparacion.raw if proyecto.preparacion else None
    out = SesionConSoluciones(path.name)
    for a in proyecto.analisis:
        r = a.estado.resultados.get("modelo_final")
        if not r or "error" in r:
            continue
        ds = a.estado.dataset
        nombre = a.nombre or f"{S.ANALYSIS_SHORT.get(a.modulo, a.modulo)} · k = {r['k']}"
        out.soluciones.append(desde_resultado(f"{nombre} ({path.stem})", r, ds.df, ds.identificador, raw,
                                              origen=f"sesion:{path.name}"))
    if not out.soluciones:
        raise ErrorUsuario(S.CMP_NO_SOLUTIONS.format(name=path.name))
    return out
