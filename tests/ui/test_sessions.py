"""M5: guardar y abrir sesiones .statlab desde la app; aviso de cambios sin guardar."""
from PySide6.QtWidgets import QFileDialog

from statlab.core.dataset import Rol
from statlab.core.flow import EstadoPaso as E
from statlab.modules.kmeans.panels import FinalPanel
from statlab.ui.main_window import MainWindow

MODEL = ["hb", "vcm", "plaquetas", "neutrofilos", "hbf", "ferritina"]


def _fit(window, qtbot):
    window.load_example()
    s = window.session
    s.set_role(MODEL, Rol.MODELO)
    s.toggle_log(["ferritina"])
    s.set_role(["edad", "sexo"], Rol.DESCRIPTIVA)
    s.complete("variables")
    qtbot.waitUntil(lambda: "preprocesado" in s.estado.resultados and not s.running("preprocesado"), timeout=10000)
    s.complete("preprocesado")
    s.set_params("elegir_k", bootstrap=False)
    s.primary("elegir_k")
    qtbot.waitUntil(lambda: s.flujo["elegir_k"] == E.HECHO, timeout=60000)
    s.set_params("modelo_final", k=3, B=20)
    s.primary("modelo_final")
    qtbot.waitUntil(lambda: s.flujo["modelo_final"] == E.HECHO, timeout=60000)


def test_save_and_reopen_restores_screen(window, qtbot, tmp_path, monkeypatch):
    _fit(window, qtbot)
    s = window.session
    assert s.dirty and window.isWindowModified()
    target = tmp_path / "mi_analisis"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), ""))
    with qtbot.waitSignal(s.message) as msg:
        assert window.save_session()
    assert "ubicación segura" in msg.args[0]
    assert not s.dirty and not window.isWindowModified()
    assert "mi_analisis.statlab" in window.windowTitle()
    saved = tmp_path / "mi_analisis.statlab"
    assert saved.exists()

    before = {
        "flujo": s.flujo.to_dict(),
        "summaries": {k: c.summary.text() for k, c in window.sidebar.cards.items()},
        "kpi": window.results.findChild(FinalPanel).kpi_sil.value.text(),
        "cols": [window.data_panel.model.column_name(i) for i in range(3)],
        "highlight": [b.text() for b in window.data_panel.highlight_buttons],
    }

    # Otra ventana, como si se hubiera cerrado y vuelto a abrir la app
    other = MainWindow(s.module)
    qtbot.addWidget(other)
    other.show()
    assert other.load_path(str(saved))
    o = other.session
    assert not o.running("modelo_final") and not o.running("elegir_k")  # nada se recalcula
    assert o.flujo.to_dict() == before["flujo"]
    assert {k: c.summary.text() for k, c in other.sidebar.cards.items()} == before["summaries"]
    assert other.results.findChild(FinalPanel).kpi_sil.value.text() == before["kpi"]
    assert [other.data_panel.model.column_name(i) for i in range(3)] == before["cols"]
    assert [b.text() for b in other.data_panel.highlight_buttons] == before["highlight"]
    assert other.sidebar.cards["modelo_final"].content.k.currentData() == 3
    assert not o.dirty


def test_unsaved_changes_prompt(window, qtbot, tmp_path, monkeypatch):
    window.load_example()
    window.session.set_role(["hb", "vcm"], Rol.MODELO)
    assert window.session.dirty
    answers = iter(["cancel", "save"])
    monkeypatch.setattr(MainWindow, "_ask_unsaved", lambda self: next(answers))
    assert window.maybe_save() is False  # Cancelar: no se hace nada
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(tmp_path / "x.statlab"), ""))
    assert window.maybe_save() is True  # Guardar
    assert (tmp_path / "x.statlab").exists() and not window.session.dirty


def test_open_invalid_session_shows_message(window, tmp_path, monkeypatch):
    bad = tmp_path / "roto.statlab"
    bad.write_bytes(b"basura")
    shown = {}
    monkeypatch.setattr("statlab.ui.main_window.QMessageBox.warning", lambda p, t, text: shown.update(text=text))
    assert not window.load_path(str(bad))
    assert "no es una sesión de StatLab válida" in shown["text"]
