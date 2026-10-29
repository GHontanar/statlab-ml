"""Revisión automática de calidad: detecta problemas y propone, nunca corrige.

Cada problema puede traer una propuesta (un Paso de receta) que el usuario
acepta tras ver la vista previa. Las heurísticas son conservadoras: es mejor no
avisar de un problema dudoso que proponer un cambio equivocado.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from statlab import strings_es as S
from statlab.core.prep import receta as rc
from statlab.core.prep.diccionario import Diccionario

GRAVE, AVISO, INFO = "grave", "aviso", "info"
CODIGOS_PERDIDO = (99, 999, 9999, 99999, -9, -99, -999, -1)


@dataclass
class Problema:
    codigo: str
    nivel: str
    titulo: str
    detalle: str
    columna: str | None = None
    n: int = 0
    filas: list[int] = field(default_factory=list)  # posiciones afectadas (para resaltarlas)
    propuesta: rc.Paso | None = None


def _texto(s: pd.Series) -> bool:
    return not (pd.api.types.is_numeric_dtype(s) or pd.api.types.is_datetime64_any_dtype(s)
                or isinstance(s.dtype, pd.CategoricalDtype))


def _normalizar(v: str) -> str:
    v = unicodedata.normalize("NFKD", str(v)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", v).strip().casefold()


_FECHA = re.compile(r"^\s*(\d{1,4})[/\-.](\d{1,2})[/\-.](\d{1,4})(?:[ T]\d{1,2}:\d{2}(?::\d{2})?)?\s*$")


def formato_fecha(valores: pd.Series) -> tuple[str | None, bool]:
    """Deduce el formato de fechas en texto. Devuelve (formato, ambiguo).
    dd/mm se distingue de mm/dd por los valores mayores que 12."""
    m = valores.astype("string").str.extract(_FECHA).dropna()
    if m.empty:
        return None, False
    a, b, c = (pd.to_numeric(m[i]) for i in range(3))
    if (a > 31).all():
        return "amd", False
    if (a > 12).any() and (b <= 12).all():
        return "dma", False
    if (b > 12).any() and (a <= 12).all():
        return "mda", False
    return "dma", True  # todo ≤ 12: lo habitual en España, pero hay que confirmarlo


def _proporcion_numeros(s: pd.Series) -> float:
    present = s.dropna().astype("string").str.strip()
    present = present[present != ""]
    if present.empty:
        return 0.0
    num, fallidos = rc.texto_a_numero(present)
    return 1 - fallidos / len(present)


def _proporcion_fechas(s: pd.Series) -> float:
    present = s.dropna().astype("string").str.strip()
    present = present[present != ""]
    if present.empty:
        return 0.0
    return float(present.str.match(_FECHA).mean())


def revisar(df: pd.DataFrame, diccionario: Diccionario | None = None, id_col: str | None = None) -> list[Problema]:
    dic = diccionario or Diccionario()
    out: list[Problema] = []
    n = len(df)

    dup = df.astype("string").duplicated(keep="first")
    if dup.any():
        filas = list(np.flatnonzero(dup.to_numpy()))
        out.append(Problema("duplicados", GRAVE, S.Q_DUP_ROWS, S.Q_DUP_ROWS_DETAIL.format(n=len(filas)),
                            n=len(filas), filas=filas, propuesta=rc.Paso("duplicados", {})))
    if id_col and id_col in df.columns:
        ids = df[id_col].astype("string")
        dup_id = ids.duplicated(keep=False) & ids.notna() & ~df.astype("string").duplicated(keep=False)
        if dup_id.any():
            filas = list(np.flatnonzero(dup_id.to_numpy()))
            out.append(Problema("id_duplicado", GRAVE, S.Q_DUP_ID.format(col=id_col),
                                S.Q_DUP_ID_DETAIL.format(n=len(filas)), columna=id_col, n=len(filas), filas=filas))

    for col in df.columns:
        s = df[col]
        present = s.dropna()
        if len(present) == 0:
            out.append(Problema("vacia", AVISO, S.Q_EMPTY.format(col=col), S.Q_EMPTY_DETAIL, columna=col,
                                propuesta=rc.Paso("quitar", {"columnas": [col]})))
            continue
        out += _revisar_columna(df, col, s, present, n, dic)
    return out


def _revisar_columna(df, col, s, present, n, dic) -> list[Problema]:
    out = []
    entrada = dic.get(col)
    if entrada and entrada.perdidos:
        txt = s.astype("string").str.strip()
        claves = set(entrada.perdidos) | {f"{float(v.replace(',', '.')):g}" for v in entrada.perdidos if _es_num(v)}
        mask = txt.isin(claves).fillna(False)
        if pd.api.types.is_numeric_dtype(s):
            mask |= s.isin([float(v.replace(",", ".")) for v in entrada.perdidos if _es_num(v)])
        if mask.any():
            filas = list(np.flatnonzero(mask.to_numpy()))
            out.append(Problema("codigo_perdido", AVISO, S.Q_DICT_MISSING.format(col=col),
                                S.Q_DICT_MISSING_DETAIL.format(n=len(filas), codes=", ".join(entrada.perdidos)),
                                columna=col, n=len(filas), filas=filas,
                                propuesta=rc.Paso("perdidos", {"columnas": [col], "valores": list(entrada.perdidos)})))
    if _texto(s):
        p_num = _proporcion_numeros(s)
        p_fecha = _proporcion_fechas(s)
        if p_fecha >= 0.8:
            formato, ambiguo = formato_fecha(present)
            detalle = S.Q_DATE_AMBIGUOUS if ambiguo else S.Q_DATE_DETAIL.format(fmt=S.PREP_DATE_FORMATS[formato])
            out.append(Problema("fecha_texto", AVISO if ambiguo else INFO, S.Q_DATE.format(col=col), detalle,
                                columna=col, propuesta=rc.Paso("tipo", {"columna": col, "tipo": rc.FECHA,
                                                                        "formato": formato})))
        elif p_num >= 0.8:
            num, fallidos = rc.texto_a_numero(s)
            limites = int(present.astype("string").str.strip().str.match(r"^([<>]=?|≤|≥)").sum())
            detalle = S.Q_NUMTEXT_DETAIL.format(n=fallidos)
            if limites:
                detalle += " " + S.Q_NUMTEXT_LIMITS.format(n=limites)
            out.append(Problema("numero_texto", AVISO, S.Q_NUMTEXT.format(col=col), detalle, columna=col,
                                n=fallidos, propuesta=rc.Paso("tipo", {"columna": col, "tipo": rc.NUMERICA})))
        else:
            out += _categorias(col, present)
        return out

    if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
        out += _codigos_perdido(col, s)
        if entrada and (entrada.minimo is not None or entrada.maximo is not None):
            fuera = pd.Series(False, index=s.index)
            if entrada.minimo is not None:
                fuera |= s < entrada.minimo
            if entrada.maximo is not None:
                fuera |= s > entrada.maximo
            if fuera.any():
                filas = list(np.flatnonzero(fuera.to_numpy()))
                cond = _condicion_limites(col, entrada.minimo, entrada.maximo)
                out.append(Problema("fuera_limites", GRAVE, S.Q_LIMITS.format(col=col),
                                    S.Q_LIMITS_DETAIL.format(n=len(filas)), columna=col, n=len(filas), filas=filas,
                                    propuesta=rc.Paso("perdidos", {"columnas": [col], "condicion": cond})))
        mezcla = unidades_mezcladas(s)
        if mezcla:
            factor, mask = mezcla
            filas = list(np.flatnonzero(mask.to_numpy()))
            umbral = float(np.sqrt(s[mask].min() * s[~mask & s.notna()].max()))
            cond = f"[{col}] > {_num_txt(umbral)}"
            out.append(Problema("unidades", GRAVE, S.Q_UNITS.format(col=col),
                                S.Q_UNITS_DETAIL.format(n=len(filas), factor=_num_txt(1 / factor)),
                                columna=col, n=len(filas), filas=filas,
                                propuesta=rc.Paso("unidades", {"columna": col, "factor": factor, "condicion": cond})))
    out += _vacia_constante(col, s, present, n)
    return out


def _es_num(v: str) -> bool:
    try:
        float(str(v).replace(",", "."))
        return True
    except ValueError:
        return False


def _num_txt(x: float) -> str:
    return (f"{x:.6g}").replace(".", ",")


def _condicion_limites(col: str, minimo, maximo) -> str:
    partes = []
    if minimo is not None:
        partes.append(f"[{col}] < {_num_txt(minimo)}")
    if maximo is not None:
        partes.append(f"[{col}] > {_num_txt(maximo)}")
    return partes[0] if len(partes) == 1 else f"O({partes[0]}; {partes[1]})"


def _categorias(col: str, present: pd.Series) -> list[Problema]:
    """Mismas categorías escritas de varias formas: «Hombre», «hombre », «HOMBRE»."""
    txt = present.astype("string")
    if txt.nunique() > 50:
        return []
    grupos: dict[str, dict[str, int]] = {}
    for v, c in txt.value_counts().items():
        grupos.setdefault(_normalizar(v), {})[str(v)] = int(c)
    mapa = {}
    for variantes in grupos.values():
        if len(variantes) > 1:
            principal = max(variantes, key=lambda k: (variantes[k], k == k.strip()))
            mapa.update({v: principal.strip() for v in variantes if v != principal.strip()})
    if not mapa:
        return []
    ejemplos = ", ".join(f"«{k}»" for k in list(mapa)[:4])
    return [Problema("categorias", AVISO, S.Q_CATS.format(col=col), S.Q_CATS_DETAIL.format(ej=ejemplos),
                     columna=col, n=len(mapa), propuesta=rc.Paso("recodificar", {"columna": col, "mapa": mapa}))]


def _codigos_perdido(col: str, s: pd.Series) -> list[Problema]:
    """999, -9…: muy repetidos y lejos del resto de valores."""
    present = s.dropna()
    if len(present) < 20:
        return []
    out = []
    resto_max, resto_min = None, None
    for codigo in CODIGOS_PERDIDO:
        cuenta = int((present == codigo).sum())
        if cuenta < 2:
            continue
        resto = present[present != codigo]
        if resto.empty:
            continue
        resto_max, resto_min = resto.max(), resto.min()
        rango = resto_max - resto_min or 1.0
        lejos = codigo > resto_max + 0.5 * rango or codigo < resto_min - 0.5 * rango
        if codigo == -1 and resto_min >= 0:
            lejos = True
        if lejos:
            filas = list(np.flatnonzero((s == codigo).to_numpy()))
            out.append(Problema("codigo_perdido", AVISO, S.Q_MISSING_CODE.format(col=col, code=codigo),
                                S.Q_MISSING_CODE_DETAIL.format(n=cuenta, code=codigo), columna=col, n=cuenta,
                                filas=filas, propuesta=rc.Paso("perdidos", {"columnas": [col], "valores": [codigo]})))
    return out


def unidades_mezcladas(s: pd.Series) -> tuple[float, pd.Series] | None:
    """Detecta dos grupos de valores cuya razón es ≈10, 100 o 1000 (p. ej. Hb en g/dL
    y en g/L). Devuelve (factor que lleva el grupo alto a la escala del bajo, máscara
    del grupo alto) o None. Solo con valores positivos y ambos grupos de al menos el 3 %."""
    x = s.dropna()
    x = x[(x > 0) & ~x.isin(CODIGOS_PERDIDO)]  # 999 frente a ~100 no son unidades, es un código
    if len(x) < 30:
        return None
    lx = np.log10(x.to_numpy(dtype=float))
    orden = np.sort(lx)
    saltos = np.diff(orden)
    i = int(np.argmax(saltos))
    corte = (orden[i] + orden[i + 1]) / 2
    bajo, alto = lx[lx < corte], lx[lx >= corte]
    if min(len(bajo), len(alto)) < max(3, 0.03 * len(lx)) or len(np.unique(alto)) < 2:
        return None
    dif = float(np.median(alto) - np.median(bajo))
    salto = float(saltos[i])
    dispersion = max(float(np.ptp(bajo)), float(np.ptp(alto)))
    potencia = round(dif)
    if potencia < 1 or abs(dif - potencia) > 0.15 or salto < 0.3 or dispersion > 0.8:
        return None
    mask = pd.Series(False, index=s.index)
    mask[x.index[lx >= corte]] = True
    return 10.0 ** -potencia, mask


def _vacia_constante(col: str, s: pd.Series, present: pd.Series, n: int) -> list[Problema]:
    out = []
    p_na = 1 - len(present) / max(n, 1)
    if p_na >= 0.8:
        out.append(Problema("casi_vacia", AVISO, S.Q_MOSTLY_EMPTY.format(col=col),
                            S.Q_MOSTLY_EMPTY_DETAIL.format(p=round(100 * p_na)), columna=col))
    top = present.astype("string").value_counts(normalize=True)
    if len(present) >= 10 and not top.empty and top.iloc[0] >= 0.95 and present.nunique() > 0:
        out.append(Problema("casi_constante", INFO, S.Q_CONSTANT.format(col=col),
                            S.Q_CONSTANT_DETAIL.format(p=round(100 * top.iloc[0]), v=top.index[0]), columna=col))
    return out
