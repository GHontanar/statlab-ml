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
        assert set(z.namelist()) == {"meta.json", "data.csv", "analisis.json", "resultados/a1.json"}
        assert all(not n.endswith(".pkl") for n in z.namelist())
        results = json.loads(z.read("resultados/a1.json"))
        assert "_preparado" not in results["preprocesado"]
        assert json.loads(z.read("meta.json"))["formato"] == 3
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


def test_roundtrip_con_preparacion(tmp_path):
    from statlab.core.prep.preparacion import de_ejemplo
    from statlab.core.prep.receta import Paso

    mod = KMeansModule()
    e = mod.crear_estado()
    prep = de_ejemplo()
    prep.receta.añadir(Paso("excluir", {"condicion": "edad < 2", "motivo": "Menores de 2 años"}))
    prep.receta.añadir(Paso("tipo", {"columna": "sexo", "tipo": "categorica"}))
    prep.receta.añadir(Paso("calcular", {"destino": "hb_vcm", "formula": "hb / vcm"}))
    prep.diccionario.entrada("hb").etiqueta = "Hemoglobina"
    e.preparacion = prep
    e.dataset, out = prep.dataset()
    e.dataset.asignar_rol(["hb", "hb_vcm"], Rol.MODELO)
    e.flujo.completar("datos")
    path = ses.guardar(tmp_path / "prep", e, mod.id)
    with zipfile.ZipFile(path) as z:
        assert {"original.bin", "prep.json"} <= set(z.namelist())
        assert z.read("original.bin") == sio.example_bytes()
    otra = ses.abrir(path, mod.crear_estado, mod.id)
    assert otra.preparacion.receta == prep.receta
    assert otra.preparacion.diccionario.etiqueta("hb") == "Hemoglobina"
    assert otra.dataset.excluidas_receta == out.excluidas and out.excluidas
    assert isinstance(otra.dataset.df["sexo"].dtype, pd.CategoricalDtype)  # se reaplica la receta
    pd.testing.assert_series_equal(otra.dataset.df["hb_vcm"], e.dataset.df["hb_vcm"])
    assert otra.dataset.roles == e.dataset.roles


def _formato_antiguo(path_nuevo, destino, formato: int):
    """Reescribe una sesión de formato 3 con un análisis como se guardaba en el formato 1 o 2."""
    with zipfile.ZipFile(path_nuevo) as z, zipfile.ZipFile(destino, "w") as w:
        meta = json.loads(z.read("meta.json"))
        lista = json.loads(z.read("analisis.json"))["analisis"]
        meta.update(formato=formato, modulo=lista[0]["modulo"])
        meta.pop("activo")
        estado = lista[0]["estado"]
        if formato == 1:
            estado.pop("excluidas_receta")
        w.writestr("meta.json", json.dumps(meta))
        w.writestr("data.csv", z.read("data.csv"))
        w.writestr("state.json", json.dumps(estado))
        w.writestr("results.json", z.read("resultados/a1.json"))
        if formato == 2 and "prep.json" in z.namelist():
            w.writestr("prep.json", z.read("prep.json"))
            w.writestr("original.bin", z.read("original.bin"))


def test_sesion_formato_1_se_migra(tmp_path, full_state):
    mod, e = full_state
    path = ses.guardar(tmp_path / "v3", e, mod.id)
    v1 = tmp_path / "v1_viejo.statlab"
    _formato_antiguo(path, v1, 1)
    otra = ses.abrir(v1, mod.crear_estado, mod.id)
    assert otra.preparacion is not None and otra.preparacion.receta.pasos == []
    pd.testing.assert_frame_equal(otra.preparacion.leidos, otra.dataset.df)
    assert otra.dataset.excluidas_receta == {}
    assert otra.resultados["modelo_final"]["tamanos"] == e.resultados["modelo_final"]["tamanos"]


def test_varios_analisis(tmp_path, full_state):
    from statlab.modules.kmeans.module import GMMModule

    mod, e = full_state
    gmm = GMMModule()
    eg = gmm.crear_estado()
    eg.dataset = Dataset(e.dataset.df.copy(), fuente=e.dataset.fuente)
    eg.dataset.asignar_rol(["hb", "vcm"], Rol.MODELO)
    eg.params("elegir_k").update(covarianza="diag")
    proyecto = ses.Proyecto([ses.AnalisisGuardado("a1", "kmeans", "k-means", e),
                             ses.AnalisisGuardado("a2", "gmm", "Mi GMM", eg)], activo="a2")
    path = ses.guardar_proyecto(tmp_path / "varios", proyecto)
    abierto = ses.abrir_proyecto(path, {"kmeans": mod.crear_estado, "gmm": gmm.crear_estado})
    assert [(a.id, a.modulo, a.nombre) for a in abierto.analisis] == [("a1", "kmeans", "k-means"),
                                                                     ("a2", "gmm", "Mi GMM")]
    assert abierto.activo == "a2"
    a1, a2 = (a.estado for a in abierto.analisis)
    assert a1.resultados["modelo_final"]["tamanos"] == e.resultados["modelo_final"]["tamanos"]
    assert a2.dataset.con_rol(Rol.MODELO) == ["hb", "vcm"] and a2.params("elegir_k")["covarianza"] == "diag"
    assert a1.preparacion is a2.preparacion  # la preparación es una sola, compartida
    # una versión que no conoce GMM no puede abrirla entera
    with pytest.raises(ErrorUsuario):
        ses.abrir_proyecto(path, {"kmeans": mod.crear_estado})
    assert ses.abrir(path, mod.crear_estado, "kmeans").resultados["modelo_final"]


def test_sesion_formato_2_se_migra(tmp_path):
    from statlab.core.prep.preparacion import de_ejemplo
    from statlab.core.prep.receta import Paso

    mod = KMeansModule()
    e = mod.crear_estado()
    e.preparacion = de_ejemplo()
    e.preparacion.receta.añadir(Paso("calcular", {"destino": "x", "formula": "hb * 2"}))
    e.dataset, _ = e.preparacion.dataset()
    e.flujo.completar("datos")
    path = ses.guardar(tmp_path / "v3", e, mod.id)
    v2 = tmp_path / "v2.statlab"
    _formato_antiguo(path, v2, 2)
    otra = ses.abrir(v2, mod.crear_estado, mod.id)
    assert otra.preparacion.receta == e.preparacion.receta and "x" in otra.dataset.columnas
