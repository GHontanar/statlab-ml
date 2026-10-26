"""Figuras para exportar (matplotlib, sin Qt): la misma paleta, símbolos y coma decimal que la app.

Se exportan en PNG a 300 ppp y en SVG. Se usa `matplotlib.figure.Figure` directamente
(sin pyplot) para poder generarlas desde un hilo de trabajo.
"""
from __future__ import annotations

import io
from contextlib import contextmanager
from importlib import resources
from pathlib import Path

import numpy as np
from matplotlib import font_manager, rc_context
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, MaxNLocator

from statlab import strings_es as S
from statlab.core import fmt

# Mismos valores que la interfaz (ui/theme/tokens.py), sin importar Qt.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
MARKERS = ["o", "s", "D", "^", "X", "P", "*", "v"]
DIVERGING = ["#1c5cab", "#6da7ec", "#f0efec", "#ec8a88", "#c43a3a"]
TEXT, MUTED, GRID, ACCENT = "#1C1C1A", "#6E6D68", "#E2E1DC", "#1F63BA"
SIZE_CM = (16, 9.5)

_font_family: str | None = None


def _register_fonts() -> str:
    """Registra Inter (empaquetada con la app) para que las figuras sean iguales en todos los equipos."""
    global _font_family
    if _font_family is None:
        fonts = resources.files("statlab.ui").joinpath("theme", "fonts")
        for name in ("Inter-Regular.ttf", "Inter-Medium.ttf", "Inter-SemiBold.ttf", "Inter-Bold.ttf"):
            with resources.as_file(fonts.joinpath(name)) as path:
                font_manager.fontManager.addfont(str(path))
        _font_family = "Inter"
    return _font_family


@contextmanager
def _style():
    with rc_context({
        "font.family": _register_fonts(),
        "font.size": 9,
        "axes.edgecolor": GRID,
        "axes.labelcolor": TEXT,
        "axes.titlesize": 10,
        "axes.titleweight": "semibold",
        "axes.titlelocation": "left",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "axes.axisbelow": True,
        "svg.fonttype": "path",
        "axes.unicode_minus": True,
    }):
        yield


def _coma(value, _pos=None) -> str:
    text = f"{value:.10g}"
    return text.replace("-", "−").replace(".", ",")


def _axes(fig: Figure, title: str, xlabel: str, ylabel: str):
    ax = fig.add_subplot(1, 1, 1)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.yaxis.set_major_formatter(FuncFormatter(_coma))
    ax.xaxis.set_major_formatter(FuncFormatter(_coma))
    return ax


def _figure() -> Figure:
    return Figure(figsize=(SIZE_CM[0] / 2.54, SIZE_CM[1] / 2.54), layout="constrained")


def _ring(ax, x, y) -> None:
    ax.scatter([x], [y], s=260, facecolors="none", edgecolors=ACCENT, linewidths=1.6, zorder=4)


# --- Barrido de k ------------------------------------------------------------
def elbow(sweep: dict, k: int | None) -> Figure:
    with _style():
        fig = _figure()
        ax = _axes(fig, S.CHART_ELBOW, S.AXIS_K, S.AXIS_INERTIA)
        ax.plot(sweep["ks"], sweep["inercia"], "-o", color=ACCENT, markersize=5, linewidth=1.8)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        if k in sweep["ks"]:
            _ring(ax, k, sweep["inercia"][sweep["ks"].index(k)])
    return fig


def silhouette_by_k(sweep: dict, k: int | None) -> Figure:
    with _style():
        fig = _figure()
        ax = _axes(fig, S.CHART_SIL, S.AXIS_K, S.AXIS_SIL)
        ks, y = np.asarray(sweep["ks"]), np.asarray(sweep["silueta"], dtype=float)
        boot = sweep.get("boot")
        if boot:
            lo, hi = np.asarray(boot["ic_inf"]), np.asarray(boot["ic_sup"])
            ax.errorbar(ks, y, yerr=[np.clip(y - lo, 0, None), np.clip(hi - y, 0, None)], fmt="none",
                        ecolor=MUTED, capsize=3, linewidth=1)
        ax.plot(ks, y, "-o", color=ACCENT, markersize=5, linewidth=1.8)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        if k in sweep["ks"]:
            _ring(ax, k, y[list(ks).index(k)])
    return fig


# --- Modelo final ------------------------------------------------------------
def _cluster_name(c: int) -> str:
    return f"C{c + 1}"


