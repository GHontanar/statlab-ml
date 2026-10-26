"""Prueba de extremo a extremo de la página con el AppTest de Streamlit."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")
VARS = ["hb", "vcm", "plaquetas", "neutrofilos", "hbf", "ferritina"]


def _run_full(imputation="knn", boot_k=False):
    at = AppTest.from_file(APP, default_timeout=180)
    at.run()
    assert not at.exception
    at.sidebar.selectbox[0].set_value("id")
    at.run()
    at.sidebar.multiselect[0].set_value(VARS)
    at.run()
    sb = at.sidebar
    sb.multiselect[1].set_value(["ferritina"])
    sb.multiselect[2].set_value(["edad", "sexo", "tph", "fenotipo_simulado"])
    sb.selectbox[1].set_value(imputation)
    if boot_k:
        sb.toggle[1].set_value(True)
    at.run()
    assert not at.exception, at.exception
    at.button[0].click().run()          # barrido de k
    assert not at.exception, at.exception
    at.selectbox[0].set_value(3)        # k final (selectbox del área principal)
    at.select_slider[0].set_value(100)
    at.run()
    at.button[1].click().run()          # ajustar y validar
    assert not at.exception, at.exception
    return at


def test_full_flow_knn():
    at = _run_full("knn", boot_k=True)
    labels = [m.label for m in at.metric]
    assert "Silueta media" in labels and "IC95% bootstrap" in labels
    sil = float(next(m.value for m in at.metric if m.label == "Silueta media"))
    assert sil > 0.3
    assert any("Hennig" in str(t.value) for t in at.text_area) or len(at.text_area) == 1


def test_full_flow_complete_cases():
    at = _run_full("complete")
    excl = next(m.value for m in at.metric if m.label == "Excluidas")
    assert int(excl) > 0
