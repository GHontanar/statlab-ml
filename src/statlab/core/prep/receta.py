"""Receta de preparación: pasos que se aplican en orden a los datos leídos.

- Los datos leídos nunca se modifican: `aplicar` trabaja sobre una copia.
- Las filas nunca se borran: excluir (también los duplicados) las marca con su
  motivo. Así las posiciones de fila (0…n−1) son estables y el diagrama de flujo
  de pacientes sale directamente de los pasos.
- Un paso que falla no detiene la receta: se informa y se salta, y los
  siguientes siguen aplicándose (los que dependan de él darán su propio aviso).
- Todo es JSON: la receta se guarda en la sesión y en las plantillas.
"""
from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from statlab import strings_es as S
from statlab.core.errors import ErrorUsuario
from statlab.core.prep import formula

# Tipos de columna que el usuario puede fijar
NUMERICA, CATEGORICA, ORDINAL, FECHA, TEXTO = "numerica", "categorica", "ordinal", "fecha", "texto"
TIPOS = (NUMERICA, CATEGORICA, ORDINAL, FECHA, TEXTO)
FORMATOS_FECHA = ("dma", "mda", "amd")  # día/mes/año, mes/día/año, año-mes-día


@dataclass
class Paso:
    tipo: str
    params: dict[str, Any] = field(default_factory=dict)
    activo: bool = True
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "tipo": self.tipo, "activo": self.activo, "params": self.params}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Paso:
        return cls(tipo=d["tipo"], params=dict(d.get("params", {})), activo=d.get("activo", True), id=d["id"])

    @property
    def descripcion(self) -> str:
        return describir(self)


@dataclass
class Receta:
    pasos: list[Paso] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"pasos": [p.to_dict() for p in self.pasos]}

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> Receta:
        return cls([Paso.from_dict(p) for p in (d or {}).get("pasos", [])])

    def añadir(self, paso: Paso) -> Paso:
        validar(paso)
        self.pasos.append(paso)
        return paso

    def quitar(self, paso_id: str) -> None:
        self.pasos = [p for p in self.pasos if p.id != paso_id]

    def mover(self, paso_id: str, delta: int) -> None:
        i = next(i for i, p in enumerate(self.pasos) if p.id == paso_id)
        j = max(0, min(len(self.pasos) - 1, i + delta))
        self.pasos.insert(j, self.pasos.pop(i))

    def paso(self, paso_id: str) -> Paso:
        return next(p for p in self.pasos if p.id == paso_id)


@dataclass
class InformePaso:
    id: str
    ok: bool = True
    mensaje: str = ""
    celdas: int = 0  # celdas cambiadas
    filas: int = 0  # filas excluidas por este paso (nuevas, no ya excluidas antes)
    columnas_nuevas: list[str] = field(default_factory=list)


@dataclass
class Preparado:
    df: pd.DataFrame
    excluidas: dict[int, str]  # posición de fila → motivo (el del primer paso que la excluye)
    informes: list[InformePaso]
    n_leidas: int

    @property
    def errores(self) -> list[InformePaso]:
        return [i for i in self.informes if not i.ok]

    def flujo(self) -> list[tuple[str, int]]:
        """Diagrama de flujo de pacientes: (motivo, n excluidos) por orden de la receta."""
        cuenta: dict[str, int] = {}
        for motivo in self.excluidas.values():
            cuenta[motivo] = cuenta.get(motivo, 0) + 1
        orden = list(dict.fromkeys(self.excluidas.values()))  # orden de inserción = orden de los pasos
        return [(m, cuenta[m]) for m in orden]


@dataclass
class _Ctx:
    df: pd.DataFrame
    excluidas: dict[int, str]


# --- Pasos --------------------------------------------------------------------

_NUM_TEXTO = re.compile(r"^\s*([<>]=?|≤|≥)?\s*([-+−]?\d+(?:[.,]\d+)?)\s*([^\d\s].*)?$")


