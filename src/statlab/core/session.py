"""Archivo de sesión .statlab: un zip con todo lo necesario para restaurar el trabajo.

Formato 3 (una sesión, varios análisis sobre los mismos datos):

- meta.json         versión del formato y de la app, fecha y análisis activo
- data.csv          la tabla de análisis ya preparada (UTF-8, punto decimal, precisión completa)
- original.bin      el archivo de datos original, byte a byte
- prep.json         opciones de lectura, receta de preparación y diccionario
- analisis.json     lista de análisis: id, módulo, nombre, columnas y tipos, roles, filas,
                    parámetros de cada paso y estado del flujo
- resultados/<id>.json  resultados de cada análisis (sin los objetos de trabajo «_…»)

Formatos anteriores (se siguen abriendo): 1 = un análisis, sin preparación;
2 = un análisis con original.bin y prep.json (state.json y results.json).

Nunca se usa pickle: un archivo de sesión no puede ejecutar código al abrirse.
Al abrir no se recalcula nada; la matriz preparada se reconstruye bajo demanda.
"""
from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from statlab import __version__
from statlab import strings_es as S
from statlab.core.dataset import Dataset, Rol
from statlab.core.errors import ErrorUsuario
from statlab.core.estado import EstadoSesion, serializable
from statlab.core.flow import FlujoPasos

if TYPE_CHECKING:
    from statlab.core.prep.preparacion import Preparacion

FORMATO = 3
SUFIJO = ".statlab"


@dataclass
class AnalisisGuardado:
    id: str
    modulo: str
    nombre: str
    estado: EstadoSesion


@dataclass
class Proyecto:
    """Lo que contiene un archivo .statlab: la preparación (compartida) y los análisis."""

    analisis: list[AnalisisGuardado]
    activo: str = ""
    preparacion: Preparacion | None = None
    extra: dict[str, Any] = field(default_factory=dict)  # p. ej. soluciones importadas


def _dump(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, indent=1, allow_nan=False).encode("utf-8")


def _estado_a_dict(estado: EstadoSesion) -> dict[str, Any]:
    ds = estado.dataset
    return {
        "fuente": ds.fuente,
        "excluidas_receta": {str(k): v for k, v in sorted(ds.excluidas_receta.items())},
        "columnas": [{"nombre": c, "tipo": str(ds.df[c].dtype)} for c in ds.columnas],
        "roles": {c: r.value for c, r in ds.roles.items()},
        "log": sorted(ds.log),
        "solo_filas": None if ds.solo_filas is None else sorted(ds.solo_filas),
        "excluidas": sorted(ds.excluidas),
        "subgrupos": ds.subgrupos,
        "parametros": estado.parametros,
        "flujo": estado.flujo.to_dict(),
    }


def guardar_proyecto(path: str | Path, proyecto: Proyecto) -> Path:
    """Escribe la sesión (primero en un archivo temporal, para no dejar uno a medias)."""
    if not proyecto.analisis or proyecto.analisis[0].estado.dataset is None:
        raise ErrorUsuario(S.SESSION_NOTHING)
    path = Path(path)
    if path.suffix.lower() != SUFIJO:
        path = path.with_suffix(SUFIJO)
    meta = {
        "formato": FORMATO,
        "app": "StatLab",
        "version_app": __version__,
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "activo": proyecto.activo or proyecto.analisis[0].id,
    }
    lista = [{"id": a.id, "modulo": a.modulo, "nombre": a.nombre, "estado": _estado_a_dict(a.estado)}
             for a in proyecto.analisis]
    df = proyecto.analisis[0].estado.dataset.df  # todos los análisis comparten la tabla
    csv = df.to_csv(index=False, lineterminator="\n").encode("utf-8")

    tmp = path.with_name(path.name + ".tmp")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("meta.json", _dump(meta))
        z.writestr("data.csv", csv)
        z.writestr("analisis.json", _dump({"analisis": lista, "extra": proyecto.extra}))
        for a in proyecto.analisis:
            resultados = {paso: serializable(r) for paso, r in a.estado.resultados.items()}
            z.writestr(f"resultados/{a.id}.json", _dump(resultados))
        if proyecto.preparacion is not None:
            z.writestr("original.bin", proyecto.preparacion.raw)
            z.writestr("prep.json", _dump(proyecto.preparacion.to_dict()))
    tmp.replace(path)
    return path


