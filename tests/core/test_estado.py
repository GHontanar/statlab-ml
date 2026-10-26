from statlab.core import io as sio
from statlab.core.dataset import Dataset, Rol, validar_variables
from statlab.core.estado import serializable
from statlab.modules.kmeans.module import KMeansModule, preprocesar, resumen_preprocesado

MODEL = ["hb", "vcm", "plaquetas", "neutrofilos", "hbf", "ferritina"]


def _estado():
    mod = KMeansModule()
    estado = mod.crear_estado()
    estado.dataset = Dataset(sio.read_example(), fuente="x.csv")
    return mod, estado


def test_snapshot_is_independent():
    _, estado = _estado()
    estado.dataset.asignar_rol(MODEL, Rol.MODELO)
    copia = estado.snapshot()
    estado.dataset.asignar_rol(["hb"], None)
    estado.params("preprocesado")["vecinos"] = 9
    assert "hb" in copia.dataset.con_rol(Rol.MODELO)
    assert copia.params("preprocesado")["vecinos"] == 5
    assert copia.dataset.df is estado.dataset.df  # los datos no se copian


def test_validation_messages():
    _, estado = _estado()
    ds = estado.dataset
    assert any("al menos 2" in m for m in validar_variables(ds))
    ds.asignar_rol(["hb", "vcm"], Rol.MODELO)
    assert validar_variables(ds) == []
    ds.analizar_solo([0, 1, 2])
    assert any("Solo hay 3 filas" in m for m in validar_variables(ds))
    na_hb = ds.df.index[ds.df["hb"].isna()].tolist()
    assert len(na_hb) >= 10
    ds.analizar_solo(na_hb)  # filas en las que hb está vacía
    assert any("«hb»" in m for m in validar_variables(ds))


def test_preprocess_result_and_summary():
    _, estado = _estado()
    estado.dataset.asignar_rol(MODEL, Rol.MODELO)
    estado.dataset.alternar_log(["ferritina"])
    r = preprocesar(estado)
    assert r["n_analizadas"] == 240 and r["celdas_imputadas"] == 80 and r["log"] == ["ferritina"]
    assert "_preparado" in r and "_preparado" not in serializable(r)
    estado.resultados["preprocesado"] = r
    assert resumen_preprocesado(estado).splitlines() == [
        "Perdidos: KNN, 5 vecinos (80 celdas imputadas)",
        "Escalado: z-score",
        "log(1+x): ferritina",
    ]
    estado.params("preprocesado")["imputacion"] = "complete"
    r = preprocesar(estado)
    assert r["n_excluidas"] > 0 and r["celdas_imputadas"] == 0