def texto_a_numero(s: pd.Series, limites: str = "valor") -> tuple[pd.Series, int]:
    """Convierte texto a número: «12,3», «<0,5», «>200», «12,3 mg/dL».
    `limites`: «valor» usa el número de «<0,5» (0,5); «na» lo deja perdido.
    Devuelve la serie y cuántos valores no se pudieron leer (pasan a perdidos)."""
    if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
        return s.astype(float), 0
    txt = s.astype("string").str.strip()
    txt = txt.mask(txt.str.lower().isin({"", "na", "nan", "n/a", "nd", "-", "."}))
    m = txt.str.extract(_NUM_TEXTO)
    num = pd.to_numeric(m[1].str.replace(",", ".", regex=False).str.replace("−", "-", regex=False), errors="coerce")
    if limites == "na":
        num = num.mask(m[0].notna())
    fallidos = int((txt.notna() & m[1].isna()).sum())
    return num.astype(float), fallidos


_FORMATOS = {"dma": True, "mda": False}


def texto_a_fecha(s: pd.Series, formato: str) -> tuple[pd.Series, int]:
    if pd.api.types.is_datetime64_any_dtype(s):
        return s, 0
    txt = s.astype("string").str.strip()
    txt = txt.mask(txt == "")
    if formato == "amd":
        f = pd.to_datetime(txt, errors="coerce", yearfirst=True, dayfirst=False, format="mixed")
    else:
        f = pd.to_datetime(txt, errors="coerce", dayfirst=_FORMATOS[formato], format="mixed")
    return f, int((txt.notna() & f.isna()).sum())


def is_numeric_col(s: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s)


def _cambiadas(antes: pd.Series, despues: pd.Series) -> int:
    a, d = antes.astype("string"), despues.astype("string")
    distintos = (a != d).fillna(True) & ~(a.isna() & d.isna())
    return int(distintos.sum())


def _col(ctx: _Ctx, nombre: str) -> pd.Series:
    if nombre not in ctx.df.columns:
        raise ErrorUsuario(S.PREP_NO_COLUMN.format(col=nombre))
    return ctx.df[nombre]


def _destino(params: dict[str, Any], defecto: str) -> str:
    d = str(params.get("destino") or "").strip()
    return d or defecto


def _paso_tipo(ctx: _Ctx, p: dict[str, Any], inf: InformePaso) -> None:
    col, tipo = p["columna"], p["tipo"]
    s = _col(ctx, col)
    if tipo == NUMERICA:
        nuevo, fallidos = texto_a_numero(s, p.get("limites", "valor"))
        if fallidos:
            inf.mensaje = S.PREP_UNREADABLE.format(n=fallidos)
    elif tipo == FECHA:
        nuevo, fallidos = texto_a_fecha(s, p.get("formato", "dma"))
        if fallidos:
            inf.mensaje = S.PREP_UNREADABLE.format(n=fallidos)
    elif tipo == ORDINAL:
        orden = [str(v) for v in p.get("orden", [])]
        txt = s.astype("string").str.strip()
        presentes = [v for v in txt.dropna().unique() if v not in orden]
        nuevo = pd.Series(pd.Categorical(txt, categories=orden + sorted(presentes), ordered=True), index=s.index)
    elif tipo in (CATEGORICA, TEXTO):
        nuevo = s.astype("string").str.strip().mask(s.isna())
        nuevo = nuevo.mask(nuevo == "")
        if tipo == CATEGORICA:
            nuevo = nuevo.astype("category")
    else:
        raise ErrorUsuario(S.PREP_BAD_TYPE.format(tipo=tipo))
    ctx.df[col] = nuevo  # cambiar el tipo no cuenta como cambiar celdas; solo se avisa de lo ilegible


def _paso_perdidos(ctx: _Ctx, p: dict[str, Any], inf: InformePaso) -> None:
    """Valores que significan «perdido» (999, «-9»…) o los que cumplen una condición."""
    total = 0
    for col in p["columnas"]:
        s = _col(ctx, col)
        mask = pd.Series(False, index=s.index)
        valores = p.get("valores") or []
        if valores:
            txt = s.astype("string").str.strip()
            claves = {str(v).strip() for v in valores}
            claves |= {k.replace(",", ".") for k in claves} | {k.replace(".", ",") for k in claves}
            mask |= txt.isin(claves).fillna(False)
            if pd.api.types.is_numeric_dtype(s):
                nums = [float(str(v).replace(",", ".")) for v in valores if _es_numero(v)]
                mask |= s.isin(nums)
        if p.get("condicion"):
            mask |= formula._logico(formula.calcular(p["condicion"], ctx.df)).fillna(False).astype(bool)
        mask &= s.notna()
        total += int(mask.sum())
        ctx.df[col] = s.mask(mask)
    inf.celdas = total


