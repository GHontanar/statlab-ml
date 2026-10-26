"""Gráficos Plotly para StatLab ML.

Paleta categórica validada (orden fijo, nunca ciclado) y, como codificación
secundaria, un símbolo distinto por cluster: en el PCA hay muchos pares de
colores juntos y el color no debe ser el único canal.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SYMBOLS = ["circle", "square", "diamond", "triangle-up", "x", "cross", "star", "triangle-down"]
MUTED = "#898781"
NEUTRAL = "#f0efec"
DIVERGING = [[0.0, "#1c5cab"], [0.25, "#6da7ec"], [0.5, NEUTRAL], [0.75, "#ec8a88"], [1.0, "#c43a3a"]]
MAX_CLUSTERS = len(SERIES)


def color(c: int) -> str:
    return SERIES[c % len(SERIES)]


def _base(fig: go.Figure, title: str, height: int = 340, **layout) -> go.Figure:
    layout.setdefault("margin", dict(l=10, r=10, t=48, b=10))
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=15)),
        height=height,
        hoverlabel=dict(font_size=12),
        separators=",.",          # coma decimal, punto de millar
        **layout,
    )
    return fig


def elbow(sweep: pd.DataFrame, k_sel: int | None = None) -> go.Figure:
    fig = go.Figure(
        go.Scatter(
            x=sweep["k"], y=sweep["Inercia"], mode="lines+markers",
            line=dict(width=2, color=SERIES[0]), marker=dict(size=9, color=SERIES[0]),
            hovertemplate="k = %{x}<br>Inercia = %{y:,.1f}<extra></extra>",
        )
    )
    if k_sel is not None and k_sel in set(sweep["k"]):
        y = float(sweep.loc[sweep["k"] == k_sel, "Inercia"].iloc[0])
        fig.add_annotation(x=k_sel, y=y, text=f"k = {k_sel}", showarrow=True, arrowhead=0, ay=-30)
    fig.update_xaxes(title="Número de clusters (k)", dtick=1)
    fig.update_yaxes(title="Inercia (suma de cuadrados intra)", rangemode="tozero")
    return _base(fig, "Método del codo", showlegend=False)


def silhouette_by_k(sweep: pd.DataFrame, boot_k: pd.DataFrame | None = None, k_sel: int | None = None) -> go.Figure:
    err = None
    if boot_k is not None:
        b = sweep[["k", "Silueta"]].merge(boot_k, on="k")
        err = dict(
            type="data", symmetric=False,
            array=(b["IC95 sup"] - b["Silueta"]).clip(lower=0),
            arrayminus=(b["Silueta"] - b["IC95 inf"]).clip(lower=0),
            color=MUTED, thickness=1.5, width=6,
        )
        custom = np.c_[b["IC95 inf"], b["IC95 sup"]]
        hover = "k = %{x}<br>Silueta = %{y:.3f}<br>IC95 boot %{customdata[0]:.3f}–%{customdata[1]:.3f}<extra></extra>"
    else:
        custom = None
        hover = "k = %{x}<br>Silueta = %{y:.3f}<extra></extra>"
    fig = go.Figure(
        go.Scatter(
            x=sweep["k"], y=sweep["Silueta"], mode="lines+markers", error_y=err, customdata=custom,
            line=dict(width=2, color=SERIES[0]), marker=dict(size=9, color=SERIES[0]),
            hovertemplate=hover,
        )
    )
    if k_sel is not None and k_sel in set(sweep["k"]):
        y = float(sweep.loc[sweep["k"] == k_sel, "Silueta"].iloc[0])
        fig.add_annotation(x=k_sel, y=y, text=f"k = {k_sel}", showarrow=True, arrowhead=0, ay=-30)
    fig.update_xaxes(title="Número de clusters (k)", dtick=1)
    fig.update_yaxes(title="Silueta media", range=[min(0, float(sweep["Silueta"].min()) - 0.05), 1])
    return _base(fig, "Silueta media por k" + (" (IC95% bootstrap)" if boot_k is not None else ""), showlegend=False)


def silhouette_plot(sil: np.ndarray, labels: np.ndarray) -> go.Figure:
    """Gráfico de silueta clásico: una barra por observación, ordenadas dentro de cada cluster."""
    k = labels.max() + 1
    n = len(sil)
    gap = max(2, int(0.02 * n))
    fig = go.Figure()
    y0 = 0
    for c in range(k):
        v = np.sort(sil[labels == c])
        pos = np.arange(y0, y0 + len(v))
        fig.add_trace(
            go.Bar(
                x=v, y=pos, orientation="h", width=1.0, marker=dict(color=color(c), line=dict(width=0)),
                name=f"Cluster {c + 1} (n={len(v)})",
                hovertemplate=f"Cluster {c + 1}<br>Silueta = %{{x:.3f}}<extra></extra>",
            )
        )
        fig.add_annotation(
            x=0, y=y0 + len(v) / 2, xref="paper", text=f"C{c + 1}", showarrow=False,
            xanchor="right", xshift=-4, font=dict(size=12),
        )
        y0 += len(v) + gap
    mean = float(np.mean(sil))
    fig.add_vline(x=mean, line=dict(color=MUTED, width=1.5, dash="dash"),
                  annotation_text=f"media {mean:.2f}".replace(".", ","), annotation_position="top")
    fig.add_vline(x=0, line=dict(color=MUTED, width=1))
    fig.update_yaxes(visible=False, autorange="reversed")
    fig.update_xaxes(title="Coeficiente de silueta", range=[min(-0.2, float(sil.min()) - 0.05), 1])
    return _base(fig, "Silueta por observación", height=420, bargap=0,
                 legend=dict(orientation="h", y=-0.18), margin=dict(l=40, r=10, t=48, b=10))


def pca_scatter(coords, labels, centers2, evr, ids=None, sil=None) -> go.Figure:
    k = labels.max() + 1
    fig = go.Figure()
    for c in range(k):
        m = labels == c
        custom = np.c_[
            np.asarray(ids)[m] if ids is not None else np.where(m)[0] + 1,
            sil[m] if sil is not None else np.full(m.sum(), np.nan),
        ]
        fig.add_trace(
            go.Scattergl(
                x=coords[m, 0], y=coords[m, 1], mode="markers", name=f"Cluster {c + 1}",
                marker=dict(size=8, color=color(c), symbol=SYMBOLS[c % len(SYMBOLS)], opacity=0.8,
                            line=dict(width=0.5, color="rgba(255,255,255,0.7)")),
                customdata=custom,
                hovertemplate=f"ID %{{customdata[0]}}<br>Cluster {c + 1}<br>Silueta %{{customdata[1]:.2f}}<extra></extra>",
            )
        )
    if centers2 is not None:
        fig.add_trace(
            go.Scatter(
                x=centers2[:, 0], y=centers2[:, 1], mode="markers", name="Centroides",
                text=[f"C{c + 1}" for c in range(k)],
                marker=dict(size=16, color=[color(c) for c in range(k)], symbol="diamond",
                            line=dict(width=2, color="#0b0b0b")),
                hovertemplate="Centroide %{text}<extra></extra>",
            )
        )
        for c in range(k):
            fig.add_annotation(
                x=centers2[c, 0], y=centers2[c, 1], text=f"<b>C{c + 1}</b>", showarrow=False, yshift=20,
                bgcolor="rgba(255,255,255,0.85)", bordercolor="rgba(11,11,11,0.25)", borderpad=2,
                font=dict(size=12, color="#0b0b0b"),
            )
    fig.update_xaxes(title=f"CP1 ({100 * evr[0]:.0f}% varianza)", zeroline=False)
    fig.update_yaxes(title=f"CP2 ({100 * evr[1]:.0f}% varianza)", zeroline=False)
    return _base(fig, "Clusters proyectados en las dos primeras componentes principales", height=460,
                 legend=dict(orientation="h", y=-0.15))


def profile_heatmap(zmat: pd.DataFrame) -> go.Figure:
    lim = max(1.0, float(np.nanmax(np.abs(zmat.values))))
    fig = go.Figure(
        go.Heatmap(
            z=zmat.values, x=list(zmat.columns), y=list(zmat.index),
            colorscale=DIVERGING, zmin=-lim, zmax=lim, zmid=0,
            text=np.round(zmat.values, 2), texttemplate="%{text:.2f}", textfont=dict(size=12, color="#0b0b0b"),
            xgap=2, ygap=2,
            colorbar=dict(title="z", thickness=12),
            hovertemplate="%{y}<br>%{x}: z = %{z:.2f}<extra></extra>",
        )
    )
    fig.update_yaxes(autorange="reversed")
    return _base(fig, "Perfil de cada cluster (media estandarizada de cada variable)",
                 height=120 + 50 * len(zmat))


def bootstrap_hist(sil: np.ndarray, ci: tuple[float, float], point: float) -> go.Figure:
    fig = go.Figure(
        go.Histogram(x=sil[~np.isnan(sil)], nbinsx=30, marker=dict(color=SERIES[0], line=dict(width=1, color="rgba(255,255,255,0.6)")),
                     hovertemplate="Silueta %{x}<br>%{y} remuestras<extra></extra>")
    )
    for x, txt in ((ci[0], "IC 2,5%"), (ci[1], "IC 97,5%")):
        fig.add_vline(x=x, line=dict(color=MUTED, width=1.5, dash="dash"), annotation_text=txt, annotation_position="top")
    fig.add_vline(x=point, line=dict(color="#0b0b0b", width=1.5), annotation_text="modelo", annotation_position="bottom right")
    vals = sil[~np.isnan(sil)]
    lo_x, hi_x = float(min(vals.min(), point)), float(max(vals.max(), point))
    mid, half = (lo_x + hi_x) / 2, max((hi_x - lo_x) / 2 * 1.15, 0.05)  # evita ejes degenerados
    fig.update_traces(xbins=dict(start=mid - half, end=mid + half, size=2 * half / 30))
    fig.update_xaxes(title="Silueta media en cada remuestra", range=[mid - half, mid + half], tickformat=".2f")
    fig.update_yaxes(title="Remuestras")
    return _base(fig, "Distribución bootstrap de la silueta", showlegend=False)


def jaccard_bars(jmean: np.ndarray, jci: np.ndarray) -> go.Figure:
    k = len(jmean)
    names = [f"C{c + 1}" for c in range(k)]
    fig = go.Figure(
        go.Bar(
            x=names, y=jmean, marker=dict(color=[color(c) for c in range(k)], cornerradius=4),
            error_y=dict(type="data", symmetric=False, array=jci[:, 1] - jmean, arrayminus=jmean - jci[:, 0],
                         color=MUTED, thickness=1.5, width=6),
            customdata=jci, texttemplate="%{y:.2f}", textposition="outside",
            hovertemplate="%{x}<br>Jaccard medio %{y:.2f}<br>IC95 %{customdata[0]:.2f}–%{customdata[1]:.2f}<extra></extra>",
        )
    )
    for y, txt in ((0.75, "estable ≥ 0,75"), (0.6, "dudoso < 0,60")):
        fig.add_hline(y=y, line=dict(color=MUTED, width=1, dash="dot"), annotation_text=txt,
                      annotation_position="top right")
    fig.update_yaxes(title="Jaccard medio (bootstrap)", range=[0, 1.08])
    return _base(fig, "Estabilidad de cada cluster", showlegend=False, bargap=0.45)
