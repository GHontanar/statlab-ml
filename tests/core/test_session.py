import json
import zipfile

import numpy as np
import pandas as pd
import pytest

from statlab.core import io as sio
from statlab.core import session as ses
from statlab.core.dataset import Dataset, Rol
from statlab.core.errors import ErrorUsuario
from statlab.core.flow import EstadoPaso as E
from statlab.modules.kmeans.module import KMeansModule, ajustar, barrer, preprocesar

MODEL = ["hb", "vcm", "plaquetas", "neutrofilos", "hbf", "ferritina"]


@pytest.fixture(scope="module")
def full_state():
    mod = KMeansModule()
    e = mod.crear_estado()
    e.dataset = Dataset(sio.read_example(), fuente="datos_ejemplo.csv")
    e.dataset.asignar_rol(MODEL, Rol.MODELO)
    e.dataset.alternar_log(["ferritina"])
    e.dataset.asignar_rol(["edad", "sexo"], Rol.DESCRIPTIVA)
    e.dataset.asignar_rol(["id"], Rol.IDENTIFICADOR)
    e.dataset.excluir([3])
    e.dataset.guardar_subgrupo("primeros", [0, 1, 2])
    for paso in ["datos", "variables"]:
        e.flujo.completar(paso)
    e.resultados["preprocesado"] = preprocesar(e)
    e.flujo.completar("preprocesado")
    e.params("elegir_k").update(bootstrap=False)
    e.resultados["elegir_k"] = barrer(e, lambda f: None, lambda: False)
    e.flujo.completar("elegir_k")
    e.params("modelo_final").update(k=3, B=20)
    e.resultados["modelo_final"] = ajustar(e, lambda f: None, lambda: False)
    e.flujo.completar("modelo_final")
    return mod, e


def test_roundtrip(tmp_path, full_state):
    mod, e = full_state
    path = ses.guardar(tmp_path / "analisis", e, mod.id)
    assert path.suffix == ".statlab"
    with zipfile.ZipFile(path) as z:
        assert set(z.namelist()) == {"meta.json", "data.csv", "state.json", "results.json"}
        assert all(not n.endswith(".pkl") for n in z.namelist())
        results = json.loads(z.read("results.json"))
        assert "_preparado" not in results["preprocesado"]
    r = ses.abrir(path, mod.crear_estado, mod.id)
    pd.testing.assert_frame_equal(r.dataset.df, e.dataset.df, check_dtype=False)
    assert [str(t) for t in r.dataset.df.dtypes] == [str(t) for t in e.dataset.df.dtypes]
    assert r.dataset.roles == e.dataset.roles and r.dataset.log == {"ferritina"}
    assert r.dataset.excluidas == {3} and r.dataset.subgrupos == {"primeros": [0, 1, 2]}
    assert r.params("modelo_final")["k"] == 3 and r.params("elegir_k")["bootstrap"] is False
    assert r.flujo.to_dict() == e.flujo.to_dict() and r.flujo["exportar"] == E.ACTIVO
    assert r.resultados["modelo_final"]["tamanos"] == e.resultados["modelo_final"]["tamanos"]
    assert r.resultados["elegir_k"] == e.resultados["elegir_k"]
    # Se puede seguir calculando: la matriz preparada se reconstruye bajo demanda.
    again = barrer(r, lambda f: None, lambda: False)
    assert np.allclose(again["silueta"], e.resultados["elegir_k"]["silueta"])


def test_na_and_text_preserved(tmp_path):
    mod = KMeansModule()
    e = mod.crear_estado()
    df = pd.DataFrame({"a": [1.5, np.nan, 2.25], "b": ["x", None, "NA"], "n": [1, 2, 3]})
    e.dataset = Dataset(df, fuente="t.csv")
    r = ses.abrir(ses.guardar(tmp_path / "t.statlab", e, mod.id), mod.crear_estado, mod.id)
    assert r.dataset.df["a"].isna().tolist() == [False, True, False]
    assert r.dataset.df["b"].iloc[0] == "x" and pd.isna(r.dataset.df["b"].iloc[1])
    assert r.dataset.df["b"].iloc[2] == "NA"
    assert str(r.dataset.df["b"].dtype) == str(e.dataset.df["b"].dtype)
    assert r.dataset.df["n"].dtype.kind == "i"


def test_invalid_files(tmp_path):
    mod = KMeansModule()
    bad = tmp_path / "x.statlab"
    bad.write_bytes(b"no es un zip")
    with pytest.raises(ErrorUsuario, match="no es una sesión"):
        ses.abrir(bad, mod.crear_estado, mod.id)
    with zipfile.ZipFile(bad, "w") as z:
        z.writestr("meta.json", json.dumps({"formato": 99, "version_app": "9.0", "modulo": "kmeans"}))
        for name in ("data.csv", "state.json", "results.json"):
            z.writestr(name, "{}")
    with pytest.raises(ErrorUsuario, match="más reciente"):
        ses.abrir(bad, mod.crear_estado, mod.id)
    with pytest.raises(ErrorUsuario):
        ses.guardar(tmp_path / "vacia", mod.crear_estado(), mod.id)