def _es_numero(v: Any) -> bool:
    try:
        float(str(v).replace(",", "."))
        return True
    except ValueError:
        return False


def _paso_recodificar(ctx: _Ctx, p: dict[str, Any], inf: InformePaso) -> None:
    col = p["columna"]
    s = _col(ctx, col)
    mapa = {str(k).strip(): v for k, v in p["mapa"].items()}  # el texto se compara sin espacios en los bordes
    txt = s.astype("string").str.strip()
    nuevo = txt.map(lambda v: mapa.get(v, v) if v is not pd.NA else v).astype("string")
    vacios = {k for k, v in mapa.items() if v is None or str(v).strip() == ""}
    nuevo = nuevo.mask(txt.isin(vacios))
    destino = _destino(p, col)
    inf.celdas = _cambiadas(txt, nuevo)
    if isinstance(s.dtype, pd.CategoricalDtype):
        nuevo = nuevo.astype("category")
    if destino != col:
        inf.columnas_nuevas.append(destino)
    ctx.df[destino] = nuevo


def _paso_unidades(ctx: _Ctx, p: dict[str, Any], inf: InformePaso) -> None:
    """Multiplica por un factor (todas las filas o las que cumplen una condición)."""
    col = p["columna"]
    s = formula._num(_col(ctx, col))
    factor = float(p["factor"])
    if p.get("condicion"):
        mask = formula._logico(formula.calcular(p["condicion"], ctx.df)).fillna(False).astype(bool)
    else:
        mask = s.notna()
    mask &= s.notna()
    ctx.df[col] = s.where(~mask, s * factor)
    inf.celdas = int(mask.sum())


def _paso_categorizar(ctx: _Ctx, p: dict[str, Any], inf: InformePaso) -> None:
    col = p["columna"]
    s = formula._num(_col(ctx, col))
    destino = _destino(p, f"{col}_cat")
    if p.get("cuantiles"):
        q = int(p["cuantiles"])
        cortes = list(np.unique(s.quantile(np.linspace(0, 1, q + 1)[1:-1]).to_numpy()))
    else:
        cortes = sorted(float(c) for c in p["cortes"])
    bordes = [-np.inf, *cortes, np.inf]
    etiquetas = p.get("etiquetas") or _etiquetas_cortes(cortes)
    if len(etiquetas) != len(bordes) - 1:
        raise ErrorUsuario(S.PREP_CUT_LABELS.format(n=len(bordes) - 1))
    # [a, b): «< 25», «25–30», «≥ 30»
    cat = pd.cut(s, bordes, right=False, labels=etiquetas, ordered=True)
    ctx.df[destino] = cat
    inf.columnas_nuevas.append(destino)


def _etiquetas_cortes(cortes: list[float]) -> list[str]:
    from statlab.core import fmt

    def f(x: float) -> str:
        return fmt.num(x, 0 if float(x).is_integer() else fmt.column_decimals(pd.Series([x])))

    if not cortes:
        return [S.PREP_ALL]
    out = [f"< {f(cortes[0])}"]
    out += [f"{f(a)}–{f(b)}" for a, b in zip(cortes, cortes[1:], strict=False)]
    out.append(f"≥ {f(cortes[-1])}")
    return out


def _paso_calcular(ctx: _Ctx, p: dict[str, Any], inf: InformePaso) -> None:
    destino = _destino(p, "")
    if not destino:
        raise ErrorUsuario(S.PREP_NO_NAME)
    r = formula.calcular(p["formula"], ctx.df)
    if pd.api.types.is_bool_dtype(r):
        r = r.astype("Float64").astype(float)  # VERDADERO/FALSO → 1/0, útil como evento o indicador
    if destino not in ctx.df.columns:
        inf.columnas_nuevas.append(destino)
    ctx.df[destino] = r


_UNIDADES_T = {"dias": 1.0, "meses": 365.25 / 12, "anos": 365.25}