def guardar(path: str | Path, estado: EstadoSesion, modulo: str, nombre: str = "") -> Path:
    """Atajo para una sesión con un solo análisis."""
    return guardar_proyecto(path, Proyecto([AnalisisGuardado("a1", modulo, nombre, estado)], "a1",
                                           estado.preparacion))


def _leer_datos(raw: bytes, columnas: list[dict]) -> pd.DataFrame:
    tipos = {c["nombre"]: c["tipo"] for c in columnas}
    texto = {n: "string" for n, t in tipos.items() if not (t.startswith(("float", "int")) or t == "bool")}
    # Solo la celda vacía es NA: un texto «NA» guardado tal cual vuelve igual.
    df = pd.read_csv(io.BytesIO(raw), dtype=texto, keep_default_na=False, na_values=[""])
    for nombre, tipo in tipos.items():
        if nombre in texto and tipo in ("str", "string"):
            df[nombre] = df[nombre].astype(tipo)  # tipo de texto de pandas, con NA
        elif tipo.startswith("datetime64"):
            df[nombre] = pd.to_datetime(df[nombre].astype(object).where(df[nombre].notna(), None))
        elif tipo == "category":
            df[nombre] = df[nombre].astype("category")
        elif nombre in texto:
            df[nombre] = df[nombre].astype(object).where(df[nombre].notna(), None)
        elif tipo.startswith("int") and not df[nombre].isna().any():
            df[nombre] = df[nombre].astype(tipo)
        elif tipo == "bool":
            df[nombre] = df[nombre].astype(bool)
    return df[[c["nombre"] for c in columnas]]


def _leer_zip(path: Path) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(path) as z:
            nombres = set(z.namelist())
            if not {"meta.json", "data.csv"} <= nombres:
                raise ErrorUsuario(S.SESSION_INVALID)
            out: dict[str, Any] = {"meta": json.loads(z.read("meta.json")), "data": z.read("data.csv")}
            out["prep"] = json.loads(z.read("prep.json")) if "prep.json" in nombres else None
            out["original"] = z.read("original.bin") if "original.bin" in nombres else None
            if "analisis.json" in nombres:
                out["analisis"] = json.loads(z.read("analisis.json"))
                out["resultados"] = {n[len("resultados/"):-len(".json")]: json.loads(z.read(n))
                                     for n in nombres if n.startswith("resultados/") and n.endswith(".json")}
            elif {"state.json", "results.json"} <= nombres:
                out["state"] = json.loads(z.read("state.json"))
                out["results"] = json.loads(z.read("results.json"))
            else:
                raise ErrorUsuario(S.SESSION_INVALID)
            return out
    except (zipfile.BadZipFile, json.JSONDecodeError, UnicodeDecodeError, KeyError) as e:
        raise ErrorUsuario(S.SESSION_INVALID) from e


def migrar(contenido: dict[str, Any]) -> dict[str, Any]:
    """Adapta sesiones de formatos anteriores al actual.

    1 → 2: no había preparación (la añade `_preparacion`) ni filas excluidas por la receta.
    2 → 3: un solo análisis en state.json/results.json pasa a la lista de análisis."""
    meta = contenido["meta"]
    formato = int(meta.get("formato", 0))
    if formato < 1:
        raise ErrorUsuario(S.SESSION_INVALID)
    if formato < 3:
        state = contenido.pop("state")
        state.setdefault("excluidas_receta", {})
        contenido["analisis"] = {"analisis": [{"id": "a1", "modulo": meta.get("modulo", "kmeans"), "nombre": "",
                                               "estado": state}], "extra": {}}
        contenido["resultados"] = {"a1": contenido.pop("results")}
        meta["activo"] = "a1"
    return contenido


