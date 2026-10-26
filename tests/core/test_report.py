import json
import zipfile

import pandas as pd
import pytest

from statlab.core import io as sio
from statlab.core.dataset import Dataset, Rol
from statlab.core.errors import ErrorUsuario
from statlab.core.report import exports as ex
from statlab.modules.kmeans.module import KMeansModule, ajustar, barrer, preprocesar

MODEL = ["hb", "vcm", "plaquetas", "neutrofilos", "hbf", "ferritina"]


@pytest.fixture(scope="module")
def exportacion():
    mod = KMeansModule()
    e = mod.crear_estado()
    e.dataset = Dataset(sio.read_example(), fuente="datos_ejemplo.csv")
    e.dataset.asignar_rol(MODEL, Rol.MODELO)
    e.dataset.alternar_log(["ferritina"])
    e.dataset.asignar_rol(["edad", "sexo", "tph"], Rol.DESCRIPTIVA)
    e.dataset.excluir([0])
    e.resultados["preprocesado"] = preprocesar(e)
    e.params("elegir_k").update(B=20)
    e.resultados["elegir_k"] = barrer(e, lambda f: None, lambda: False)
    e.params("modelo_final").update(k=3, B=20)
    e.resultados["modelo_final"] = ajustar(e, lambda f: None, lambda: False)
    return mod.exportar(e)


def test_requires_final_model():
    mod = KMeansModule()
    with pytest.raises(ErrorUsuario):
        mod.exportar(mod.crear_estado())


def test_csv_spanish_excel(tmp_path, exportacion):
    path = ex.escribir("csv", exportacion, tmp_path / "datos")[0]
    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")  # BOM para Excel
    df = pd.read_csv(path, sep=";", decimal=",", encoding="utf-8-sig")
    assert list(df.columns[-2:]) == ["cluster", "silueta"]
    assert pd.isna(df.loc[0, "cluster"])  # fila excluida del análisis
    assert set(df["cluster"].dropna().astype(int)) == {1, 2, 3}
    assert ";" in raw.decode("utf-8-sig").splitlines()[1] and "," in raw.decode("utf-8-sig").splitlines()[1]


def test_json_and_methods(tmp_path, exportacion):
    data = json.loads(ex.escribir("json", exportacion, tmp_path / "r.json")[0].read_text(encoding="utf-8"))
    assert data["parametros"]["modelo_final"]["k"] == 3
    assert data["resultados"]["modelo_final"]["tamanos"]
    md = ex.escribir("md", exportacion, tmp_path / "m")[0].read_text(encoding="utf-8")
    assert md.startswith("# Texto de métodos") and "Jaccard" in md


def test_figures_png_svg(tmp_path, exportacion):
    files = ex.escribir("figuras", exportacion, tmp_path / "figs")
    names = sorted(p.name for p in files)
    assert len(names) == 14 and "03_pca.png" in names and "03_pca.svg" in names
    png = (tmp_path / "figs" / "03_pca.png").read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    from PIL import Image  # matplotlib depende de Pillow

    with Image.open(tmp_path / "figs" / "01_codo.png") as im:
        assert round(im.info["dpi"][0]) == 300


def test_pdf_and_docx(tmp_path, exportacion):
    pdf = ex.escribir("pdf", exportacion, tmp_path / "informe")[0]
    assert pdf.read_bytes()[:4] == b"%PDF" and pdf.stat().st_size > 50_000
    docx = ex.escribir("docx", exportacion, tmp_path / "informe")[0]
    with zipfile.ZipFile(docx) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    for text in ("Informe de clustering k-means", "Parámetros del análisis", "Barrido de k", "Modelo final",
                 "Texto de métodos", "Versiones del software", "Muy estable"):
        assert text in xml
    # El orden de las secciones es el del documento de traspaso
    order = [xml.index(t) for t in ("Parámetros del análisis", "Barrido de k", "Modelo final", "Figuras",
                                    "Perfiles, variables", "Sensibilidad a la imputación", "Texto de métodos",
                                    "Versiones del software")]
    assert order == sorted(order)
    assert len([n for n in zipfile.ZipFile(docx).namelist() if n.startswith("word/media/")]) == 7


def test_everything_in_a_folder(tmp_path, exportacion):
    files = ex.escribir("todo", exportacion, tmp_path / "salida", base="ejemplo")
    names = {p.name for p in files}
    assert {"ejemplo_datos_con_clusters.csv", "ejemplo_resultados.json", "ejemplo_metodos.md",
            "ejemplo_informe.pdf", "ejemplo_informe.docx"} <= names
