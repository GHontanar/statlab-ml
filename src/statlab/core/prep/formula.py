"""Lenguaje de fórmulas de la calculadora, al estilo de Excel en español.

    peso / (talla/100)^2
    SI([sexo] = "F"; 0,7; 0,9)
    AÑOS([fecha nacimiento]; [fecha inclusión])

- Columnas: un nombre simple (`peso`) o entre corchetes si tiene espacios u
  otros signos (`[fecha nacimiento]`).
- Coma decimal (`0,7`; también se acepta `0.7`) y `;` para separar argumentos.
- Operadores `+ - * / ^`, comparaciones `= <> < > <= >=`, `&` para unir textos.
- Un valor perdido en una entrada da un resultado perdido (salvo ESNA y SI con
  su condición conocida).

Es un analizador propio: la fórmula nunca se ejecuta como código Python, así
que un archivo de fórmulas compartido no puede hacer nada en el equipo.
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from statlab import strings_es as S
from statlab.core.errors import ErrorUsuario

# --- Árbol --------------------------------------------------------------------


@dataclass(frozen=True)
class Num:
    valor: float


@dataclass(frozen=True)
class Texto:
    valor: str


@dataclass(frozen=True)
class Logico:
    valor: bool


@dataclass(frozen=True)
class Col:
    nombre: str


@dataclass(frozen=True)
class Op:
    op: str
    izq: object
    der: object


@dataclass(frozen=True)
class Neg:
    arg: object


@dataclass(frozen=True)
class Func:
    nombre: str
    args: tuple


# --- Léxico -------------------------------------------------------------------

_TOKEN = re.compile(
    r"""
    (?P<esp>\s+)
  | (?P<num>\d+(?:[.,]\d+)?(?:[eE][+-]?\d+)?)
  | (?P<texto>"(?:[^"]|"")*")
  | (?P<col>\[[^\]]+\])
  | (?P<nombre>[^\W\d]\w*)
  | (?P<op><=|>=|<>|[-+*/^=<>&();])
    """,
    re.VERBOSE,
)


def _tokens(texto: str) -> list[tuple[str, str, int]]:
    out, i = [], 0
    while i < len(texto):
        m = _TOKEN.match(texto, i)
        if not m:
            raise ErrorUsuario(S.FORMULA_CHAR.format(char=texto[i], pos=i + 1))
        tipo = m.lastgroup
        if tipo != "esp":
            out.append((tipo, m.group(), i))
        i = m.end()
    out.append(("fin", "", len(texto)))
    return out


# --- Sintaxis (precedencia: comparación < & < + - < * / < ^ < unario) -----------

_PREC = {"=": 1, "<>": 1, "<": 1, ">": 1, "<=": 1, ">=": 1, "&": 2, "+": 3, "-": 3, "*": 4, "/": 4, "^": 6}


class _Parser:
    def __init__(self, texto: str):
        self.toks = _tokens(texto)
        self.i = 0

    def ver(self) -> tuple[str, str, int]:
        return self.toks[self.i]

    def tomar(self, valor: str | None = None) -> tuple[str, str, int]:
        tok = self.toks[self.i]
        if valor is not None and tok[1] != valor:
            raise ErrorUsuario(S.FORMULA_EXPECTED.format(what=valor, pos=tok[2] + 1))
        self.i += 1
        return tok

    def expr(self, minimo: int = 0):
        izq = self.unario()
        while True:
            tipo, op, _ = self.ver()
            prec = _PREC.get(op) if tipo == "op" else None
            if prec is None or prec < minimo:
                return izq
            self.tomar()
            # ^ es asociativo por la derecha; el resto por la izquierda
            der = self.expr(prec if op == "^" else prec + 1)
            izq = Op(op, izq, der)

    def unario(self):
        tipo, valor, _ = self.ver()
        if tipo == "op" and valor in "+-":
            self.tomar()
            arg = self.expr(5)  # -x^2 = -(x^2), como en matemáticas
            return arg if valor == "+" else Neg(arg)
        return self.atomo()

    def atomo(self):
        tipo, valor, pos = self.tomar()
        if tipo == "num":
            return Num(float(valor.replace(",", ".")))
        if tipo == "texto":
            return Texto(valor[1:-1].replace('""', '"'))
        if tipo == "col":
            return Col(valor[1:-1].strip())
        if tipo == "nombre":
            clave = _clave(valor)
            if self.ver()[1] == "(":
                if clave not in FUNCIONES:
                    raise ErrorUsuario(S.FORMULA_UNKNOWN_FUNC.format(name=valor))
                self.tomar("(")
                args = []
                if self.ver()[1] != ")":
                    args.append(self.expr())
                    while self.ver()[1] == ";":
                        self.tomar()
                        args.append(self.expr())
                self.tomar(")")
                nmin, nmax = FUNCIONES[clave][1]
                if not nmin <= len(args) <= nmax:
                    raise ErrorUsuario(S.FORMULA_NARGS.format(name=valor.upper()))
                return Func(clave, tuple(args))
            if clave in ("VERDADERO", "FALSO"):
                return Logico(clave == "VERDADERO")
            return Col(valor)
        if valor == "(":
            nodo = self.expr()
            self.tomar(")")
            return nodo
        if tipo == "fin":
            raise ErrorUsuario(S.FORMULA_INCOMPLETE)
        raise ErrorUsuario(S.FORMULA_UNEXPECTED.format(tok=valor, pos=pos + 1))


def _clave(nombre: str) -> str:
    """Nombre de función sin tildes y en mayúsculas: «años» → «ANOS»."""
    sin = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    return sin.upper()


def analizar(texto: str):
    """Texto → árbol. Lanza ErrorUsuario con la posición del problema."""
    if not texto or not texto.strip():
        raise ErrorUsuario(S.FORMULA_EMPTY)
    p = _Parser(texto)
    nodo = p.expr()
    tipo, valor, pos = p.ver()
    if tipo != "fin":
        raise ErrorUsuario(S.FORMULA_UNEXPECTED.format(tok=valor, pos=pos + 1))
    return nodo


def columnas(nodo) -> list[str]:
    """Columnas que usa una fórmula, en orden de aparición y sin repetir."""
    out: list[str] = []

    def visitar(n):
        if isinstance(n, Col):
            if n.nombre not in out:
                out.append(n.nombre)
        elif isinstance(n, Op):
            visitar(n.izq)
            visitar(n.der)
        elif isinstance(n, Neg):
            visitar(n.arg)
        elif isinstance(n, Func):
            for a in n.args:
                visitar(a)

    visitar(nodo)
    return out


def renombrar(texto: str, mapa: dict[str, str]) -> str:
    """Sustituye columnas de una fórmula (para aplicar una de «Mis fórmulas» a otro
    archivo). Devuelve la fórmula reescrita con todas las columnas entre corchetes."""
    return a_texto(_sustituir(analizar(texto), mapa))


def _sustituir(n, mapa):
    if isinstance(n, Col):
        return Col(mapa.get(n.nombre, n.nombre))
    if isinstance(n, Op):
        return Op(n.op, _sustituir(n.izq, mapa), _sustituir(n.der, mapa))
    if isinstance(n, Neg):
        return Neg(_sustituir(n.arg, mapa))
    if isinstance(n, Func):
        return Func(n.nombre, tuple(_sustituir(a, mapa) for a in n.args))
    return n


def a_texto(n) -> str:
    if isinstance(n, Num):
        v = n.valor
        return (str(int(v)) if v.is_integer() else repr(v)).replace(".", ",")
    if isinstance(n, Texto):
        return '"' + n.valor.replace('"', '""') + '"'
    if isinstance(n, Logico):
        return "VERDADERO" if n.valor else "FALSO"
    if isinstance(n, Col):
        return f"[{n.nombre}]"
    if isinstance(n, Neg):
        return f"-({a_texto(n.arg)})"
    if isinstance(n, Op):
        return f"({a_texto(n.izq)} {n.op} {a_texto(n.der)})"
    nombre = next(k for k in _NOMBRES if _clave(k) == n.nombre)
    return f"{nombre}(" + "; ".join(a_texto(a) for a in n.args) + ")"


# --- Evaluación ---------------------------------------------------------------


def _num(s: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(s):
        return s.astype(float)
    if pd.api.types.is_numeric_dtype(s):
        return s.astype(float)
    if pd.api.types.is_datetime64_any_dtype(s):
        raise ErrorUsuario(S.FORMULA_DATE_ARITH)
    out = pd.to_numeric(s, errors="coerce")
    if out.isna().sum() > s.isna().sum():
        raise ErrorUsuario(S.FORMULA_NOT_NUMBER)
    return out.astype(float)


def _logico(s: pd.Series) -> pd.Series:
    """Serie lógica con NA (boolean de pandas)."""
    if pd.api.types.is_bool_dtype(s):
        return s.astype("boolean")
    return (_num(s) != 0).astype("boolean").mask(s.isna())


def _fecha(s: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(s):
        return s
    raise ErrorUsuario(S.FORMULA_NOT_DATE)


def _comparar(op: str, a: pd.Series, b: pd.Series) -> pd.Series:
    na = a.isna() | b.isna()
    if all(pd.api.types.is_numeric_dtype(x) or pd.api.types.is_bool_dtype(x) for x in (a, b)):
        a, b = _num(a), _num(b)
    elif pd.api.types.is_datetime64_any_dtype(a) and pd.api.types.is_datetime64_any_dtype(b):
        pass
    else:
        if op not in ("=", "<>"):
            raise ErrorUsuario(S.FORMULA_TEXT_ORDER)
        a, b = a.astype("string").str.strip(), b.astype("string").str.strip()
    with np.errstate(invalid="ignore"):
        r = {"=": a == b, "<>": a != b, "<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b}[op]
    return pd.Series(r, index=a.index).astype("boolean").mask(na)


def _aritmetica(op: str, a: pd.Series, b: pd.Series) -> pd.Series:
    a, b = _num(a), _num(b)
    with np.errstate(all="ignore"):
        if op == "+":
            r = a + b
        elif op == "-":
            r = a - b
        elif op == "*":
            r = a * b
        elif op == "/":
            r = a / b
        else:
            r = a**b
    return r.replace([np.inf, -np.inf], np.nan)


def _si(cond, a, b=None):
    if b is None:
        b = pd.Series(np.nan, index=a.index)
    c = _logico(cond)
    out = b.where(c.fillna(False).to_numpy(dtype=bool) == False, a)  # noqa: E712
    return out.mask(c.isna())


def _min(*args):
    r = _num(args[0])
    for a in args[1:]:
        r = np.minimum(r, _num(a))
    return r


def _max(*args):
    r = _num(args[0])
    for a in args[1:]:
        r = np.maximum(r, _num(a))
    return r


def _unario(f: Callable) -> Callable:
    def g(x):
        with np.errstate(all="ignore"):
            return pd.Series(f(_num(x).to_numpy()), index=x.index).replace([np.inf, -np.inf], np.nan)

    return g


def _y(*args):
    r = _logico(args[0])
    for a in args[1:]:
        r = r & _logico(a)
    return r


def _o(*args):
    r = _logico(args[0])
    for a in args[1:]:
        r = r | _logico(a)
    return r


def _diferencia(unidad: str):
    def g(inicio, fin):
        a, b = _fecha(inicio), _fecha(fin)
        dias = (b - a).dt.days.astype(float)
        if unidad == "dias":
            return dias
        if unidad == "meses":
            return dias / (365.25 / 12)
        return dias / 365.25

    return g


def _redondear(x, d=None):
    dec = 0 if d is None else int(_num(d).iloc[0]) if len(d) else 0
    return _num(x).round(dec)


def _esna(x):
    return x.isna().astype("boolean")


def _unir(a, b):
    na = a.isna() | b.isna()
    return (a.astype("string") + b.astype("string")).mask(na)


# nombre visible → (función, (mín. args, máx. args))
_NOMBRES: dict[str, tuple[Callable, tuple[int, int]]] = {
    "SI": (_si, (2, 3)),
    "Y": (_y, (2, 30)),
    "O": (_o, (2, 30)),
    "NO": (lambda x: ~_logico(x), (1, 1)),
    "MIN": (_min, (1, 30)),
    "MAX": (_max, (1, 30)),
    "ABS": (_unario(np.abs), (1, 1)),
    "LN": (_unario(np.log), (1, 1)),
    "LOG10": (_unario(np.log10), (1, 1)),
    "EXP": (_unario(np.exp), (1, 1)),
    "RAIZ": (_unario(np.sqrt), (1, 1)),
    "REDONDEAR": (_redondear, (1, 2)),
    "ESNA": (_esna, (1, 1)),
    "AÑOS": (_diferencia("anos"), (2, 2)),
    "MESES": (_diferencia("meses"), (2, 2)),
    "DIAS": (_diferencia("dias"), (2, 2)),
}
FUNCIONES = {_clave(k): v for k, v in _NOMBRES.items()}
NOMBRES_FUNCIONES = list(_NOMBRES)


def evaluar(nodo, df: pd.DataFrame) -> pd.Series:
    """Evalúa el árbol sobre la tabla, fila a fila (vectorizado)."""
    n = len(df)

    def ev(x) -> pd.Series:
        if isinstance(x, Num):
            return pd.Series(np.full(n, x.valor), index=df.index)
        if isinstance(x, Texto):
            return pd.Series([x.valor] * n, index=df.index, dtype="string")
        if isinstance(x, Logico):
            return pd.Series([x.valor] * n, index=df.index, dtype="boolean")
        if isinstance(x, Col):
            if x.nombre not in df.columns:
                raise ErrorUsuario(S.FORMULA_NO_COLUMN.format(col=x.nombre))
            return df[x.nombre]
        if isinstance(x, Neg):
            return -_num(ev(x.arg))
        if isinstance(x, Op):
            a, b = ev(x.izq), ev(x.der)
            if x.op in _PREC and _PREC[x.op] == 1:
                return _comparar(x.op, a, b)
            if x.op == "&":
                return _unir(a, b)
            return _aritmetica(x.op, a, b)
        f, _ = FUNCIONES[x.nombre]
        return f(*[ev(a) for a in x.args])

    r = ev(nodo)
    if len(r) != n:  # pragma: no cover - defensivo
        raise ErrorUsuario(S.FORMULA_INCOMPLETE)
    return r


def calcular(texto: str, df: pd.DataFrame) -> pd.Series:
    return evaluar(analizar(texto), df)