def abrir_proyecto(path: str | Path, fabricas: dict[str, Callable[[], EstadoSesion]],
                   solo_modulo: str | None = None) -> Proyecto:
    """Restaura una sesión. `fabricas[modulo]()` da el estado vacío de cada módulo (pasos y
    valores por defecto). Los análisis de un módulo que esta versión no tiene dan error."""
    path = Path(path)
    contenido = _leer_zip(path)
    meta = contenido["meta"]
    if int(meta.get("formato", 0)) > FORMATO:
        raise ErrorUsuario(S.SESSION_NEWER.format(version=meta.get("version_app", "?")))
    contenido = migrar(contenido)
    lista = contenido["analisis"]["analisis"]
    if solo_modulo is not None:
        otros = [a["modulo"] for a in lista if a["modulo"] != solo_modulo]
        lista = [a for a in lista if a["modulo"] == solo_modulo]
        if not lista and otros:
            raise ErrorUsuario(S.SESSION_OTHER_MODULE.format(modulo=otros[0]))
    if not lista:
        raise ErrorUsuario(S.SESSION_INVALID)
    desconocidos = [a["modulo"] for a in lista if a["modulo"] not in fabricas]
    if desconocidos:
        raise ErrorUsuario(S.SESSION_OTHER_MODULE.format(modulo=desconocidos[0]))

    primero = lista[0]["estado"]
    fuente = primero.get("fuente", path.name)
    df = _leer_datos(contenido["data"], primero["columnas"])
    preparacion, df = _preparacion(contenido["prep"], contenido["original"], df, fuente)

    analisis = []
    for a in lista:
        estado = fabricas[a["modulo"]]()
        estado.preparacion = preparacion
        estado.dataset = _dataset(df, a["estado"], fuente)
        st = a["estado"]
        for paso, params in st["parametros"].items():
            estado.params(paso).update(params)
        estado.flujo = FlujoPasos.from_dict(estado.flujo.ids, st["flujo"])
        resultados = contenido["resultados"].get(a["id"], {})
        estado.resultados = {p: r for p, r in resultados.items() if p in estado.flujo.ids}
        analisis.append(AnalisisGuardado(a["id"], a["modulo"], a.get("nombre", ""), estado))
    activo = meta.get("activo") if any(a.id == meta.get("activo") for a in analisis) else analisis[0].id
    return Proyecto(analisis, activo, preparacion, contenido["analisis"].get("extra", {}))


def _dataset(df: pd.DataFrame, st: dict[str, Any], fuente: str) -> Dataset:
    ds = Dataset(df, fuente=st.get("fuente", fuente))
    ds.excluidas_receta = {int(k): v for k, v in st.get("excluidas_receta", {}).items()}
    ds.roles = {c: Rol(r) for c, r in st["roles"].items() if c in ds.columnas}
    ds.log = {c for c in st["log"] if c in ds.columnas}
    ds.solo_filas = None if st["solo_filas"] is None else set(st["solo_filas"])
    ds.excluidas = set(st["excluidas"])
    ds.subgrupos = {k: list(v) for k, v in st["subgrupos"].items()}
    return ds


def abrir(path: str | Path, crear_estado: Callable[[], EstadoSesion], modulo: str) -> EstadoSesion:
    """Atajo: el primer análisis del módulo `modulo` de la sesión."""
    proyecto = abrir_proyecto(path, {modulo: crear_estado}, solo_modulo=modulo)
    return proyecto.analisis[0].estado


def _preparacion(prep_d, original, df: pd.DataFrame, fuente: str):
    """Reconstruye la preparación. Devuelve (preparación, tabla de análisis)."""
    from statlab.core.prep.preparacion import Preparacion

    if prep_d is None or original is None:  # sesión de formato 1: el CSV guardado pasa a ser el «original»
        return Preparacion.desde_dataframe(fuente, df), df
    prep = Preparacion.from_dict(prep_d, original)
    try:
        rehecho = prep.aplicar().df
    except ErrorUsuario:
        return prep, df
    mismos = list(rehecho.columns) == list(df.columns) and len(rehecho) == len(df)
    return prep, (rehecho if mismos else df)
