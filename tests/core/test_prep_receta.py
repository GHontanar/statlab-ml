import numpy as np
import pandas as pd
import pytest

from statlab.core.errors import ErrorUsuario
from statlab.core.prep import receta as rc
from statlab.core.prep.receta import Paso, Receta


@pytest.fixture
def datos():
    return pd.DataFrame({
        "id": ["A1", "A2", "A3", "A4", "A2"],
        "hb": ["12,5", "<5", "13,1 g/dL", "x", "<5"],
        "sexo": ["Hombre", "hombre ", "Mujer", "MUJER", "hombre "],
        "glucosa": [90.0, 999.0, 110.0, 95.0, 999.0],
        "f_inc": ["01/02/2020", "15/03/2020", "20/12/2019", "05/05/2021", "15/03/2020"],
        "f_evento": ["01/02/2021", None, None, "05/11/2021", None],
        "f_ultimo": ["01/02/2022", "15/03/2022", "20/06/2020", "05/05/2022", "15/03/2022"],
        "edad": [17.0, 45.0, 60.0, 80.0, 45.0],
    })


def test_los_datos_leidos_no_se_modifican(datos):
    copia = datos.copy()
    r = Receta()
    r.añadir(Paso("tipo", {"columna": "hb", "tipo": "numerica"}))
    r.añadir(Paso("excluir", {"condicion": "edad < 18", "motivo": "Menores de edad"}))
    rc.aplicar(datos, r)
    pd.testing.assert_frame_equal(datos, copia)


def test_texto_a_numero_con_limites(datos):
    r = Receta([Paso("tipo", {"columna": "hb", "tipo": "numerica"})])
    out = rc.aplicar(datos, r)
    assert out.df["hb"].tolist()[:3] == [12.5, 5.0, 13.1]
    assert np.isnan(out.df["hb"].iloc[3])
    assert "1 valores" in out.informes[0].mensaje
    r.pasos[0].params["limites"] = "na"
    assert rc.aplicar(datos, r).df["hb"].isna().sum() == 3


def test_pasos_encadenados_y_flujo(datos):
    r = Receta()
    for p in [
        Paso("perdidos", {"columnas": ["glucosa"], "valores": [999]}),
        Paso("recodificar", {"columna": "sexo", "mapa": {"hombre": "Hombre", "MUJER": "Mujer"}}),
        Paso("tipo", {"columna": "sexo", "tipo": "categorica"}),
        Paso("tipo", {"columna": "f_inc", "tipo": "fecha", "formato": "dma"}),
        Paso("tipo", {"columna": "f_evento", "tipo": "fecha", "formato": "dma"}),
        Paso("tipo", {"columna": "f_ultimo", "tipo": "fecha", "formato": "dma"}),
        Paso("seguimiento", {"inicio": "f_inc", "evento": "f_evento", "ultimo_contacto": "f_ultimo",
                             "unidad": "meses", "destino_tiempo": "meses_seg", "destino_evento": "evento"}),
        Paso("duplicados", {"columnas": ["id"]}),
        Paso("excluir", {"condicion": "edad < 18", "motivo": "Menores de edad"}),
        Paso("categorizar", {"columna": "edad", "cortes": [50, 70], "destino": "grupo_edad"}),
        Paso("calcular", {"destino": "hiper", "formula": "glucosa > 100"}),
    ]:
        r.añadir(p)
    out = rc.aplicar(datos, r)
    assert not out.errores, [i.mensaje for i in out.errores]
    df = out.df
    assert df["glucosa"].isna().sum() == 2 and out.informes[0].celdas == 2
    assert df["sexo"].tolist() == ["Hombre", "Hombre", "Mujer", "Mujer", "Hombre"]
    assert df["meses_seg"].round(0).tolist()[:4] == [12, 24, 6, 6]
    assert df["evento"].tolist()[:4] == [1, 0, 0, 1]
    assert list(df["grupo_edad"].astype(str)) == ["< 50", "< 50", "50–70", "≥ 70", "< 50"]
    np.testing.assert_array_equal(df["hiper"].to_numpy(), [0, np.nan, 1, 0, np.nan])  # VERDADERO/FALSO → 1/0
    # las filas no se borran: se marcan con el motivo, en el orden de la receta
    assert len(df) == 5
    assert out.excluidas == {4: "Duplicado", 0: "Menores de edad"}
    assert out.flujo() == [("Duplicado", 1), ("Menores de edad", 1)]


def test_paso_que_falla_no_detiene_la_receta(datos):
    r = Receta([
        Paso("calcular", {"destino": "x", "formula": "noexiste * 2"}),
        Paso("calcular", {"destino": "y", "formula": "edad * 2"}),
    ])
    out = rc.aplicar(datos, r)
    assert not out.informes[0].ok and "noexiste" in out.informes[0].mensaje
    assert "x" not in out.df and out.df["y"].iloc[0] == 34


def test_paso_desactivado_y_orden(datos):
    r = Receta()
    a = r.añadir(Paso("calcular", {"destino": "z", "formula": "edad + 1"}))
    b = r.añadir(Paso("calcular", {"destino": "z", "formula": "z * 10"}))
    assert rc.aplicar(datos, r).df["z"].iloc[0] == 180
    r.mover(b.id, -1)
    assert not rc.aplicar(datos, r).informes[0].ok  # z aún no existe
    r.mover(b.id, +1)
    a.activo = False
    assert not rc.aplicar(datos, r).informes[1].ok


def test_validar_formula_al_anadir():
    with pytest.raises(ErrorUsuario):
        Receta().añadir(Paso("calcular", {"destino": "x", "formula": "edad +"}))
    with pytest.raises(ErrorUsuario):
        Receta().añadir(Paso("nada", {}))


def test_excluir_necesita_motivo(datos):
    out = rc.aplicar(datos, Receta([Paso("excluir", {"condicion": "edad < 18", "motivo": " "})]))
    assert not out.informes[0].ok and not out.excluidas


def test_unidades_con_condicion():
    d = pd.DataFrame({"hb": [12.0, 130.0, 14.0]})
    out = rc.aplicar(d, Receta([Paso("unidades", {"columna": "hb", "factor": 0.1, "condicion": "hb > 40"})]))
    assert out.df["hb"].tolist() == [12.0, 13.0, 14.0] and out.informes[0].celdas == 1


def test_receta_json_ida_y_vuelta(datos):
    r = Receta([Paso("excluir", {"condicion": "edad < 18", "motivo": "Menores"}), Paso("quitar", {"columnas": ["id"]})])
    r.pasos[1].activo = False
    r2 = Receta.from_dict(r.to_dict())
    assert r2 == r
    assert [p.descripcion for p in r2.pasos] == ["Excluir: Menores (edad < 18)", "Quitar id"]


def test_renombrar_y_quitar(datos):
    r = Receta([Paso("renombrar", {"columna": "hb", "nombre": "edad"})])
    assert "Ya hay" in rc.aplicar(datos, r).informes[0].mensaje
    r = Receta([Paso("renombrar", {"columna": "hb", "nombre": "hemoglobina"}), Paso("quitar", {"columnas": ["id"]})])
    df = rc.aplicar(datos, r).df
    assert "hemoglobina" in df and "id" not in df
