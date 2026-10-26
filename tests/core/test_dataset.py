import numpy as np
import pandas as pd
import pytest

from statlab.core import fmt
from statlab.core import io as sio
from statlab.core.dataset import Dataset, Rol, column_summary


@pytest.fixture
def ds():
    return Dataset(sio.read_example(), fuente="datos_ejemplo.csv")


def test_roles_only_numeric_in_model(ds):
    cambio = ds.asignar_rol(["hb", "sexo"], Rol.MODELO)
    assert cambio.aplicadas == ["hb"]
    assert "sexo" in cambio.rechazadas and "numérica" in cambio.mensaje
    assert ds.con_rol(Rol.MODELO) == ["hb"]
    assert ds.asignar_rol(["sexo"], Rol.DESCRIPTIVA).aplicadas == ["sexo"]


def test_single_identifier(ds):
    assert ds.asignar_rol(["id", "sexo"], Rol.IDENTIFICADOR).rechazadas
    ds.asignar_rol(["id"], Rol.IDENTIFICADOR)
    ds.asignar_rol(["tph"], Rol.IDENTIFICADOR)
    assert ds.identificador == "tph" and "id" not in ds.roles


def test_log_toggle(ds):
    ds.alternar_log(["ferritina"])
    assert ds.roles["ferritina"] == Rol.MODELO and ds.log == {"ferritina"}
    ds.alternar_log(["ferritina"])
    assert ds.log == set() and ds.roles["ferritina"] == Rol.MODELO
    ds.alternar_log(["ferritina"])
    ds.asignar_rol(["ferritina"], Rol.DESCRIPTIVA)
    assert ds.log == set()
    assert "sexo" in ds.alternar_log(["sexo"]).rechazadas
    ds.df.loc[0, "hb"] = -1
    assert "negativos" in ds.alternar_log(["hb"]).mensaje


def test_rows(ds):
    assert len(ds.filas_activas()) == 240 and not ds.filtro_filas_activo
    ds.analizar_solo([0, 1, 2, 3])
    ds.excluir([3])
    assert ds.filas_activas().tolist() == [0, 1, 2]
    assert ds.resumen_filas() == "3 de 240"
    assert not ds.fila_activa(3) and not ds.fila_activa(10)
    ds.analizar_solo([3, 4])  # volver a incluir quita la exclusión
    assert ds.filas_activas().tolist() == [3, 4]
    ds.guardar_subgrupo(" tph ", [5, 5, 1])
    assert ds.subgrupos == {"tph": [1, 5]}
    with pytest.raises(ValueError):
        ds.guardar_subgrupo("  ", [1])
    ds.usar_todas()
    assert ds.resumen_filas() == "todas (240)"


def test_column_summary(ds):
    rows = dict(column_summary(ds.df["hb"]))
    assert rows["Tipo"] == "Numérica"
    assert rows["Valores perdidos (NA)"].startswith(str(int(ds.df["hb"].isna().sum())))
    assert "," in rows["Media (DE)"]
    rows = dict(column_summary(ds.df["sexo"]))
    assert rows["Tipo"] == "Texto / categórica" and rows["Valores distintos"] == "2"


def test_format():
    assert fmt.num(12.5, 2) == "12,50"
    assert fmt.num(-0.25, 1) == "−0,2" or fmt.num(-0.25, 1) == "−0,3"
    assert fmt.num(float("nan")) == "NA"
    assert fmt.column_decimals(pd.Series([1.0, 2.5, np.nan])) == 1
    assert fmt.column_decimals(pd.Series([3.28, 4.1])) == 2
    assert fmt.column_decimals(pd.Series([71.0, 64.0])) == 0
    assert fmt.column_decimals(pd.Series([1 / 3])) == fmt.MAX_DECIMALS