def _paso_fechas(ctx: _Ctx, p: dict[str, Any], inf: InformePaso) -> None:
    """Diferencia entre dos fechas (p. ej. edad a partir de la fecha de nacimiento)."""
    a = formula._fecha(_col(ctx, p["inicio"]))
    b = formula._fecha(_col(ctx, p["fin"]))
    destino = _destino(p, "")
    if not destino:
        raise ErrorUsuario(S.PREP_NO_NAME)
    t = (b - a).dt.days.astype(float) / _UNIDADES_T[p.get("unidad", "anos")]
    negativos = int((t < 0).sum())
    if negativos:
        inf.mensaje = S.PREP_NEGATIVE_TIME.format(n=negativos)
    ctx.df[destino] = t
    inf.columnas_nuevas.append(destino)


def _paso_seguimiento(ctx: _Ctx, p: dict[str, Any], inf: InformePaso) -> None:
    """Tiempo de seguimiento y evento a partir de fechas.

    tiempo = (fecha del evento si la hay; si no, último contacto) − inicio
    evento = 1 si hay fecha del evento, 0 si no (censurado)."""
    inicio = formula._fecha(_col(ctx, p["inicio"]))
    fecha_ev = formula._fecha(_col(ctx, p["evento"]))
    ultimo = formula._fecha(_col(ctx, p["ultimo_contacto"]))
    fin = fecha_ev.where(fecha_ev.notna(), ultimo)
    t = (fin - inicio).dt.days.astype(float) / _UNIDADES_T[p.get("unidad", "meses")]
    ev = fecha_ev.notna().astype(float).where(fin.notna() & inicio.notna())
    dt = _destino({"destino": p.get("destino_tiempo")}, "tiempo")
    de = _destino({"destino": p.get("destino_evento")}, "evento")
    avisos = []
    if (t < 0).any():
        avisos.append(S.PREP_NEGATIVE_TIME.format(n=int((t < 0).sum())))
    if t.isna().any():
        avisos.append(S.PREP_NO_FOLLOWUP.format(n=int(t.isna().sum())))
    inf.mensaje = " ".join(avisos)
    ctx.df[dt] = t
    ctx.df[de] = ev
    inf.columnas_nuevas += [dt, de]


def _excluir(ctx: _Ctx, mask: pd.Series, motivo: str, inf: InformePaso) -> None:
    nuevas = 0
    for pos in np.flatnonzero(mask.to_numpy(dtype=bool)):
        if int(pos) not in ctx.excluidas:
            ctx.excluidas[int(pos)] = motivo
            nuevas += 1
    inf.filas = nuevas


def _paso_excluir(ctx: _Ctx, p: dict[str, Any], inf: InformePaso) -> None:
    motivo = str(p.get("motivo") or "").strip()
    if not motivo:
        raise ErrorUsuario(S.PREP_NO_REASON)
    cond = formula._logico(formula.calcular(p["condicion"], ctx.df))
    sin_dato = int(cond.isna().sum())
    if sin_dato:
        inf.mensaje = S.PREP_EXCLUDE_NA.format(n=sin_dato)
    _excluir(ctx, cond.fillna(False).astype(bool), motivo, inf)


def _paso_duplicados(ctx: _Ctx, p: dict[str, Any], inf: InformePaso) -> None:
    cols = p.get("columnas") or None
    for c in cols or []:
        _col(ctx, c)
    sub = ctx.df if cols is None else ctx.df[cols]
    mask = sub.astype("string").duplicated(keep="first")
    if cols:
        mask &= sub.notna().all(axis=1)
    _excluir(ctx, mask, str(p.get("motivo") or S.PREP_DUPLICATE_REASON), inf)


def _paso_quitar(ctx: _Ctx, p: dict[str, Any], inf: InformePaso) -> None:
    for c in p["columnas"]:
        _col(ctx, c)
    ctx.df = ctx.df.drop(columns=p["columnas"])


def _paso_renombrar(ctx: _Ctx, p: dict[str, Any], inf: InformePaso) -> None:
    col, nuevo = p["columna"], str(p["nombre"]).strip()
    _col(ctx, col)
    if not nuevo:
        raise ErrorUsuario(S.PREP_NO_NAME)
    if nuevo != col and nuevo in ctx.df.columns:
        raise ErrorUsuario(S.PREP_NAME_TAKEN.format(col=nuevo))
    ctx.df = ctx.df.rename(columns={col: nuevo})


