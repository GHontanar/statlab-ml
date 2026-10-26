"""M4: modelo final — KPIs, pestañas, enlace PCA/lazo ↔ tabla, columna cluster y resaltado."""
import numpy as np
import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QPolygonF
from ui_helpers import capture

from statlab.core.dataset import Rol
from statlab.core.flow import EstadoPaso as E
from statlab.modules.kmeans.panels import FinalPanel
from statlab.ui.data_table.model import ROLE_CLUSTER

MODEL = ["hb", "vcm", "plaquetas", "neutrofilos", "hbf", "ferritina"]


@pytest.fixture
def fitted(window, qtbot):
    """Criterio de aceptación: k = 3 sobre los datos de ejemplo, modelo ajustado y validado."""
    window.load_example()
    s = window.session
    s.set_role(MODEL, Rol.MODELO)
    s.toggle_log(["ferritina"])
    s.set_role(["edad", "sexo", "tph"], Rol.DESCRIPTIVA)
    s.set_role(["id"], Rol.IDENTIFICADOR)
    s.complete("variables")
    qtbot.waitUntil(lambda: "preprocesado" in s.estado.resultados and not s.running("preprocesado"), timeout=10000)
    s.complete("preprocesado")
    s.set_params("elegir_k", bootstrap=False)
    s.primary("elegir_k")
    qtbot.waitUntil(lambda: s.flujo["elegir_k"] == E.HECHO, timeout=60000)
    s.set_params("modelo_final", k=3, B=50)
    card = window.sidebar.cards["modelo_final"]
    assert card.content.k.currentData() == 3 and card.content.B.currentData() == 50
    qtbot.mouseClick(card.primary, Qt.MouseButton.LeftButton)
    assert card.running_box.isVisible()  # la UI sigue respondiendo
    qtbot.waitUntil(lambda: s.flujo["modelo_final"] == E.HECHO, timeout=60000)
    window.work_splitter.setSizes([260, 640])
    return window


def test_kpis_and_tabs(fitted):
    panel = fitted.results.findChild(FinalPanel)
    assert panel is not None
    assert panel.kpi_sil.value.text() == "0,52"
    assert panel.kpi_ari.value.text() == "1,00"
    assert panel.kpi_unstable.value.text() == "0 de 3"
    assert "C1 · 109 (45 %)" in panel.sizes.text() and "C3 · 55 (23 %)" in panel.sizes.text()
    tabs = [panel.tabs.tabText(i) for i in range(panel.tabs.count())]
    assert tabs == ["Resumen", "Silueta", "Estabilidad", "Sensibilidad a la imputación", "Variables descriptivas"]
    st = panel.stability_table
    assert [st.item(i, 5).text() for i in range(3)] == ["Muy estable"] * 3
    assert "no dependen" in panel.sensitivity_warning.text()
    assert panel.descriptive_table.item(0, 0).text() == "edad"
    assert fitted.session.flujo["exportar"] == E.ACTIVO
    assert "109 / 76 / 55" in fitted.sidebar.cards["modelo_final"].summary.text()
    capture(fitted, "m4-modelo-final")
    for i, name in enumerate(["resumen", "silueta", "estabilidad", "sensibilidad", "descriptivas"]):
        panel.tabs.setCurrentIndex(i)
        capture(fitted.results, f"m4-pestana-{name}")


