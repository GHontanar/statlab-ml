"""Exportes sencillos: CSV con cluster y silueta, JSON de parámetros y resultados, métodos en Markdown."""
from __future__ import annotations

import json
import platform
from datetime import datetime
from importlib import metadata
from pathlib import Path

import numpy as np
import pandas as pd

from statlab import __version__

LIBRERIAS = ["numpy", "pandas", "scikit-learn", "matplotlib", "reportlab", "python-docx", "PySide6-Essentials",
             "pyqtgraph"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]


def fecha_larga(d: datetime | None = None) -> str:
    d = d or datetime.now()
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def versiones() -> list[tuple[str, str]]:
    out = [("StatLab", __version__), ("Python", platform.python_version())]
    for lib in LIBRERIAS:
        try:
            out.append((lib, metadata.version(lib)))
        except metadata.PackageNotFoundError:
            continue
    return out


def tabla_con_clusters(df: pd.DataFrame, filas: list[int], etiquetas: list[int], silueta: list[float]) -> pd.DataFrame:
    """Los datos cargados más `cluster` (1…k; vacío si la fila no entró en el modelo) y `silueta`."""
    out = df.copy()
    cluster = np.full(len(df), np.nan)
    sil = np.full(len(df), np.nan)
    cluster[filas] = np.asarray(etiquetas) + 1
    sil[filas] = silueta
    out["cluster"] = pd.array(np.where(np.isnan(cluster), pd.NA, cluster), dtype="Int64")
    out["silueta"] = sil
    return out


def escribir_csv(df: pd.DataFrame, path: str | Path) -> Path:
    """`;` como separador y coma decimal, UTF-8 con BOM: se abre bien en Excel en español."""
    path = Path(path)
    df.to_csv(path, sep=";", decimal=",", index=False, encoding="utf-8-sig")
    return path


def escribir_json(datos: dict, path: str | Path) -> Path:
    path = Path(path)
    path.write_text(json.dumps(datos, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return path


def escribir_md(texto: str, path: str | Path) -> Path:
    path = Path(path)
    path.write_text(texto, encoding="utf-8")
    return path


TIPOS = ("csv", "json", "md", "figuras", "pdf", "docx", "todo")
SUFIJOS = {"csv": ".csv", "json": ".json", "md": ".md", "pdf": ".pdf", "docx": ".docx"}


def escribir(tipo: str, exportacion, destino: str | Path, base: str = "statlab") -> list[Path]:
    """Escribe un exporte. Para «figuras» y «todo», `destino` es una carpeta."""
    from statlab.core.report import figures, pdf, word

    destino = Path(destino)
    if tipo in SUFIJOS:
        destino = destino if destino.suffix.lower() == SUFIJOS[tipo] else destino.with_suffix(SUFIJOS[tipo])
    if tipo == "csv":
        return [escribir_csv(exportacion.tabla, destino)]
    if tipo == "json":
        return [escribir_json(exportacion.json, destino)]
    if tipo == "md":
        return [escribir_md(exportacion.metodos, destino)]
    if tipo == "pdf":
        return [pdf.render(exportacion.bloques, destino, exportacion.titulo)]
    if tipo == "docx":
        return [word.render(exportacion.bloques, destino, exportacion.titulo)]
    if tipo == "figuras":
        out = []
        for nombre, figura in exportacion.figuras.items():
            out += figures.save(figura, destino, nombre)
        return out
    if tipo == "todo":
        destino.mkdir(parents=True, exist_ok=True)
        out = []
        for t, nombre in (("csv", f"{base}_datos_con_clusters"), ("json", f"{base}_resultados"),
                          ("md", f"{base}_metodos"), ("pdf", f"{base}_informe"), ("docx", f"{base}_informe")):
            out += escribir(t, exportacion, destino / nombre)
        out += escribir("figuras", exportacion, destino / "figuras")
        return out
    raise ValueError(f"Tipo de exporte desconocido: {tipo}")
