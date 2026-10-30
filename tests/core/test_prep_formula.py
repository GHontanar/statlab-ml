import numpy as np
import pandas as pd
import pytest

from statlab.core.errors import ErrorUsuario
from statlab.core.prep import formula as F


@pytest.fixture
def df():
    return pd.DataFrame({
        "peso": [70.0, 80.0, np.nan],
        "talla": [175.0, 160.0, 170.0],
        "sexo": pd.Series(["F", "M", "F"], dtype="string"),
        "cr": [0.8, 1.2, 1.0],
        "edad": [50.0, 70.0, 30.0],
        "fecha nac": pd.to_datetime(["1970-01-01", "1950-06-15", None]),
        "fecha inc": pd.to_datetime(["2020-01-01", "2020-06-15", "2020-01-01"]),
    })


def test_aritmetica_coma_decimal_y_precedencia(df):
    imc = F.calcular("peso / (talla/100)^2", df)
    assert imc.round(1).tolist()[:2] == [22.9, 31.2]
    assert np.isnan(imc.iloc[2])  # un perdido en la entrada da perdido
    assert F.calcular("2 + 3 * 2 ^ 2", df).iloc[0] == 14
    assert F.calcular("-2^2", df).iloc[0] == -4
    assert F.calcular("2^3^2", df).iloc[0] == 2**9
    assert F.calcular("0,5 * 2", df).iloc[0] == F.calcular("0.5 * 2", df).iloc[0] == 1


def test_ckd_epi_2021_se_puede_escribir(df):
    texto = (
        '142 * MIN(cr / SI(sexo = "F"; 0,7; 0,9); 1) ^ SI(sexo = "F"; -0,241; -0,302)'
        ' * MAX(cr / SI(sexo = "F"; 0,7; 0,9); 1) ^ -1,2 * 0,9938 ^ edad * SI(sexo = "F"; 1,012; 1)'
    )
    fg = F.calcular(texto, df)

    def ref(cr, edad, mujer):
        k, a = (0.7, -0.241) if mujer else (0.9, -0.302)
        return 142 * min(cr / k, 1) ** a * max(cr / k, 1) ** -1.2 * 0.9938**edad * (1.012 if mujer else 1)

    assert fg.tolist() == pytest.approx([ref(0.8, 50, True), ref(1.2, 70, False), ref(1.0, 30, True)])


def test_columnas_con_espacios_y_fechas(df):
    edad = F.calcular("AÑOS([fecha nac]; [fecha inc])", df)
    assert edad.round(1).tolist()[:2] == [50.0, 70.0]
    assert np.isnan(edad.iloc[2])
    assert F.calcular("anos([fecha nac]; [fecha inc])", df).round(1).iloc[0] == 50.0  # sin tilde ni mayúsculas
    assert F.columnas(F.analizar("AÑOS([fecha nac]; [fecha inc]) + peso + peso")) == ["fecha nac", "fecha inc", "peso"]


def test_logica_y_na(df):
    r = F.calcular('SI(Y(edad >= 50; sexo = "F"); 1; 0)', df)
    assert r.tolist() == [1, 0, 0]
    assert F.calcular("ESNA(peso)", df).tolist() == [False, False, True]
    assert F.calcular("SI(peso > 75; 1)", df).isna().tolist() == [True, False, True]
    assert F.calcular('sexo & "-x"', df).tolist() == ["F-x", "M-x", "F-x"]


@pytest.mark.parametrize("texto, trozo", [
    ("peso +", "incompleta"),
    ("peso @ 2", "carácter"),
    ("FOO(peso)", "función"),
    ("SI(peso)", "argumentos"),
    ("(peso", "Falta"),
    ("pesos * 2", "columna «pesos»"),
    ('sexo > "F"', "="),
    ("sexo * 2", "texto"),
    ("[fecha nac] - [fecha inc]", "AÑOS"),
    ("", "Escribe"),
])
def test_errores_en_espanol(df, texto, trozo):
    with pytest.raises(ErrorUsuario, match=trozo):
        F.calcular(texto, df)


def test_renombrar_para_mis_formulas(df):
    t = F.renombrar("peso / (talla/100)^2", {"peso": "peso kg", "talla": "altura"})
    otro = df.rename(columns={"peso": "peso kg", "talla": "altura"})
    assert F.calcular(t, otro).round(1).tolist()[:2] == [22.9, 31.2]
    # la fórmula reescrita se vuelve a leer igual
    assert F.renombrar(t, {}) == t


def test_nunca_ejecuta_codigo(df):
    for malicioso in ("__import__('os')", "peso.__class__", "exec(1)"):
        with pytest.raises(ErrorUsuario):
            F.calcular(malicioso, df)
