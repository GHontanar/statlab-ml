"""F3: GMM y jerárquico con la misma interfaz que k-means."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import adjusted_rand_score

from statlab.core import clustering as cl
from statlab.core import io as sio
from statlab.core import kmeans as km
from statlab.core.dataset import Dataset, Rol
from statlab.modules.kmeans.module import GMMModule, JerarquicoModule, KMeansModule, ajustar, barrer, preprocesar

COHORTE = Path(__file__).parents[2] / "ejemplos" / "cohorte_cardiometabolica_prueba.csv"
VARS = ["imc", "glucosa", "hba1c", "colesterol_ldl", "trigliceridos", "pcr", "tas", "creatinina"]
EJEMPLO = ["hb", "vcm", "plaquetas", "neutrofilos", "hbf", "ferritina"]


@pytest.fixture(scope="module")
def cohorte():
    df = pd.read_csv(COHORTE, sep=";", decimal=",", encoding="utf-8-sig")
    p = km.prepare(df, VARS, "knn", "standard", 5, ["trigliceridos", "pcr"])
    return p, df.loc[p.row_index, "perfil_simulado"].to_numpy()


def test_kmeans_generico_identico_al_de_siempre():
    X = km.prepare(sio.read_example(), EJEMPLO, "knn", "standard", 5, ["ferritina"]).X
    a = km.sweep_k(X, range(2, 9), 20, 2026)
    b = cl.sweep(cl.algoritmo("kmeans"), X, range(2, 9), {"n_init": 20}, 2026)
    assert np.allclose(a["Silueta"], b["Silueta"]) and np.allclose(a["Inercia"], b["criterio"])
    _, lab = km.fit_kmeans(X, 3, 20, 2026)
    assert (cl.algoritmo("kmeans").ajustar(X, 3, {"n_init": 20}, 2026).labels == lab).all()
    b1 = km.bootstrap_validate(X, 3, lab, B=10, seed=2026)
    b2 = cl.bootstrap_validate(cl.algoritmo("kmeans"), X, 3, lab, {"n_init": 20}, B=10, seed=2026)
    assert np.allclose(b1.jaccard_mean, b2.jaccard_mean)


@pytest.mark.parametrize("alg, op", [
    ("gmm", {"covarianza": "full", "n_init": 3}),
    ("gmm", {"covarianza": "diag", "n_init": 3}),
    ("jerarquico", {"enlace": "ward"}),
    ("jerarquico", {"enlace": "average"}),
])
def test_recuperan_los_perfiles(cohorte, alg, op):
    p, verdad = cohorte
    aj = cl.algoritmo(alg).ajustar(p.X, 4, op, 2026)
    assert adjusted_rand_score(verdad, aj.labels) > 0.95
    assert list(np.bincount(aj.labels)) == sorted(np.bincount(aj.labels), reverse=True)  # 1 = el más grande
    assert aj.centros.shape == (4, len(VARS))


def test_gmm_probabilidades_y_bic(cohorte):
    p, _ = cohorte
    A = cl.algoritmo("gmm")
    aj = A.ajustar(p.X, 4, {"covarianza": "diag"}, 0)
    assert aj.probabilidades.shape == (len(p.X), 4)
    assert (aj.probabilidades.argmax(axis=1) == aj.labels).all()  # columnas en el mismo orden que las etiquetas
    assert (A.predecir(aj, p.X) == aj.labels).all()
    extra = A.extra_barrido(p.X, [2, 3, 4, 5], {"n_init": 1}, 0)
    assert set(extra["bic_covarianzas"]) == set(cl.COVARIANZAS)
    d = cl.describe_probabilidades(aj.probabilidades)
    assert 0 <= d["n_frontera"] < len(p.X) and 0.5 < d["media"] <= 1


def test_jerarquico_dendrograma_y_altura(cohorte):
    p, _ = cohorte
    H = cl.algoritmo("jerarquico")
    sw = cl.sweep(H, p.X, range(2, 9), {"enlace": "ward"})
    alturas = sw["criterio"].tolist()
    assert alturas == sorted(alturas, reverse=True)
    dend = H.extra_barrido(p.X, list(range(2, 9)), {"enlace": "ward"}, 0)["dendrograma"]
    assert len(dend["icoord"]) == len(dend["dcoord"]) > 0
    assert dend["cortes"]["2"] > dend["cortes"]["3"] > dend["cortes"]["4"]


def _estado(mod, df, cols, log):
    e = mod.crear_estado()
    e.dataset = Dataset(df)
    e.dataset.asignar_rol(cols, Rol.MODELO)
    e.dataset.alternar_log(log)
    e.resultados["preprocesado"] = preprocesar(e)
    return e


@pytest.mark.parametrize("Mod", [GMMModule, JerarquicoModule])
def test_modulos_completos(Mod):
    """Criterio de aceptación de F3: k-means y GMM (o jerárquico) con k=4 coinciden (ARI ≥ 0,90)."""
    df = pd.read_csv(COHORTE, sep=";", decimal=",", encoding="utf-8-sig")
    mod = Mod()
    e = _estado(mod, df, VARS, ["trigliceridos", "pcr"])
    e.params("elegir_k").update(bootstrap=False)
    sweep = barrer(e, lambda f: None, lambda: False, mod.id)
    assert sweep["algoritmo"] == mod.id and sweep["mejor"]["silueta"] == 4
    e.resultados["elegir_k"] = sweep
    e.params("modelo_final").update(k=4, B=20)
    r = ajustar(e, lambda f: None, lambda: False, mod.id)
    assert r["k"] == 4 and r["algoritmo"] == mod.id
    assert ("probabilidad" in r) == (mod.id == "gmm")
    assert "jerárquico" in r["metodos"] or "mezclas gaussianas" in r["metodos"]

    ek = _estado(KMeansModule(), df, VARS, ["trigliceridos", "pcr"])
    ek.params("elegir_k").update(bootstrap=False)
    ek.resultados["elegir_k"] = barrer(ek, lambda f: None, lambda: False)
    ek.params("modelo_final").update(k=4, B=10)
    rk = ajustar(ek, lambda f: None, lambda: False)
    assert adjusted_rand_score(rk["etiquetas"], r["etiquetas"]) >= 0.90


def test_gmm_elige_por_bic_por_defecto():
    df = pd.read_csv(COHORTE, sep=";", decimal=",", encoding="utf-8-sig")
    mod = GMMModule()
    e = _estado(mod, df, VARS, ["trigliceridos", "pcr"])
    e.params("elegir_k").update(bootstrap=False, covarianza="diag", k_max=6)
    e.resultados["elegir_k"] = barrer(e, lambda f: None, lambda: False, "gmm")
    from statlab.modules.kmeans.module import k_elegido

    assert k_elegido(e) == e.resultados["elegir_k"]["mejor"]["criterio"] == 4


@pytest.mark.parametrize("Mod, figura", [(GMMModule, "01_bic"), (JerarquicoModule, "01_dendrograma")])
def test_informe_por_algoritmo(tmp_path, Mod, figura):
    import zipfile

    from statlab.core.report import exports as ex

    df = pd.read_csv(COHORTE, sep=";", decimal=",", encoding="utf-8-sig")
    mod = Mod()
    e = _estado(mod, df, VARS, ["trigliceridos", "pcr"])
    e.params("elegir_k").update(bootstrap=False)
    e.resultados["elegir_k"] = barrer(e, lambda f: None, lambda: False, mod.id)
    e.params("modelo_final").update(k=4, B=10)
    e.resultados["modelo_final"] = ajustar(e, lambda f: None, lambda: False, mod.id)
    exp = mod.exportar(e)
    assert figura in exp.figuras and ("08_pertenencia" in exp.figuras) == (mod.id == "gmm")
    docx = ex.escribir("docx", exp, tmp_path / "informe")[0]
    xml = zipfile.ZipFile(docx).read("word/document.xml").decode("utf-8")
    assert exp.titulo in xml and ("BIC" in xml if mod.id == "gmm" else "Altura de fusión" in xml)
    assert exp.json["modulo"] == mod.id
