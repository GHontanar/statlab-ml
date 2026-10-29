import pytest

from statlab.core.errors import ErrorUsuario
from statlab.core.prep.diccionario import Diccionario, Entrada
from statlab.core.prep.mis_formulas import Biblioteca, FormulaGuardada
from statlab.core.prep.preparacion import de_ejemplo
from statlab.core.prep.receta import aplicar


def test_etiquetas():
    d = Diccionario({"hb": Entrada(etiqueta="Hemoglobina", unidad="g/dL"), "x": Entrada(unidad="mg")})
    assert d.etiqueta("hb") == "Hemoglobina (g/dL)"
    assert d.etiqueta("x") == "x (mg)" and d.etiqueta("otra") == "otra"


@pytest.mark.parametrize("ext", [".csv", ".xlsx"])
def test_exportar_e_importar(tmp_path, ext):
    d = Diccionario({
        "hb": Entrada(etiqueta="Hemoglobina", unidad="g/dL", minimo=3.0, maximo=25.5, perdidos=["999", "-9"]),
        "sexo": Entrada(etiqueta="Sexo", categorias={"1": "Hombre", "2": "Mujer"}),
    })
    path = d.exportar(tmp_path / f"dic{ext}", ["id", "hb", "sexo"])
    otro = Diccionario.importar(path)
    assert otro.entradas == d.entradas  # «id» sin nada definido no se importa


def test_importar_sin_columna_variable(tmp_path):
    p = tmp_path / "mal.csv"
    p.write_text("nombre;etiqueta\nhb;Hemoglobina\n", encoding="utf-8")
    with pytest.raises(ErrorUsuario, match="variable"):
        Diccionario.importar(p)


def test_dict_ida_y_vuelta():
    d = Diccionario({"hb": Entrada(etiqueta="Hb", minimo=1.0)})
    assert Diccionario.from_dict(d.to_dict()) == d


def test_mis_formulas_en_otro_archivo(tmp_path):
    bib = Biblioteca()
    bib.guardar_formula(FormulaGuardada("imc", "peso / (talla/100)^2", "Índice de masa corporal"))
    path = bib.escribir(tmp_path / "mis_formulas.json")
    bib2 = Biblioteca.leer(path)
    f = bib2.get("imc")
    assert f.entradas == ["peso", "talla"]
    with pytest.raises(ErrorUsuario, match="talla"):
        f.paso({"peso": "peso_kg"})
    import pandas as pd

    df = pd.DataFrame({"peso_kg": [70.0], "altura cm": [175.0]})
    paso = f.paso({"peso": "peso_kg", "talla": "altura cm"})
    from statlab.core.prep.receta import Receta

    assert aplicar(df, Receta([paso])).df["imc"].round(1).tolist() == [22.9]


def test_mis_formulas_importar_y_errores(tmp_path):
    a, b = Biblioteca(), Biblioteca()
    a.guardar_formula(FormulaGuardada("x", "edad * 2"))
    b.guardar_formula(FormulaGuardada("x", "edad * 3"))
    b.guardar_formula(FormulaGuardada("y", "edad + 1"))
    assert a.importar(b) == (1, 1) and a.get("x").formula == "edad * 3"
    with pytest.raises(ErrorUsuario):
        a.guardar_formula(FormulaGuardada("z", "edad +"))
    (tmp_path / "otro.json").write_text('{"tipo": "otra cosa"}', encoding="utf-8")
    with pytest.raises(ErrorUsuario):
        Biblioteca.leer(tmp_path / "otro.json")
    assert Biblioteca.leer(tmp_path / "no_existe.json").formulas == []


def test_preparacion_conserva_roles_al_cambiar_la_receta():
    from statlab.core.dataset import Rol
    from statlab.core.prep.receta import Paso

    prep = de_ejemplo()
    ds, _ = prep.dataset()
    ds.asignar_rol(["hb", "vcm"], Rol.MODELO)
    ds.alternar_log(["ferritina"])
    ds.excluir([5])
    prep.receta.añadir(Paso("excluir", {"condicion": "edad < 1", "motivo": "Menores de 1 año"}))
    prep.receta.añadir(Paso("calcular", {"destino": "hb_vcm", "formula": "hb / vcm"}))
    ds2, out = prep.dataset(ds)
    assert ds2.roles == ds.roles and ds2.log == {"ferritina"}
    assert ds2.excluidas == {5} and set(ds2.excluidas_receta) == set(out.excluidas)
    assert len(ds2.filas_activas()) == 240 - len(out.excluidas | {5: ""})
    assert "hb_vcm" in ds2.columnas
