"""M5: exportes desde el paso 6, en segundo plano."""
import pandas as pd
import pytest
from PySide6.QtCore import Qt
from ui_helpers import capture

from statlab.core.dataset import Rol
from statlab.core.flow import EstadoPaso as E
from statlab.modules.kmeans.steps import ExportWidget

MODEL = ["hb", "vcm", "plaquetas", "neutrofilos", "hbf", "ferritina"]


@pytest.fixture
def fitted(window, qtbot):
    window.load_example()
    s = window.session
    s.set_role(MODEL, Rol.MODELO)
    s.toggle_log(["ferritina"])
    s.set_role(["edad", "sexo", "tph"], Rol.DESCRIPTIVA)
    s.complete("variables")
    qtbot.waitUntil(lambda: "preprocesado" in s.estado.resultados and not s.running("preprocesado"), timeout=10000)
    s.complete("preprocesado")
    s.set_params("elegir_k", B=20)
    s.primary("elegir_k")
    qtbot.waitUntil(lambda: s.flujo["elegir_k"] == E.HECHO, timeout=60000)
    s.set_params("modelo_final", k=3, B=20)
    s.primary("modelo_final")
    qtbot.waitUntil(lambda: s.flujo["modelo_final"] == E.HECHO, timeout=60000)
    return window


def test_export_buttons(fitted, qtbot, tmp_path, monkeypatch):
    s = fitted.session
    card = fitted.sidebar.cards["exportar"]
    widget: ExportWidget = card.content
    assert card.state == E.ACTIVO and widget.isVisible()
    targets = {"pdf": tmp_path / "informe.pdf", "csv": tmp_path / "datos.csv", "todo": tmp_path / "todo"}
    monkeypatch.setattr(ExportWidget, "_ask_path", lambda self, tipo: str(targets[tipo]))

    with qtbot.waitSignal(s.message, timeout=60000) as msg:
        qtbot.mouseClick(widget.buttons["pdf"], Qt.MouseButton.LeftButton)
        assert not widget.buttons["csv"].isEnabled()  # mientras exporta
    assert "informe.pdf" in msg.args[0]
    assert targets["pdf"].read_bytes()[:4] == b"%PDF"
    from statlab.modules.kmeans.panels import FinalPanel

    panel = fitted.results.findChild(FinalPanel)
    assert panel is not None and panel.isVisible()  # el panel sigue mostrando el modelo
    assert s.flujo["exportar"] == E.HECHO
    assert widget.isVisible() and widget.buttons["csv"].isEnabled()  # se puede volver a exportar
    assert "informe.pdf" in card.summary.text() or card.summary.isHidden()

    with qtbot.waitSignal(s.message, timeout=60000):
        qtbot.mouseClick(widget.buttons["csv"], Qt.MouseButton.LeftButton)
    df = pd.read_csv(targets["csv"], sep=";", decimal=",", encoding="utf-8-sig")
    assert df["cluster"].value_counts().sort_index().tolist() == [109, 76, 55]

    with qtbot.waitSignal(s.message, timeout=120000) as msg:
        qtbot.mouseClick(widget.buttons["todo"], Qt.MouseButton.LeftButton)
    assert (targets["todo"] / "figuras" / "03_pca.svg").exists()
    assert (targets["todo"] / "datos_ejemplo_informe.docx").exists()
    capture(fitted, "m5-exportar")


def test_export_error_is_human(fitted, qtbot, tmp_path, monkeypatch):
    s = fitted.session
    widget = fitted.sidebar.cards["exportar"].content
    blocked = tmp_path / "no_es_carpeta"
    blocked.write_text("x")
    monkeypatch.setattr(ExportWidget, "_ask_path", lambda self, tipo: str(blocked / "informe.pdf"))
    with qtbot.waitSignal(s.message, timeout=60000) as msg:
        widget.export("pdf")
    assert "No se ha podido escribir" in msg.args[0] and "Traceback" not in msg.args[0]