def silhouette_obs(r: dict) -> Figure:
    with _style():
        fig = _figure()
        ax = _axes(fig, S.SIL_TITLE, S.AXIS_OBS, S.AXIS_SIL_OBS)
        sil, labels = np.asarray(r["silueta_obs"]), np.asarray(r["etiquetas"])
        x0, centers = 0, []
        gap = max(3, len(sil) // 60)
        for c in range(r["k"]):
            vals = np.sort(sil[labels == c])[::-1]
            ax.bar(np.arange(x0, x0 + len(vals)), vals, width=1.0, color=SERIES[c], linewidth=0)
            centers.append(x0 + len(vals) / 2)
            x0 += len(vals) + gap
        ax.axhline(r["silueta_media"], color=TEXT, linestyle="--", linewidth=1)
        ax.axhline(0, color=MUTED, linewidth=0.8)
        ax.set_xticks(centers, [_cluster_name(c) for c in range(r["k"])])
        ax.grid(axis="x", visible=False)
    return fig


def pca(r: dict) -> Figure:
    with _style():
        fig = Figure(figsize=(SIZE_CM[0] / 2.54, 12 / 2.54), layout="constrained")
        var = r["pca"]["varianza"]
        ax = _axes(fig, S.PCA_TITLE, f"CP1 ({fmt.pct(100 * var[0])})", f"CP2 ({fmt.pct(100 * var[1])})")
        coords, labels = np.asarray(r["pca"]["coords"]), np.asarray(r["etiquetas"])
        centros = np.asarray(r["pca"]["centros"])
        for c in range(r["k"]):
            m = labels == c
            ax.scatter(coords[m, 0], coords[m, 1], s=16, marker=MARKERS[c], color=SERIES[c], alpha=0.8,
                       linewidths=0.3, edgecolors="white", label=f"{_cluster_name(c)} (n = {int(m.sum())})")
        for c, (x, y) in enumerate(centros):
            ax.scatter([x], [y], s=110, marker="D", color=SERIES[c], edgecolors=TEXT, linewidths=1.2, zorder=5)
            ax.annotate(_cluster_name(c), (x, y), xytext=(7, 6), textcoords="offset points", fontweight="semibold")
        ax.legend(frameon=False, loc="best")
    return fig


def heatmap(r: dict) -> Figure:
    with _style():
        z = np.asarray(r["perfiles"]["z"], dtype=float)
        cols = r["perfiles"]["columnas"]
        fig = Figure(figsize=(SIZE_CM[0] / 2.54, (2.5 + 1.0 * len(z)) / 2.54 * 1.6), layout="constrained")
        ax = fig.add_subplot(1, 1, 1)
        ax.set_title(S.HEATMAP_TITLE)
        cmap = LinearSegmentedColormap.from_list("statlab_div", DIVERGING)
        im = ax.imshow(z, cmap=cmap, vmin=-2, vmax=2, aspect="auto")
        ax.set_xticks(range(len(cols)), cols, rotation=30, ha="right")
        ax.set_yticks(range(len(z)), [_cluster_name(c) for c in range(len(z))])
        ax.grid(False)
        for spine in ax.spines.values():
            spine.set_visible(False)
        for i in range(z.shape[0]):
            for j in range(z.shape[1]):
                white = abs(z[i, j]) > 1.1
                ax.text(j, i, fmt.num(z[i, j], 2), ha="center", va="center", fontsize=8,
                        color="white" if white else TEXT)
        bar = fig.colorbar(im, ax=ax, shrink=0.8)
        bar.ax.yaxis.set_major_formatter(FuncFormatter(_coma))
        bar.set_label("z")
    return fig


def jaccard(r: dict) -> Figure:
    with _style():
        fig = _figure()
        ax = _axes(fig, S.JACCARD_TITLE, S.AXIS_CLUSTER, S.AXIS_JACCARD)
        jm = np.asarray(r["boot"]["jaccard_media"], dtype=float)
        ci = np.asarray(r["boot"]["jaccard_ic"], dtype=float)
        x = np.arange(1, r["k"] + 1)
        ax.axhline(0.75, color=MUTED, linestyle="--", linewidth=0.9)
        ax.axhline(0.60, color=MUTED, linestyle=":", linewidth=0.9)
        for c in range(r["k"]):
            ax.errorbar([x[c]], [jm[c]], yerr=[[max(jm[c] - ci[c, 0], 0)], [max(ci[c, 1] - jm[c], 0)]],
                        fmt=MARKERS[c], color=SERIES[c], ecolor=MUTED, capsize=4, markersize=8)
        ax.set_ylim(0, 1.05)
        ax.set_xticks(x, [_cluster_name(c) for c in range(r["k"])])
        ax.legend([Line2D([], [], color=MUTED, linestyle="--"), Line2D([], [], color=MUTED, linestyle=":")],
                  ["0,75", "0,60"], frameon=False, loc="lower right")
    return fig


def boot_histogram(r: dict) -> Figure:
    with _style():
        fig = _figure()
        ax = _axes(fig, S.HIST_TITLE, S.AXIS_SIL, S.AXIS_FREQ)
        sil = np.asarray([v for v in r["boot"]["silueta"] if v is not None], dtype=float)
        lo, hi = float(sil.min()), float(sil.max())
        if hi - lo < 0.01:
            mid = (lo + hi) / 2
            lo, hi = mid - 0.005, mid + 0.005
        ax.hist(sil, bins=min(25, max(5, len(sil) // 8)), range=(lo, hi), color=ACCENT, alpha=0.7)
        ax.axvline(r["silueta_media"], color=TEXT, linestyle="--", linewidth=1.2)
        if hi - lo < 0.05:
            mid = (lo + hi) / 2
            ax.set_xlim(mid - 0.025, mid + 0.025)
    return fig


# --- Salida ------------------------------------------------------------------
def png_bytes(fig: Figure, dpi: int = 300) -> bytes:
    buf = io.BytesIO()
    with _style():
        fig.savefig(buf, format="png", dpi=dpi, facecolor="white")
    return buf.getvalue()


def save(fig: Figure, folder: Path, name: str) -> list[Path]:
    """Guarda `name.png` (300 ppp) y `name.svg`."""
    folder.mkdir(parents=True, exist_ok=True)
    out = []
    with _style():
        for ext in ("png", "svg"):
            path = folder / f"{name}.{ext}"
            fig.savefig(path, format=ext, dpi=300, facecolor="white")
            out.append(path)
    return out
