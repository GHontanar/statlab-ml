"""Criterio de aceptación final del documento de traspaso (sección 11)."""
import numpy as np
import pandas as pd
import pytest

from statlab.core import io as sio
from statlab.core import kmeans as kc

COLS = ["hb", "vcm", "plaquetas", "neutrofilos", "hbf", "ferritina"]
SEED = 2026


@pytest.fixture(scope="module")
def prepared():
    df = sio.read_example()
    return df, kc.prepare(df, COLS, "knn", "standard", 5, log_cols=["ferritina"])


def test_sweep(prepared):
    _, p = prepared
    sw = kc.sweep_k(p.X, range(2, 9), n_init=20, seed=SEED)
    best_sil = sw.loc[sw["Silueta"].idxmax()]
    assert int(best_sil["k"]) == 2
    assert round(best_sil["Silueta"], 3) == 0.557
    assert int(sw.loc[sw["Calinski-Harabasz"].idxmax(), "k"]) == 3


def test_final_model_k3(prepared):
    df, p = prepared
    _, lab = kc.fit_kmeans(p.X, 3, n_init=20, seed=SEED)
    assert np.bincount(lab).tolist() == [109, 76, 55]
    assert round(kc._silhouette(p.X, lab), 2) == 0.52
    boot = kc.bootstrap_validate(p.X, 3, lab, B=50, seed=SEED)
    assert (boot.jaccard_mean > 0.99).all()
    # Fenotipos simulados A / C / B, salvo 1 caso A asignado a C2.
    tab = pd.crosstab(df.loc[p.row_index, "fenotipo_simulado"], lab)
    assert tab.loc["A"].tolist() == [109, 1, 0]
    assert tab.loc["C"].tolist() == [0, 75, 0]
    assert tab.loc["B"].tolist() == [0, 0, 55]
