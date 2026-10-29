"""F3: comparar soluciones (ARI, Sankey, tabla cruzada, importar, guardar)."""
from pathlib import Path

from ui_helpers import capture

from statlab.core.dataset import Rol
from statlab.core.flow import EstadoPaso as E
from statlab.core.report import exports as ex
from statlab.ui.main_window import MODO_ANALIZAR, MainWindow

COHORTE = Path(__file__).parents[2] / "ejemplos" / "cohorte_cardiometabolica_prueba.csv"
VARS = ["imc", "glucosa", "hba1c", "colesterol_ldl", "trigliceridos", "pcr", "tas", "creatinina"]


def _ajustar(s, qtbot):
    s.complete("variables")
    qtbot.waitUntil(lambda: "preprocesado" in s.estado.resultados and not s.running("preprocesado"), timeout=20000)
    s.complete("preprocesado")
    s.set_params("elegir_k", bootstrap=False, k_max=6)
    s.primary("elegir_k")
    qtbot.waitUntil(lambda: s.flujo["elegir_k"] == E.HECHO, timeout=90000)
    s.set_params("modelo_final", k=4, B=20)
    s.primary("modelo_final")
    qtbot.waitUntil(lambda: s.flujo["modelo_final"] == E.HECHO, timeout=90000)


def _dos_ajustados(window, qtbot):
    assert window.load_path(str(COHORTE))
    window.set_mode(MODO_ANALIZAR)
    s = window.session
    s.set_role(VARS, Rol.MODELO)
    s.toggle_log(["trigliceridos", "pcr"])
    s.set_role(["id"], Rol.IDENTIFICADOR)
    _ajustar(s, qtbot)
    g = window.new_analysis("gmm")
    g.session.set_params("elegir_k", covarianza="diag")
    _ajustar(g.session, qtbot)
    return window.workspaces


def test_comparar_kmeans_y_gmm(window, qtbot, tmp_path):
    k, g = _dos_ajustados(window, qtbot)
    assert window.tabs.bar.tabText(2) == "Comparar soluciones"
    window.tabs.bar.setCurrentIndex(2)
    assert window.comparing and window.session is g.session  # los atajos siguen apuntando a un análisis
    c = window.comparison
    r = c.resultado
    assert r is not None and r["a"] == "k-means · k = 4" and r["b"] == "GMM · k = 4"
    assert r["ari"] >= 0.90 and c.kpi_ari.value.text() == f"{r['ari']:.2f}".replace(".", ",")
    assert c.cruzada.rowCount() == 4 and c.sankey.r is r
    capture(window, "f3-comparar")
    # seleccionar los que cambian lleva a la tabla de A
    if r["n_discordantes"]:
        c.ver_disc.click()
        assert window.workspace is k and not window.comparing

    # importar la misma solución de k-means exportada a CSV: ARI idéntico al de la sesión
    csv = ex.escribir("csv", k.module.exportar(k.session.estado), tmp_path / "km")[0]
    window.show_comparison()
    c.importar_csv(str(csv))
    assert c.eleccion["b"] == "importada:0" and c.lista.count() == 1
    c.eleccion["a"] = "analisis:a1"
    c.refresh()
    assert c.resultado["ari"] == 1.0  # la misma partición
    assert window.dirty

    # guardar y abrir conserva lo importado y la elección
    path = window.session.save_session(tmp_path / "comparada.statlab")
    other = MainWindow(k.module)
    qtbot.addWidget(other)
    other.show()
    assert other.load_path(str(path))
    other.show_comparison()
    assert len(other.comparison.importadas) == 1 and other.comparison.resultado["ari"] == 1.0


def test_sin_dos_soluciones_explica_que_falta(window):
    window.load_example()
    window.show_comparison()
    c = window.comparison
    assert c.resultado is None and c.vacio.isVisible() and "dos soluciones" in c.vacio.text()
