import io

import numpy as np
import pandas as pd
import pytest

from statlab.core import io as sio
from statlab.core.prep import calidad as q
from statlab.core.prep import receta as rc
from statlab.core.prep.diccionario import Diccionario, Entrada
from statlab.core.prep.preparacion import Preparacion


def excel_sucio() -> bytes:
    """Excel «sucio» de referencia (criterio de aceptación de F2): datos en la hoja 2,
    cabecera en la fila 3, cabecera de dos filas, unidades mezcladas, categorías
    incoherentes, fechas dd/mm, códigos 999 y una fila de totales al final."""
    rng = np.random.default_rng(1)
    n = 60
    hb = rng.normal(13, 1.2, n).round(1)
    hb[:8] = (hb[:8] * 10).round(0)  # 8 pacientes en g/L
    sexo = rng.choice(["Hombre", "Mujer"], n).astype(object)
    sexo[[3, 9]] = "hombre "
    sexo[[5]] = "MUJER"
    gluc = rng.normal(100, 12, n).round(0)
    gluc[[10, 20, 30]] = 999
    fechas = [f"{d:02d}/{m:02d}/2020" for d, m in zip(rng.integers(1, 29, n), rng.integers(1, 13, n), strict=True)]
    fechas[0] = "25/01/2020"  # al menos un día > 12
    filas = [["Registro de ejemplo (datos ficticios)", None, None, None, None, None],
             [None, None, None, None, None, None],
             ["Paciente", "Demografía", None, "Analítica", None, "Inclusión"],
             ["id", "sexo", "edad", "hb", "glucosa", "fecha"]]
    for i in range(n):
        filas.append([f"P{i:03d}", sexo[i], int(rng.integers(20, 90)), hb[i], gluc[i], fechas[i]])
    filas.append(["Total", n, None, None, None, None])
    buf = io.BytesIO()
    with pd.ExcelWriter(buf) as w:
        nota = pd.DataFrame({"nota": ["Las instrucciones están en la hoja Datos"]})
        nota.to_excel(w, sheet_name="Léeme", index=False)
        pd.DataFrame(filas).to_excel(w, sheet_name="Datos", index=False, header=False)
    return buf.getvalue()


def test_excel_sucio_se_lee_y_se_detecta():
    raw = excel_sucio()
    lect = sio.leer("registro.xlsx", raw, sio.OpcionesLectura(hoja="Datos"))
    assert lect.hojas == ["Léeme", "Datos"]
    assert lect.opciones.fila_cabecera == 3 and lect.opciones.filas_cabecera == 2
    assert list(lect.df.columns) == ["Paciente id", "Demografía sexo", "Demografía edad", "Analítica hb",
                                     "Analítica glucosa", "Inclusión fecha"]
    assert len(lect.df) == 60  # sin la fila de totales
    assert any("final" in a for a in lect.avisos)
    problemas = {p.codigo: p for p in q.revisar(lect.df)}
    assert [p.codigo for p in q.revisar(lect.df)].count("unidades") == 1  # 999 en glucosa no es un cambio de unidad
    assert problemas["unidades"].columna == "Analítica hb"
    assert problemas["unidades"].n == 8 and problemas["unidades"].propuesta.params["factor"] == pytest.approx(0.1)
    assert problemas["categorias"].propuesta.params["mapa"] == {"hombre ": "Hombre", "MUJER": "Mujer"}
    assert problemas["codigo_perdido"].n == 3
    fecha = problemas["fecha_texto"].propuesta
    assert fecha.params == {"columna": "Inclusión fecha", "tipo": "fecha", "formato": "dma"}


def test_aceptar_todas_las_propuestas_deja_los_datos_limpios():
    prep = Preparacion.desde_archivo("registro.xlsx", excel_sucio(), sio.OpcionesLectura(hoja="Datos"))
    for p in q.revisar(prep.leidos):
        if p.propuesta is not None:
            prep.receta.añadir(p.propuesta)
    ds, out = prep.dataset()
    assert not out.errores
    df = ds.df
    assert df["Analítica hb"].between(8, 18).all()
    assert set(df["Demografía sexo"].astype(str)) == {"Hombre", "Mujer"}
    assert df["Analítica glucosa"].isna().sum() == 3
    assert pd.api.types.is_datetime64_any_dtype(df["Inclusión fecha"])
    # una segunda revisión ya no encuentra nada que proponer
    assert [p.codigo for p in q.revisar(df) if p.propuesta is not None] == []


def test_mes_dia_y_ambiguo():
    assert q.formato_fecha(pd.Series(["01/25/2020", "02/03/2020"])) == ("mda", False)
    assert q.formato_fecha(pd.Series(["01/02/2020", "03/04/2020"])) == ("dma", True)
    assert q.formato_fecha(pd.Series(["2020-01-25"])) == ("amd", False)


def test_duplicados_e_id_repetido():
    df = pd.DataFrame({"id": ["a", "b", "b", "c", "c"], "x": [1, 2, 3, 4, 4]})
    cods = {p.codigo: p for p in q.revisar(df, id_col="id")}
    assert cods["duplicados"].filas == [4]
    assert cods["id_duplicado"].filas == [1, 2]  # mismo ID con datos distintos: solo se avisa
    assert cods["id_duplicado"].propuesta is None


def test_limites_y_perdidos_del_diccionario():
    df = pd.DataFrame({"hb": [12.0, 45.0, 13.0, -9.0, 14.0]})
    dic = Diccionario({"hb": Entrada(minimo=3, maximo=25, perdidos=["-9"])})
    cods = {p.codigo: p for p in q.revisar(df, dic)}
    assert cods["codigo_perdido"].filas == [3]
    assert cods["fuera_limites"].filas == [1, 3]
    out = rc.aplicar(df, rc.Receta([cods["codigo_perdido"].propuesta, cods["fuera_limites"].propuesta]))
    assert out.df["hb"].isna().tolist() == [False, True, False, True, False]


def test_sin_falsos_positivos_en_los_datos_de_ejemplo():
    graves = [p for p in q.revisar(sio.read_example()) if p.nivel == q.GRAVE]
    assert graves == []


def test_lognormal_no_es_mezcla_de_unidades():
    rng = np.random.default_rng(0)
    ferritina = pd.Series(np.exp(rng.normal(4, 1.0, 300)))
    assert q.unidades_mezcladas(ferritina) is None


def test_sin_hoja_elegida_usa_la_primera_con_datos():
    lect = sio.leer("registro.xlsx", excel_sucio())
    assert lect.opciones.hoja == "Datos" and len(lect.df) == 60
    assert "Datos" in lect.avisos[0]
