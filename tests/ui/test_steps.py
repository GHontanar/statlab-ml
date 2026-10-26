"""M2: estados de los pasos, invalidación en cascada y preprocesado."""
import pytest
from PySide6.QtCore import Qt
from ui_helpers import capture

from statlab.core.dataset import Rol
from statlab.core.flow import EstadoPaso as E

MODEL = ["hb", "vcm", "plaquetas", "neutrofilos", "hbf", "ferritina"]


@pytest.fixture
def session(window, qtbot):
    window.load_example()
    return window.session


def _wait_prep(qtbot, session):
    qtbot.waitUntil(lambda: not session.running("preprocesado") and "preprocesado" in session.estado.resultados,
                    timeout=10000)


def _setup_roles(session):
    session.set_role(MODEL, Rol.MODELO)
    session.toggle_log(["ferritina"])
    session.set_role(["edad", "sexo", "tph"], Rol.DESCRIPTIVA)
    session.set_role(["id"], Rol.IDENTIFICADOR)


def test_variables_validation_blocks_continue(window, session, qtbot):
    card = window.sidebar.cards["variables"]
    assert card.state == E.ACTIVO
    assert card.errors.isVisible() and "al menos 2" in card.errors.text()
    assert not card.primary.isEnabled()
    session.set_role(["hb", "vcm"], Rol.MODELO)
    assert not card.errors.isVisible() and card.primary.isEnabled()


def test_full_flow_with_preview(window, session, qtbot):
    _setup_roles(session)
    sidebar = window.sidebar
    qtbot.mouseClick(sidebar.cards["variables"].primary, Qt.MouseButton.LeftButton)
    assert session.flujo["variables"] == E.HECHO and session.flujo["preprocesado"] == E.ACTIVO
    _wait_prep(qtbot, session)
    prep_card = sidebar.cards["preprocesado"]
    widget = prep_card.content
    assert widget.result.text() == "240 filas analizadas · 0 excluidas · 80 celdas imputadas"
    assert prep_card.primary.isEnabled()

    # Cambiar a «sin escalar» recalcula la vista previa y muestra los avisos del motor.
    widget.scaling.setCurrentIndex(widget.scaling.findData("none"))
    _wait_prep(qtbot, session)
    qtbot.waitUntil(lambda: widget.warnings.isVisible())
    assert "Sin escalar" in widget.warnings.text()
    widget.scaling.setCurrentIndex(widget.scaling.findData("standard"))
    _wait_prep(qtbot, session)
    capture(window, "m2-preprocesado")

    qtbot.mouseClick(prep_card.primary, Qt.MouseButton.LeftButton)
    assert session.flujo["preprocesado"] == E.HECHO and session.flujo["elegir_k"] == E.ACTIVO
    assert "KNN, 5 vecinos (80 celdas imputadas)" in prep_card.summary.text()
    assert prep_card.summary.isVisible() and not widget.isVisible()


def test_cascade_stale_and_recalculate(window, session, qtbot):
    _setup_roles(session)
    session.complete("variables")
    _wait_prep(qtbot, session)
    session.complete("preprocesado")

    # Cambiar un rol en la tabla deja el preprocesado desactualizado y bloquea «Elegir k».
    session.set_role(["hbf"], None)
    card = window.sidebar.cards["preprocesado"]
    assert session.flujo["preprocesado"] == E.DESACTUALIZADO
    assert session.flujo["elegir_k"] == E.PENDIENTE
    assert card.stale_note.isVisible() and card.recalc_button.isVisible()
    assert "80 celdas" in card.summary.text()  # conserva el resultado visible
    capture(window, "m2-desactualizado")

    qtbot.mouseClick(card.recalc_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: session.flujo["preprocesado"] == E.HECHO, timeout=10000)
    assert session.estado.resultados["preprocesado"]["columnas"] == ["hb", "vcm", "plaquetas", "neutrofilos",
                                                                     "ferritina"]
    assert session.flujo["elegir_k"] == E.ACTIVO
    assert not card.stale_note.isVisible()


def test_invalid_change_reopens_variables(window, session, qtbot):
    _setup_roles(session)
    session.complete("variables")
    _wait_prep(qtbot, session)
    session.set_role(MODEL[1:], None)  # queda 1 variable
    assert session.flujo["variables"] == E.ACTIVO
    assert session.flujo["preprocesado"] == E.PENDIENTE
    assert "al menos 2" in window.sidebar.cards["variables"].errors.text()


def test_click_done_card_reopens(window, session, qtbot):
    _setup_roles(session)
    session.complete("variables")
    _wait_prep(qtbot, session)
    session.complete("preprocesado")
    card = window.sidebar.cards["preprocesado"]
    qtbot.mouseClick(card, Qt.MouseButton.LeftButton)
    assert session.flujo["preprocesado"] == E.ACTIVO and session.flujo["elegir_k"] == E.PENDIENTE
    assert card.content.isVisible()
    # Editar un parámetro del paso reabierto no afecta a los anteriores.
    card.content.neighbors.setValue(7)
    _wait_prep(qtbot, session)
    assert session.params("preprocesado")["vecinos"] == 7
    assert session.flujo["variables"] == E.HECHO


def test_preprocess_error_is_human(window, session, qtbot):
    session.set_role(["hb", "vcm"], Rol.MODELO)
    df = session.dataset.df
    # 12 filas, cada una con algún NA en hb o vcm: pasan la validación del paso 2, pero
    # con casos completos no queda ninguna fila y el motor lo rechaza.
    filas = df.index[df[["hb", "vcm"]].isna().any(axis=1)].tolist()[:12]
    assert df.loc[filas, "hb"].notna().any() and df.loc[filas, "vcm"].notna().any()
    session.analyze_only(filas)
    session.complete("variables")
    _wait_prep(qtbot, session)
    card = window.sidebar.cards["preprocesado"]
    card.content.missing.setCurrentIndex(card.content.missing.findData("complete"))
    qtbot.waitUntil(lambda: "error" in session.estado.resultados.get("preprocesado", {}), timeout=10000)
    assert "Solo quedan 0 filas" in card.content.warnings.text()
    assert "Traceback" not in card.content.warnings.text()
    assert not card.primary.isEnabled()
    assert not session.complete("preprocesado")


def test_new_data_resets_flow(window, session, qtbot):
    _setup_roles(session)
    session.complete("variables")
    _wait_prep(qtbot, session)
    window.load_example()
    assert session.flujo.to_dict()["variables"] == "active"
    assert session.estado.resultados == {}
    assert session.dataset.roles == {}