def test_table_gets_cluster_columns_and_highlight(fitted, qtbot):
    dp = fitted.data_panel
    model = dp.model
    assert model.column_name(0) == "cluster" and model.column_name(1) == "silueta"
    r = fitted.session.estado.resultados["modelo_final"]
    first = r["filas"][0]
    assert model.data(model.index(model.view_row(first), 0), ROLE_CLUSTER) == r["etiquetas"][0]
    assert model.data(model.index(0, 1)).count(",") == 1  # silueta con coma decimal
    # Las columnas de resultado no aceptan roles; las demás siguen funcionando.
    dp.select_columns(["cluster", "hb"])
    assert dp.selected_columns() == ["hb"]

    texts = [b.text() for b in dp.highlight_buttons]
    assert texts == ["● C1", "■ C2", "◆ C3", "Todos"]
    qtbot.mouseClick(dp.highlight_buttons[1], Qt.MouseButton.LeftButton)
    assert model.highlight == 1
    c2_row = next(i for i, c in zip(r["filas"], r["etiquetas"], strict=True) if c == 1)
    c1_row = next(i for i, c in zip(r["filas"], r["etiquetas"], strict=True) if c == 0)
    assert model.data(model.index(model.view_row(c2_row), 5), Qt.ItemDataRole.BackgroundRole) is not None
    muted = model.data(model.index(model.view_row(c1_row), 5), Qt.ItemDataRole.ForegroundRole)
    assert muted.name().lower() == "#6e6d68"
    capture(fitted, "m4-resaltado")
    qtbot.mouseClick(dp.highlight_buttons[-1], Qt.MouseButton.LeftButton)
    assert model.highlight is None
    # Ordenar por cluster
    model.sort(0, Qt.SortOrder.AscendingOrder)
    assert model.data(model.index(0, 0), ROLE_CLUSTER) == 0


def test_pca_click_and_lasso_select_rows(fitted, qtbot):
    panel = fitted.results.findChild(FinalPanel)
    pca = panel.pca
    dp = fitted.data_panel
    # Clic real en un punto
    i = 0
    x, y = pca.coords[i]
    scene = pca.getViewBox().mapViewToScene(QPointF(x, y))
    pos = pca.mapFromScene(scene)
    qtbot.mouseClick(pca.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(int(pos.x()), int(pos.y())))
    assert int(pca.rows[i]) in dp.selected_rows()
    # Lazo alrededor del centroide de C3 → selecciona filas de C3
    c3 = pca.coords[pca.labels == 2]
    cx, cy = c3.mean(axis=0)
    d = 1.2
    square = QPolygonF([QPointF(cx - d, cy - d), QPointF(cx + d, cy - d), QPointF(cx + d, cy + d),
                        QPointF(cx - d, cy + d)])
    pca.box.lasso_finished.emit(square)
    selected = dp.selected_rows()
    labels = dict(zip(pca.rows.tolist(), pca.labels.tolist(), strict=True))
    assert len(selected) >= 30 and {labels[r] for r in selected} == {2}
    assert dp.row_bar.isVisible()
    assert len(pca.highlight.getData()[0]) == len(selected)


def test_heatmap_row_shows_original_units(fitted, qtbot):
    panel = fitted.results.findChild(FinalPanel)
    hm = panel.heatmap
    qtbot.mouseClick(hm, Qt.MouseButton.LeftButton, pos=QPoint(hm.width() // 2, 26 + 34 // 2))
    assert panel.profile.isVisible()
    assert panel.profile.text().startswith("C1 (n = 109): hb 12,66 (1,03)")


def test_changing_k_marks_final_stale_and_recalculates(fitted, qtbot):
    s = fitted.session
    s.set_params("modelo_final", k=2)
    assert s.flujo["modelo_final"] == E.DESACTUALIZADO and s.flujo["exportar"] == E.PENDIENTE
    fitted.results.refresh()
    assert fitted.results.stale.isVisible()
    s.recalculate("modelo_final")
    qtbot.waitUntil(lambda: s.flujo["modelo_final"] == E.HECHO, timeout=60000)
    r = s.estado.resultados["modelo_final"]
    assert r["k"] == 2 and len(fitted.data_panel.highlight_buttons) == 3


def test_reopen_sweep_and_leave_unchanged(fitted, qtbot):
    s = fitted.session
    s.reopen("elegir_k")
    assert s.flujo["elegir_k"] == E.ACTIVO
    from statlab.modules.kmeans.panels import SweepPanel

    assert fitted.results.findChild(SweepPanel) is not None  # vuelve a verse el barrido
    s.reopen("modelo_final")  # salir sin cambiar nada
    assert s.flujo["elegir_k"] == E.HECHO
    assert s.flujo["modelo_final"] == E.ACTIVO


def test_new_data_removes_cluster_columns(fitted):
    fitted.load_example()
    assert not fitted.data_panel.model.has_results
    assert not fitted.data_panel.highlight_bar.isVisible()
    assert np.all(fitted.data_panel.model.column_name(0) == "id")