PASOS: dict[str, Callable[[_Ctx, dict[str, Any], InformePaso], None]] = {
    "tipo": _paso_tipo,
    "perdidos": _paso_perdidos,
    "recodificar": _paso_recodificar,
    "unidades": _paso_unidades,
    "categorizar": _paso_categorizar,
    "calcular": _paso_calcular,
    "fechas": _paso_fechas,
    "seguimiento": _paso_seguimiento,
    "excluir": _paso_excluir,
    "duplicados": _paso_duplicados,
    "quitar": _paso_quitar,
    "renombrar": _paso_renombrar,
}


def validar(paso: Paso) -> None:
    """Comprobación previa (lo que no depende de los datos): tipo conocido y fórmulas
    bien escritas. Así un error de sintaxis se ve al escribirla, no al aplicar."""
    if paso.tipo not in PASOS:
        raise ErrorUsuario(S.PREP_BAD_STEP.format(tipo=paso.tipo))
    for clave in ("formula", "condicion"):
        if paso.params.get(clave):
            formula.analizar(paso.params[clave])


def aplicar(datos: pd.DataFrame, receta: Receta) -> Preparado:
    ctx = _Ctx(df=datos.copy().reset_index(drop=True), excluidas={})
    informes = []
    for paso in receta.pasos:
        inf = InformePaso(paso.id)
        if paso.activo:
            antes = ctx.df.copy()
            excl_antes = dict(ctx.excluidas)
            try:
                PASOS[paso.tipo](ctx, paso.params, inf)
            except ErrorUsuario as e:
                ctx.df, ctx.excluidas = antes, excl_antes
                inf.ok, inf.mensaje, inf.celdas, inf.filas, inf.columnas_nuevas = False, str(e), 0, 0, []
            except (KeyError, TypeError, ValueError) as e:  # parámetros incompletos o datos inesperados
                ctx.df, ctx.excluidas = antes, excl_antes
                inf.ok, inf.mensaje = False, S.PREP_STEP_FAILED.format(detail=e)
        informes.append(inf)
    return Preparado(df=ctx.df, excluidas=ctx.excluidas, informes=informes, n_leidas=len(datos))


def describir(paso: Paso) -> str:
    """Frase corta para la lista de la receta."""
    p = paso.params
    t = paso.tipo
    try:
        if t == "tipo":
            return S.PREP_DESC_TYPE.format(col=p["columna"], tipo=S.PREP_TYPE_NAMES[p["tipo"]])
        if t == "perdidos":
            que = ", ".join(map(str, p.get("valores") or [])) or p.get("condicion", "")
            return S.PREP_DESC_MISSING.format(cols=", ".join(p["columnas"]), que=que)
        if t == "recodificar":
            return S.PREP_DESC_RECODE.format(col=p["columna"], n=len(p["mapa"]))
        if t == "unidades":
            return S.PREP_DESC_UNITS.format(col=p["columna"], factor=str(p["factor"]).replace(".", ","))
        if t == "categorizar":
            return S.PREP_DESC_CUT.format(col=p["columna"], dest=_destino(p, f"{p['columna']}_cat"))
        if t == "calcular":
            return f"{p.get('destino', '')} = {p['formula']}"
        if t == "fechas":
            return S.PREP_DESC_DATES.format(dest=p.get("destino", ""), a=p["inicio"], b=p["fin"])
        if t == "seguimiento":
            t_, e_ = p.get("destino_tiempo") or "tiempo", p.get("destino_evento") or "evento"
            return S.PREP_DESC_FOLLOWUP.format(t=t_, e=e_)
        if t == "excluir":
            return S.PREP_DESC_EXCLUDE.format(motivo=p.get("motivo", ""), cond=p["condicion"])
        if t == "duplicados":
            return S.PREP_DESC_DUPS.format(cols=", ".join(p.get("columnas") or []) or S.PREP_ALL_COLUMNS)
        if t == "quitar":
            return S.PREP_DESC_DROP.format(cols=", ".join(p["columnas"]))
        if t == "renombrar":
            return S.PREP_DESC_RENAME.format(col=p["columna"], nombre=p["nombre"])
    except KeyError:
        pass
    return t
