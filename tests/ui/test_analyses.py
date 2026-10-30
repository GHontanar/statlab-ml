"""F3: varios análisis en una sesión, cada uno en su pestaña."""
from ui_helpers import capture

from statlab.core.dataset import Rol
from statlab.core.prep.receta import Paso
from statlab.ui.main_window import MODO_ANALIZAR, MODO_PREPARAR, MainWindow

MODEL = ["hb", "vcm", "plaquetas", "neutrofilos", "hbf", "ferritina"]


def _dos(window):
    window.load_example()
    window.session.set_role(MODEL, Rol.MODELO)
    window.session.set_role(["id"], Rol.IDENTIFICADOR)
    window.new_analysis("gmm")
    return window.workspaces


def test_nuevo_analisis_copia_roles_y_filas(window):
    window.load_example()
    assert window.tabs.isVisible() and len(window.workspaces) == 1
    assert window.tabs.bar.count() == 2 and window.tabs.bar.tabText(1) == "Comparar soluciones"
    window.session.set_role(MODEL, Rol.MODELO)
    window.session.exclude([0, 1])
    k = window.workspace
    g = window.new_analysis("gmm")
    assert len(window.workspaces) == 2 and window.tabs.bar.currentIndex() == 1
    assert g.module.id == "gmm" and window.session is g.session
    assert g.session.dataset.con_rol(Rol.MODELO) == MODEL and g.session.dataset.excluidas == {0, 1}
    assert g.session.prep is k.session.prep  # preparación compartida
    assert [window.tabs.bar.tabText(i) for i in range(2)] == ["k-means", "GMM"]
    assert window.header.module_label.text() == "Mezclas gaussianas (GMM)"
    # roles independientes desde ahora
    g.session.set_role(["hb"], None)
    assert "hb" in k.session.dataset.con_rol(Rol.MODELO)
    window.tabs.bar.setCurrentIndex(0)
    assert window.session is k.session and window.sidebar is k.sidebar
    window.set_mode(MODO_PREPARAR)
    assert not window.tabs.isVisible()  # la preparación es común: sin pestañas
    window.set_mode(MODO_ANALIZAR)
    capture(window, "f3-pestanas")


def test_la_receta_llega_a_todos_los_analisis(window):
    k, g = _dos(window)
    window.set_mode(MODO_PREPARAR)
    k.session.change_preparation(lambda p: p.receta.añadir(Paso("calcular", {"destino": "x2", "formula": "hb * 2"})))
    assert "x2" in g.session.dataset.columnas and "x2" in g.data_panel.model.dataset.columnas
    assert g.session.dataset.con_rol(Rol.MODELO) == MODEL  # conserva sus roles
    k.session.change_dictionary(lambda d: setattr(d.entrada("hb"), "etiqueta", "Hemoglobina"))
    assert g.session.prep.diccionario.etiqueta("hb") == "Hemoglobina"


def test_guardar_y_abrir_varios_analisis(window, qtbot, tmp_path, monkeypatch):
    k, g = _dos(window)
    monkeypatch.setattr(MainWindow, "_ask_name", lambda self, ws: ("Mi GMM", True))
    window.rename_analysis(1)
    assert window.tabs.bar.tabText(1) == "Mi GMM" and window.dirty
    g.session.set_params("elegir_k", covarianza="diag")
    path = window.session.save_session(tmp_path / "dos.statlab")
    assert not window.dirty

    other = MainWindow(k.module)
    qtbot.addWidget(other)
    other.show()
    assert other.load_path(str(path))
    assert [other.tabs.bar.tabText(i) for i in range(other.tabs.bar.count())] == ["k-means", "Mi GMM",
                                                                              "Comparar soluciones"]
    assert other.workspace.module.id == "gmm"  # el que estaba activo
    assert other.session.params("elegir_k")["covarianza"] == "diag"
    assert other.workspaces[0].session.prep is other.workspaces[1].session.prep
    assert not other.dirty
    # abrir unos datos nuevos deja una sola pestaña
    other.load_example()
    assert len(other.workspaces) == 1 and other.tabs.bar.count() == 2


def test_cerrar_un_analisis(window, monkeypatch):
    k, g = _dos(window)
    assert window.tabs.bar.tabsClosable()
    assert not window.close_analysis(2)  # la pestaña de comparación no se cierra
    assert window.close_analysis(1)
    assert len(window.workspaces) == 1 and window.session is k.session
    assert not window.tabs.bar.tabsClosable()
    assert not window.close_analysis(0)  # siempre queda uno
