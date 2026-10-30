"""M3: barrido de k en segundo plano, gráficos, tabla de índices y elección de k por clic."""
import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from ui_helpers import capture

from statlab.core.dataset import Rol
from statlab.core.flow import EstadoPaso as E
from statlab.modules.kmeans.panels import SweepPanel

MODEL = ["hb", "vcm", "plaquetas", "neutrofilos", "hbf", "ferritina"]


@pytest.fixture
def ready(window, qtbot):
    """Datos de ejemplo con el preprocesado del criterio de aceptación ya hecho."""
    window.load_example()
    s = window.session
    s.set_role(MODEL, Rol.MODELO)
    s.toggle_log(["ferritina"])
    s.set_role(["edad", "sexo", "tph"], Rol.DESCRIPTIVA)
    s.set_role(["id"], Rol.IDENTIFICADOR)
    s.complete("variables")
    qtbot.waitUntil(lambda: "preprocesado" in s.estado.resultados and not s.running("preprocesado"), timeout=10000)
    s.complete("preprocesado")
    assert s.flujo["elegir_k"] == E.ACTIVO
    return window


def _run_sweep(window, qtbot, timeout=60000):
    card = window.sidebar.cards["elegir_k"]
    qtbot.mouseClick(card.primary, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: window.session.flujo["elegir_k"] == E.HECHO, timeout=timeout)


def test_sweep_results_and_panel(ready, qtbot):
    s = ready.session
    s.set_params("elegir_k", B=20)  # más rápido en los tests
    card = ready.sidebar.cards["elegir_k"]
    qtbot.mouseClick(card.primary, Qt.MouseButton.LeftButton)
    assert s.running("elegir_k")
    assert card.running_box.isVisible() and not card.primary.isEnabled()  # la UI no se bloquea
    qtbot.waitUntil(lambda: s.flujo["elegir_k"] == E.HECHO, timeout=60000)
    assert not card.running_box.isVisible()
    assert s.flujo["modelo_final"] == E.ACTIVO

    r = s.estado.resultados["elegir_k"]
    assert r["mejor"] == {"silueta": 2, "ch": 3, "db": 2, "codo": 3, "criterio": 3}
    assert round(r["silueta"][0], 3) == 0.557
    assert len(r["boot"]["ic_inf"]) == 7

    panel = ready.results.findChild(SweepPanel)
    assert panel is not None and panel.isVisible()
    chips = [c.text() for c in panel.findChildren(type(panel.card_body)) if c.objectName() == "KChip"]
    assert chips == ["Silueta: k = 2", "Calinski-Harabasz: k = 3", "Davies-Bouldin: k = 2", "Codo ≈ 3"]
    table = panel.table
    assert table.item(0, 2).text() == "0,557" and table.item(0, 2).font().bold()  # mejor silueta
    assert table.item(1, 4).font().bold() and not table.item(0, 4).font().bold()  # mejor CH en k = 3
    assert panel.k == 2  # por defecto, el de mejor silueta
    assert "k elegido: 2" in card.summary.text()
    ready.work_splitter.setSizes([200, 700])
    s.set_params("modelo_final", k=3)
    capture(ready, "m3-barrido")


def _click_point(qtbot, chart, k):
    y = chart.values[chart.ks.index(k)]
    scene = chart.getViewBox().mapViewToScene(QPointF(k, y))
    pos = chart.mapFromScene(scene)
    qtbot.mouseClick(chart.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(int(pos.x()), int(pos.y())))


def test_choose_k_by_clicking_chart(ready, qtbot):
    s = ready.session
    s.set_params("elegir_k", bootstrap=False)
    _run_sweep(ready, qtbot)
    ready.work_splitter.setSizes([200, 700])
    panel = ready.results.findChild(SweepPanel)
    _click_point(qtbot, panel.silhouette, 3)
    assert s.params("modelo_final")["k"] == 3
    assert panel.k == 3
    assert list(panel.elbow.ring.getData()[0]) == [3]
    assert "k elegido: 3" in panel.card_body.text()
    assert "k elegido: 3" in ready.sidebar.cards["elegir_k"].summary.text()
    _click_point(qtbot, panel.elbow, 4)
    assert s.params("modelo_final")["k"] == 4
    _click_point(qtbot, panel.elbow, 3)
    assert s.params("modelo_final")["k"] == 3


def test_cancel_sweep(ready, qtbot):
    s = ready.session
    s.set_params("elegir_k", B=200)
    card = ready.sidebar.cards["elegir_k"]
    qtbot.mouseClick(card.primary, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: card.running_box.isVisible())
    qtbot.mouseClick(card.cancel_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: not s.running("elegir_k"), timeout=10000)
    assert s.flujo["elegir_k"] == E.ACTIVO
    assert "elegir_k" not in s.estado.resultados
    assert card.primary.isEnabled() and not card.running_box.isVisible()


def test_upstream_change_marks_sweep_stale(ready, qtbot):
    s = ready.session
    s.set_params("elegir_k", bootstrap=False)
    _run_sweep(ready, qtbot)
    s.set_role(["hbf"], None)
    assert s.flujo["preprocesado"] == E.DESACTUALIZADO and s.flujo["elegir_k"] == E.DESACTUALIZADO
    assert s.flujo["modelo_final"] == E.PENDIENTE
    ready.results.refresh()
    assert ready.results.stale.isVisible()  # el resultado sigue visible, marcado
    # Recalcular el barrido exige antes recalcular el preprocesado.
    with qtbot.waitSignal(s.message) as blocker:
        s.recalculate("elegir_k")
    assert "Preprocesado" in blocker.args[0]
    s.recalculate("preprocesado")
    qtbot.waitUntil(lambda: s.flujo["preprocesado"] == E.HECHO, timeout=10000)
    s.recalculate("elegir_k")
    qtbot.waitUntil(lambda: s.flujo["elegir_k"] == E.HECHO, timeout=60000)
    assert s.estado.resultados["elegir_k"]["n"] == 240
    assert not ready.results.stale.isVisible()


def test_range_slider_keyboard(ready, qtbot):
    widget = ready.sidebar.cards["elegir_k"].content
    slider = widget.range
    slider.setFocus()
    qtbot.keyClick(slider, Qt.Key.Key_Right)  # tirador izquierdo: 2 → 3
    qtbot.keyClick(slider, Qt.Key.Key_Tab)
    qtbot.keyClick(slider, Qt.Key.Key_Left)  # tirador derecho: 8 → 7
    p = ready.session.params("elegir_k")
    assert (p["k_min"], p["k_max"]) == (3, 7)
    assert widget.range_value.text() == "de 3 a 7"
    slider.set_values(5, 5)
    assert slider.values() == (5, 6)  # siempre al menos dos valores de k
