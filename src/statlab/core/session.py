"""Archivo de sesión .statlab: un zip con todo lo necesario para restaurar un análisis.

- meta.json    versión del formato y de la app, fecha y módulo
- data.csv     los datos tal como se cargaron (UTF-8, punto decimal, precisión completa)
- state.json   columnas y tipos, roles, filas, parámetros de cada paso y estado del flujo
- results.json resultados serializados (sin los objetos de trabajo «_…»)

Nunca se usa pickle: un archivo de sesión no puede ejecutar código al abrirse.
Al abrir no se recalcula nada; lo que haga falta para seguir calculando (la
matriz preparada) se reconstruye bajo demanda.
"""
from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from statlab import __version__
from statlab import strings_es as S
from statlab.core.dataset import Dataset, Rol
from statlab.core.errors import ErrorUsuario
from statlab.core.estado import EstadoSesion, serializable
from statlab.core.flow import FlujoPasos

FORMATO = 1
SUFIJO = ".statlab"
_ARCHIVOS = ("meta.json", "data.csv", "state.json", "results.json")


def _dump(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, indent=1, allow_nan=False).encode("utf-8")


def guardar(path: str | Path, estado: EstadoSesion, modulo: str) -> Path:
    """Escribe la sesión (primero en un archivo temporal, para no dejar uno a medias)."""
    if estado.dataset is None:
        raise ErrorUsuario(S.SESSION_NOTHING)
    path = Path(path)
    if path.suffix.lower() != SUFIJO:
        path = path.with_suffix(SUFIJO)
    ds = estado.dataset
    meta = {
        "formato": FORMATO,
        "app": "StatLab",
        "version_app": __version__,
        "modulo": modulo,
        "fecha": datetime.now().isoformat(timespec="seconds"),
    }
    state = {
        "fuente": ds.fuente,
        "columnas": [{"nombre": c, "tipo": str(ds.df[c].dtype)} for c in ds.columnas],
        "roles": {c: r.value for c, r in ds.roles.items()},
        "log": sorted(ds.log),
        "solo_filas": None if ds.solo_filas is None else sorted(ds.solo_filas),
        "excluidas": sorted(ds.excluidas),
        "subgrupos": ds.subgrupos,
        "parametros": estado.parametros,
        "flujo": estado.flujo.to_dict(),
    }
    results = {paso: serializable(r) for paso, r in estado.resultados.items()}
    csv = ds.df.to_csv(index=False, lineterminator="\n").encode("utf-8")

    tmp = path.with_name(path.name + ".tmp")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("meta.json", _dump(meta))
        z.writestr("data.csv", csv)
        z.writestr("state.json", _dump(state))
        z.writestr("results.json", _dump(results))
    tmp.replace(path)
    return path


def _leer_datos(raw: bytes, columnas: list[dict]) -> pd.DataFrame:
    tipos = {c["nombre"]: c["tipo"] for c in columnas}
    texto = {n: "string" for n, t in tipos.items() if not (t.startswith(("float", "int")) or t == "bool")}
    # Solo la celda vacía es NA: un texto «NA» guardado tal cual vuelve igual.
    df = pd.read_csv(io.BytesIO(raw), dtype=texto, keep_default_na=False, na_values=[""])
    for nombre, tipo in tipos.items():
        if nombre in texto and tipo in ("str", "string"):
            df[nombre] = df[nombre].astype(tipo)  # tipo de texto de pandas, con NA
        elif nombre in texto:
            df[nombre] = df[nombre].astype(object).where(df[nombre].notna(), None)
        elif tipo.startswith("int") and not df[nombre].isna().any():
            df[nombre] = df[nombre].astype(tipo)
        elif tipo == "bool":
            df[nombre] = df[nombre].astype(bool)
    return df[[c["nombre"] for c in columnas]]


def abrir(path: str | Path, crear_estado: Callable[[], EstadoSesion], modulo: str) -> EstadoSesion:
    """Restaura una sesión. `crear_estado` da el estado vacío del módulo (pasos y valores por defecto)."""
    path = Path(path)
    try:
        with zipfile.ZipFile(path) as z:
            nombres = set(z.namelist())
            if not set(_ARCHIVOS) <= nombres:
                raise ErrorUsuario(S.SESSION_INVALID)
            meta = json.loads(z.read("meta.json"))
            state = json.loads(z.read("state.json"))
            results = json.loads(z.read("results.json"))
            raw = z.read("data.csv")
    except (zipfile.BadZipFile, json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ErrorUsuario(S.SESSION_INVALID) from e

    formato = int(meta.get("formato", 0))
    if formato > FORMATO:
        raise ErrorUsuario(S.SESSION_NEWER.format(version=meta.get("version_app", "?")))
    state, results = migrar(formato, state, results)
    if meta.get("modulo") != modulo:
        raise ErrorUsuario(S.SESSION_OTHER_MODULE.format(modulo=meta.get("modulo", "?")))

    estado = crear_estado()
    ds = Dataset(_leer_datos(raw, state["columnas"]), fuente=state.get("fuente", path.name))
    ds.roles = {c: Rol(r) for c, r in state["roles"].items() if c in ds.columnas}
    ds.log = {c for c in state["log"] if c in ds.columnas}
    ds.solo_filas = None if state["solo_filas"] is None else set(state["solo_filas"])
    ds.excluidas = set(state["excluidas"])
    ds.subgrupos = {k: list(v) for k, v in state["subgrupos"].items()}
    estado.dataset = ds
    for paso, params in state["parametros"].items():
        estado.params(paso).update(params)
    estado.flujo = FlujoPasos.from_dict(estado.flujo.ids, state["flujo"])
    estado.resultados = {p: r for p, r in results.items() if p in estado.flujo.ids}
    return estado


def migrar(formato: int, state: dict, results: dict) -> tuple[dict, dict]:
    """Adapta sesiones de formatos anteriores al actual (de momento solo existe el 1)."""
    if formato < 1:
        raise ErrorUsuario(S.SESSION_INVALID)
    return state, results
