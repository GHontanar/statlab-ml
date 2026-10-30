"""F2: modo «Preparar datos» (receta, revisión de calidad, diccionario, Mis fórmulas, flujo de pacientes)."""
import json
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialogButtonBox, QMessageBox
from ui_helpers import capture

from statlab.core.dataset import Rol
from statlab.core.flow import EstadoPaso as E
from statlab.ui.main_window import MODO_ANALIZAR, MODO_PREPARAR
from statlab.ui.prep.dictionary import DiccionarioDialog
from statlab.ui.prep.my_formulas import MisFormulasDialog, ruta

sys.path.insert(0, str(Path(__file__).parents[1] / "core"))
from test_prep_calidad import excel_sucio  # noqa: E402

MODEL = ["hb", "vcm", "plaquetas", "neutrofilos", "hbf", "ferritina"]


@pytest.fixture(autouse=True)
def sin_avisos_modales(monkeypatch):
    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: avisos.append(a[2])))
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: avisos.append(a[2])))
    return avisos


@pytest.fixture
def sucio(window, tmp_path):
    path = tmp_path / "registro.xlsx"
    path.write_bytes(excel_sucio())
    assert window.load_path(str(path))
    return window


def codigos(window):
    return [p.codigo for p in window.prep_sidebar.problemas]


def test_abrir_un_archivo_entra_en_preparar(sucio):
    w = sucio
    assert w.mode == MODO_PREPARAR
    assert w.sidebar_stack.currentWidget() is w.prep_sidebar
    assert w.results_stack.currentWidget() is w.prep_results
    assert w.header.mode_buttons[MODO_PREPARAR].isChecked() and w.header.modes.isVisible()
    sb = w.prep_sidebar
    assert sb.hoja.currentText() == "Datos" and sb.fila_cab.value() == 3 and sb.dos_filas.isChecked()
    assert w.session.dataset.n_filas == 60
    assert codigos(w)[:1] == ["unidades"]  # los graves primero
    assert {"categorias", "codigo_perdido", "fecha_texto"} <= set(codigos(w))
    capture(w, "f2-preparar-abierto")
    qtb = w.header.mode_buttons[MODO_ANALIZAR]
    qtb.click()
    assert w.mode == MODO_ANALIZAR and w.sidebar_stack.currentWidget() is w.sidebar


def test_corregir_con_vista_previa(sucio, qtbot):
    w, sb = sucio, sucio.prep_sidebar
    unidades = next(p for p in sb.problemas if p.codigo == "unidades")
    d = sb.open_dialog(unidades.propuesta.tipo, unidades.propuesta.params)
    qtbot.addWidget(d)
    d.actualizar()
    assert d.resumen.text().startswith("8 celdas cambian")
    assert d.tabla.rowCount() == 8 and d.tabla.item(0, 2).text() == "13,4"
    capture(d, "f2-dialogo-unidades")
    sb.add_from_dialog(d)
    assert len(w.session.prep.receta.pasos) == 1
    assert "unidades" not in codigos(w)
    assert w.session.dataset.df["Analítica hb"].max() < 20
    assert w.session.dirty

    paso = w.session.prep.receta.pasos[0]
    sb.toggle(paso.id, False)  # desactivar: vuelve a aparecer el problema
    assert "unidades" in codigos(w) and w.session.dataset.df["Analítica hb"].max() > 100
    sb.toggle(paso.id, True)
    sb.delete_step(paso.id)
    assert w.session.prep.receta.pasos == [] and "unidades" in codigos(w)


def test_ignorar_un_aviso(sucio):
    w, sb = sucio, sucio.prep_sidebar
    p = next(p for p in sb.problemas if p.codigo == "fecha_texto")
    w.session.ignore_problem(f"{p.codigo}:{p.columna}")
    assert "fecha_texto" not in codigos(w)


def test_cambiar_las_opciones_de_lectura(sucio, sin_avisos_modales):
    w, sb = sucio, sucio.prep_sidebar
    sb.dos_filas.setChecked(False)
    sb._opciones()
    assert w.session.dataset.columnas[0] == "Paciente"  # solo la fila de arriba
    assert w.session.prep.opciones.filas_cabecera == 1
    sb.dos_filas.setChecked(True)
    sb._opciones()
    assert w.session.dataset.columnas[0] == "Paciente id"


def test_formula_invalida_no_se_puede_anadir(window, qtbot):
    window.load_example()
    d = window.prep_sidebar.open_dialog("calcular", {"destino": "x", "formula": "hb +"})
    qtbot.addWidget(d)
    d.actualizar()
    assert not d.botones.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
    assert "incompleta" in d.resumen.text()
    d.widgets["formula"].setText("hb * 2")
    d.actualizar()
    assert d.botones.button(QDialogButtonBox.StandardButton.Ok).isEnabled()


