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


def test_acceptance_through_module():
    """El mismo criterio, por el camino de la app: preprocesar → barrer → ajustar (k = 3)."""
    import json

    from statlab.core.dataset import Dataset, Rol
    from statlab.core.estado import serializable
    from statlab.modules.kmeans.module import KMeansModule, ajustar, barrer, preprocesar

    estado = KMeansModule().crear_estado()
    estado.dataset = Dataset(sio.read_example())
    estado.dataset.asignar_rol(COLS, Rol.MODELO)
    estado.dataset.alternar_log(["ferritina"])
    estado.dataset.asignar_rol(["edad", "sexo"], Rol.DESCRIPTIVA)
    estado.resultados["preprocesado"] = preprocesar(estado)
    estado.params("elegir_k")["bootstrap"] = False
    sweep = barrer(estado, lambda f: None, lambda: False)
    assert sweep["mejor"]["silueta"] == 2 and round(sweep["silueta"][0], 3) == 0.557 and sweep["mejor"]["ch"] == 3
    estado.resultados["elegir_k"] = sweep
    estado.params("modelo_final").update(k=3, B=50)
    r = ajustar(estado, lambda f: None, lambda: False)
    assert r["tamanos"] == [109, 76, 55]
    assert round(r["silueta_media"], 2) == 0.52
    assert min(r["boot"]["jaccard_media"]) > 0.99 and r["inestables"] == 0
    assert r["boot"]["interpretacion"] == ["Muy estable"] * 3
    tab = pd.crosstab(estado.dataset.df.loc[r["filas"], "fenotipo_simulado"].to_numpy(), np.array(r["etiquetas"]))
    assert tab.loc["A"].tolist() == [109, 1, 0]
    assert len(r["perfiles"]["z"]) == 3 and len(r["pca"]["coords"]) == 240
    assert "12,66 (1,03)" in r["perfiles"]["tabla"]["filas"][0]  # coma decimal
    assert r["descriptivas"]["columnas"][:2] == ["Variable", "Nivel"]
    assert "Jaccard" in r["metodos"]
    json.dumps(serializable(r))  # todo el resultado es JSON
