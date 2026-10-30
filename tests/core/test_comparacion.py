"""F3: comparación de soluciones (ARI, emparejamiento, importación)."""
from pathlib import Path

import numpy as np
import pytest

from statlab.core import comparacion as cmp
from statlab.core import session as ses
from statlab.core.errors import ErrorUsuario
from statlab.core.prep.preparacion import Preparacion
from statlab.core.report import exports as ex
from statlab.modules.kmeans.module import GMMModule, KMeansModule, ajustar, barrer, preprocesar

COHORTE = Path(__file__).parents[2] / "ejemplos" / "cohorte_cardiometabolica_prueba.csv"
VARS = ["imc", "glucosa", "hba1c", "colesterol_ldl", "trigliceridos", "pcr", "tas", "creatinina"]


def _analisis(Mod, prep):
    from statlab.core.dataset import Rol

    mod = Mod()
    e = mod.crear_estado()
    e.preparacion = prep
    e.dataset, _ = prep.dataset()
    e.dataset.asignar_rol(VARS, Rol.MODELO)
    e.dataset.alternar_log(["trigliceridos", "pcr"])
    e.dataset.asignar_rol(["id"], Rol.IDENTIFICADOR)
    e.flujo.completar("datos")
    e.resultados["preprocesado"] = preprocesar(e)
    e.params("elegir_k").update(bootstrap=False, covarianza="diag")
    e.resultados["elegir_k"] = barrer(e, lambda f: None, lambda: False, mod.id)
    e.params("modelo_final").update(k=4, B=10)
    e.resultados["modelo_final"] = ajustar(e, lambda f: None, lambda: False, mod.id)
    return mod, e


@pytest.fixture(scope="module")
def dos():
    prep = Preparacion.desde_archivo(COHORTE.name, COHORTE.read_bytes())
    return _analisis(KMeansModule, prep), _analisis(GMMModule, prep), prep


def _sol(nombre, e, prep, con_id=True):
    ds = e.dataset
    return cmp.desde_resultado(nombre, e.resultados["modelo_final"], ds.df, ds.identificador if con_id else None,
                               prep.raw, origen="analisis")


def test_kmeans_frente_a_gmm(dos):
    (_, ek), (_, eg), prep = dos
    r = cmp.comparar(_sol("k-means", ek, prep), _sol("GMM", eg, prep), B=200)
    assert r["por"] == "id" and r["comunes"] == 400 and r["solo_a"] == r["solo_b"] == 0
    assert r["ari"] >= 0.90 and r["interpretacion"] == "Acuerdo excelente"  # criterio de aceptación de F3
    lo, hi = r["ari_ic"]
    assert lo <= r["ari"] <= hi
    assert r["mismo_k"] and r["concordancia_pct"] > 95
    assert r["n_discordantes"] == len(r["discordantes"]["fila_a"]) == 400 - round(r["concordancia_pct"] * 4)
    assert sum(f["n"] for f in r["flujos"]) == 400
    assert "prob_b" in r and "prob_a" not in r  # GMM aporta la probabilidad de los discordantes


def test_sin_identificador_empareja_por_fila(dos):
    (_, ek), (_, eg), prep = dos
    r = cmp.comparar(_sol("A", ek, prep, False), _sol("B", eg, prep, False), B=50)
    assert r["por"] == "fila" and r["comunes"] == 400
    otra = cmp.Solucion("X", [0, 1, 0], [0, 1, 2], huella="otra")
    with pytest.raises(ErrorUsuario, match="identificador"):
        cmp.comparar(_sol("A", ek, prep, False), otra)


def test_interseccion_y_k_distinto():
    a = cmp.Solucion("A", [0, 0, 1, 1, 2, 2], list(range(6)), ids=list("abcdef"))
    b = cmp.Solucion("B", [0, 0, 1, 1, 1], list(range(5)), ids=list("abcdg"))
    r = cmp.comparar(a, b, B=20)
    assert (r["comunes"], r["solo_a"], r["solo_b"]) == (4, 2, 1)
    assert not r["mismo_k"] and r["concordancia_pct"] is None
    assert np.array(r["cruzada"]).sum() == 4


def test_importar_csv_y_sesion_dan_el_mismo_ari(dos, tmp_path):
    """Criterio de aceptación de F3: la misma solución importada de otra sesión o exportada a
    CSV da el mismo ARI."""
    (mk, ek), (mg, eg), prep = dos
    sesion = ses.guardar(tmp_path / "otra.statlab", ek, mk.id, "Mi k-means")
    csv = ex.escribir("csv", mk.exportar(ek), tmp_path / "kmeans")[0]
    desde_ses = cmp.desde_sesion(sesion)
    assert [s.nombre for s in desde_ses.soluciones] == ["Mi k-means (otra)"]
    desde_csv = cmp.desde_csv(csv)
    assert desde_csv.k == 4 and len(desde_csv.ids) == 400
    gmm = _sol("GMM", eg, prep)
    a1 = cmp.comparar(desde_ses.soluciones[0], gmm, B=20)["ari"]
    a2 = cmp.comparar(desde_csv, gmm, B=20)["ari"]
    assert a1 == pytest.approx(a2)
    # ida y vuelta de la copia congelada
    s = desde_ses.soluciones[0]
    assert cmp.Solucion.from_dict(s.to_dict()) == s


def test_csv_con_ids_repetidos(tmp_path):
    p = tmp_path / "rep.csv"
    p.write_text("id;cluster\na;1\na;2\nb;1\n", encoding="utf-8")
    with pytest.raises(ErrorUsuario, match="repetidos"):
        cmp.desde_csv(p)


def test_steinley():
    assert [cmp.steinley(v) for v in (0.95, 0.85, 0.7, 0.3, -0.1)] == [
        "Acuerdo excelente", "Acuerdo bueno", "Acuerdo moderado", "Acuerdo escaso", "No mejor que el azar"]