def test_calculadora_y_mis_formulas(window, qtbot):
    window.load_example()
    window.set_mode(MODO_PREPARAR)
    sb = window.prep_sidebar
    d = sb.open_dialog("calcular", {"destino": "hb_vcm", "formula": "hb / vcm"})
    qtbot.addWidget(d)
    d.widgets["guardar"].setChecked(True)
    d.actualizar()
    assert "columna nueva «hb_vcm»" in d.resumen.text()
    sb.add_from_dialog(d)
    ds = window.session.dataset
    assert "hb_vcm" in ds.columnas and window.data_panel.model.columnCount() == len(ds.columnas)
    guardadas = json.loads(ruta().read_text(encoding="utf-8"))["formulas"]
    assert guardadas == [{"nombre": "hb_vcm", "formula": "hb / vcm", "descripcion": ""}]

    dlg = MisFormulasDialog(window.session, window)
    qtbot.addWidget(dlg)
    assert dlg.lista.count() == 1 and dlg.combos["hb"].currentText() == "hb"
    dlg.combos["vcm"].setCurrentText("plaquetas")
    dlg.destino.setText("hb_plaq")
    dlg.aplicar()
    pasos = window.session.prep.receta.pasos
    assert pasos[-1].params == {"destino": "hb_plaq", "formula": "([hb] / [plaquetas])", "origen": "hb_vcm"}
    assert "hb_plaq" in window.session.dataset.columnas


def test_excluir_actualiza_flujo_tabla_e_informe(window, qtbot):
    window.load_example()
    window.set_mode(MODO_PREPARAR)
    sb = window.prep_sidebar
    d = sb.open_dialog("excluir", {"condicion": "edad < 2", "motivo": "Menores de 2 años"})
    qtbot.addWidget(d)
    d.actualizar()
    n = window.session.dataset.df["edad"].lt(2).sum()
    assert d.resumen.text().startswith(f"{n} filas excluidas")
    sb.add_from_dialog(d)
    ds = window.session.dataset
    assert len(ds.excluidas_receta) == n and len(ds.filas_activas()) == 240 - n
    flujo = window.prep_results.diagrama.flujo
    assert flujo.exclusiones == [("Menores de 2 años", n)] and flujo.n_final == 240 - n
    fila = next(iter(ds.excluidas_receta))
    model = window.data_panel.model
    tip = model.headerData(model.view_row(fila), Qt.Orientation.Vertical, Qt.ItemDataRole.ToolTipRole)
    assert "Menores de 2 años" in tip
    # una exclusión a mano en la tabla también aparece
    otra = next(i for i in range(240) if i not in ds.excluidas_receta)
    window.session.exclude([otra])
    assert window.prep_results.diagrama.flujo.exclusiones[-1] == ("Excluidos a mano en la tabla", 1)
    capture(window, "f2-flujo-pacientes")


def test_cambiar_la_receta_conserva_roles_y_desactualiza(window, qtbot):
    window.load_example()
    s = window.session
    s.set_role(MODEL, Rol.MODELO)
    s.set_role(["id"], Rol.IDENTIFICADOR)
    assert s.complete("variables")
    qtbot.waitUntil(lambda: "preprocesado" in s.estado.resultados and not s.running("preprocesado"), timeout=10000)
    assert s.complete("preprocesado")
    from statlab.core.prep.receta import Paso

    s.change_preparation(lambda p: p.receta.añadir(Paso("calcular", {"destino": "x2", "formula": "hb * 2"})))
    assert s.dataset.roles["hb"] == Rol.MODELO and s.dataset.identificador == "id"
    assert s.flujo["preprocesado"] != E.HECHO  # hay que revisar el análisis con los datos nuevos


def test_sesion_guarda_la_receta(sucio, tmp_path):
    w = sucio
    sb = w.prep_sidebar
    for p in list(sb.problemas):
        if p.propuesta is not None:
            w.session.change_preparation(lambda prep, p=p: prep.receta.añadir(p.propuesta))
    pasos = [p.to_dict() for p in w.session.prep.receta.pasos]
    path = w.session.save_session(tmp_path / "con_receta.statlab")
    w.load_example()
    assert w.open_session_path(str(path))
    assert [p.to_dict() for p in w.session.prep.receta.pasos] == pasos
    assert w.mode == MODO_ANALIZAR
    assert not [c for c in codigos(w) if c in ("unidades", "categorias", "codigo_perdido")]


def test_diccionario(window, qtbot):
    window.load_example()
    d = DiccionarioDialog(window.session, window)
    qtbot.addWidget(d)
    fila = window.session.dataset.columnas.index("hb")
    d.tabla.item(fila, 1).setText("Hemoglobina")
    d.tabla.item(fila, 2).setText("g/dL")
    d.tabla.item(fila, 5).setText("10")  # máximo muy bajo: aparecen valores fuera de límites
    d._aceptar()
    dic = window.session.prep.diccionario
    assert dic.etiqueta("hb") == "Hemoglobina (g/dL)" and dic.get("hb").maximo == 10
    assert "fuera_limites" in codigos(window)
    assert "1 de 11" in window.prep_sidebar.dic_resumen.text()
