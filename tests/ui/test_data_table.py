import time

import numpy as np
import pandas as pd
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QMessageBox
from ui_helpers import capture

from statlab.core.dataset import Rol
from statlab.ui.data_table.panel import DataPanel, DataTableView

MODEL = ["hb", "vcm", "plaquetas", "neutrofilos", "hbf", "ferritina"]


@pytest.fixture
def loaded(window, qtbot):
    window.load_example()
    qtbot.waitUntil(lambda: window.data_stack.currentWidget() is window.data_panel)
    return window


def _col_pos(table: DataTableView, name: str) -> QPoint:
    header = table.horizontalHeader()
    c = table.model().column_index(name)
    table.scrollTo(table.model().index(0, c))
    return QPoint(header.sectionViewportPosition(c) + 12, header.height() // 2)


def _row_pos(table: DataTableView, view_row: int) -> QPoint:
    header = table.verticalHeader()
    return QPoint(header.width() // 2, header.sectionViewportPosition(view_row) + 8)


def _click_header(qtbot, table, name, modifier=Qt.KeyboardModifier.NoModifier, button=Qt.MouseButton.LeftButton):
    qtbot.mouseClick(table.horizontalHeader().viewport(), button, modifier, _col_pos(table, name))


def test_load_example(loaded):
    panel: DataPanel = loaded.data_panel
    model = panel.model
    assert model.rowCount() == 240 and model.columnCount() == 11
    assert "datos_ejemplo.csv · 240 filas × 11 columnas" in panel.title.text()
    hb = model.column_index("hb")
    na_row = int(np.flatnonzero(loaded.session.dataset.df["hb"].isna())[0])
    cell = model.index(model.view_row(na_row), hb)
    assert model.data(cell) == "NA"
    assert model.data(cell, Qt.ItemDataRole.FontRole).italic()
    edad = model.data(model.index(0, model.column_index("edad")))
    assert edad == "5,1"  # coma decimal
    assert loaded.sidebar.cards["datos"].state.value == "done"


def test_click_and_drag_headers(loaded, qtbot):
    panel = loaded.data_panel
    table = panel.table
    _click_header(qtbot, table, "hb")
    assert panel.selected_columns() == ["hb"]
    assert panel.column_bar.isVisible() and not panel.row_bar.isVisible()

    # Arrastrar de hb a plaquetas selecciona las tres.
    vp = table.horizontalHeader().viewport()
    qtbot.mousePress(vp, Qt.MouseButton.LeftButton, pos=_col_pos(table, "hb"))
    qtbot.mouseMove(vp, _col_pos(table, "vcm"))
    qtbot.mouseMove(vp, _col_pos(table, "plaquetas"))
    qtbot.mouseRelease(vp, Qt.MouseButton.LeftButton, pos=_col_pos(table, "plaquetas"))
    assert panel.selected_columns() == ["hb", "vcm", "plaquetas"]

    # Mayús+clic: rango; Ctrl+clic: añade o quita.
    _click_header(qtbot, table, "hb")
    _click_header(qtbot, table, "hbf", Qt.KeyboardModifier.ShiftModifier)
    assert panel.selected_columns() == ["hb", "vcm", "plaquetas", "neutrofilos", "hbf"]
    _click_header(qtbot, table, "vcm", Qt.KeyboardModifier.ControlModifier)
    assert "vcm" not in panel.selected_columns()
    _click_header(qtbot, table, "ferritina", Qt.KeyboardModifier.ControlModifier)
    assert panel.selected_columns() == ["hb", "plaquetas", "neutrofilos", "hbf", "ferritina"]
    assert "5 columna" in panel.column_bar.count.text()


def test_shortcuts_and_bar(loaded, qtbot):
    panel = loaded.data_panel
    ds = loaded.session.dataset
    panel.table.setFocus()
    panel.select_columns(MODEL)
    qtbot.keyClick(panel.table, Qt.Key.Key_M)
    assert ds.con_rol(Rol.MODELO) == MODEL
    panel.select_columns(["ferritina"])
    qtbot.keyClick(panel.table, Qt.Key.Key_L)
    assert ds.log == {"ferritina"}
    panel.select_columns(["edad", "sexo", "tph"])
    qtbot.keyClick(panel.table, Qt.Key.Key_D)
    assert ds.con_rol(Rol.DESCRIPTIVA) == ["edad", "sexo", "tph"]
    panel.select_columns(["id"])
    qtbot.keyClick(panel.table, Qt.Key.Key_I)
    assert ds.identificador == "id"
    qtbot.keyClick(panel.table, Qt.Key.Key_Escape)
    assert panel.selected_columns() == [] and not panel.column_bar.isVisible()

    # Barra flotante: quitar rol.
    panel.select_columns(["tph"])
    qtbot.mouseClick(_bar_button(panel.column_bar, "Quitar rol"), Qt.MouseButton.LeftButton)
    assert "tph" not in ds.roles

    # Resumen del paso 2 en tiempo real.
    summary = loaded.sidebar.cards["variables"].content
    assert summary.model.label.text() == "Modelo (6)"
    assert summary.descr.label.text() == "Descriptivas (2)"
    assert "Identificador: id" in summary.facts.text()
    capture(loaded, "m1-roles")


def _bar_button(bar, text):
    from PySide6.QtWidgets import QPushButton

    return next(b for b in bar.findChildren(QPushButton) if b.text() == text)


def test_non_numeric_rejected_with_message(loaded, qtbot):
    panel = loaded.data_panel
    panel.select_columns(["sexo", "hb"])
    with qtbot.waitSignal(loaded.session.message) as blocker:
        panel.apply_role(Rol.MODELO)
    assert "«sexo» no es numérica" in blocker.args[0]
    assert panel.toast.isVisible()
    assert loaded.session.dataset.con_rol(Rol.MODELO) == ["hb"]


def test_right_click_menu_keeps_selection(loaded, qtbot):
    panel = loaded.data_panel
    panel.select_columns(["hb", "vcm"])
    header = panel.table.horizontalHeader()
    # Clic derecho sobre una columna ya seleccionada no deshace la selección múltiple.
    qtbot.mousePress(header.viewport(), Qt.MouseButton.RightButton, pos=_col_pos(panel.table, "vcm"))
    assert panel.selected_columns() == ["hb", "vcm"]

    menu = panel.build_header_menu(panel.model.column_index("vcm"))
    texts = [a.text() for a in menu.actions() if a.text()]
    assert texts[:5] == ["Usar en el modelo", "Variable descriptiva", "Identificador", "Aplicar log(1+x)", "Sin usar"]
    assert "Ver resumen y NA…" in texts
    next(a for a in menu.actions() if a.text() == "Variable descriptiva").trigger()
    assert loaded.session.dataset.con_rol(Rol.DESCRIPTIVA) == ["hb", "vcm"]

    # Sobre una columna no seleccionada, el menú actúa sobre esa columna.
    menu = panel.build_header_menu(panel.model.column_index("hbf"))
    assert panel.selected_columns() == ["hbf"]
    next(a for a in menu.actions() if a.text() == "Usar en el modelo").trigger()
    assert loaded.session.dataset.roles["hbf"] == Rol.MODELO


def test_row_selection_and_bar(loaded, qtbot, monkeypatch):
    panel = loaded.data_panel
    table = panel.table
    vp = table.verticalHeader().viewport()
    qtbot.mousePress(vp, Qt.MouseButton.LeftButton, pos=_row_pos(table, 2))
    qtbot.mouseMove(vp, _row_pos(table, 3))
    qtbot.mouseMove(vp, _row_pos(table, 5))
    qtbot.mouseRelease(vp, Qt.MouseButton.LeftButton, pos=_row_pos(table, 5))
    assert panel.selected_rows() == [2, 3, 4, 5]
    assert panel.row_bar.isVisible() and not panel.column_bar.isVisible()
    capture(loaded, "m1-filas")

    qtbot.mouseClick(_bar_button(panel.row_bar, "Excluir del análisis"), Qt.MouseButton.LeftButton)
    ds = loaded.session.dataset
    assert ds.excluidas == {2, 3, 4, 5}
    assert "236 de 240" in loaded.sidebar.cards["variables"].content.facts.text()
    assert loaded.sidebar.cards["variables"].content.all_rows.isVisible()

    panel.select_rows([0, 1])
    monkeypatch.setattr("statlab.ui.data_table.panel.QInputDialog.getText", lambda *a, **k: ("niños", True))
    qtbot.mouseClick(_bar_button(panel.row_bar, "Guardar como subgrupo…"), Qt.MouseButton.LeftButton)
    assert ds.subgrupos == {"niños": [0, 1]}
    qtbot.mouseClick(_bar_button(panel.row_bar, "Analizar solo estas"), Qt.MouseButton.LeftButton)
    assert ds.filas_activas().tolist() == [0, 1]
    qtbot.mouseClick(loaded.sidebar.cards["variables"].content.all_rows, Qt.MouseButton.LeftButton)
    assert not ds.filtro_filas_activo


def test_sort_keeps_row_identity(loaded):
    panel = loaded.data_panel
    model = panel.model
    hb = model.column_index("hb")
    model.sort(hb, Qt.SortOrder.DescendingOrder)
    df = loaded.session.dataset.df
    top = model.source_row(0)
    assert df["hb"].iloc[top] == df["hb"].max()
    assert model.headerData(0, Qt.Orientation.Vertical) == str(top + 1)
    assert model.data(model.index(model.rowCount() - 1, hb)) == "NA"  # NA al final
    panel.select_rows([top])
    assert panel.selected_rows() == [top]
    model.sort(-1)
    assert model.source_row(0) == 0


def test_bad_file_shows_human_error(window, tmp_path, monkeypatch):
    bad = tmp_path / "roto.xlsx"
    bad.write_bytes(b"esto no es un excel")
    shown = {}
    monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, text: shown.update(text=text))
    assert not window.load_path(str(bad))
    assert "No he podido leer «roto.xlsx»" in shown["text"]
    assert "Traceback" not in shown["text"]
    assert window.session.dataset is None


def test_large_table_is_fast(window, tmp_path, qtbot):
    rng = np.random.default_rng(0)
    df = pd.DataFrame(rng.normal(size=(5000, 50)).round(3), columns=[f"v{i}" for i in range(50)])
    df = df.mask(rng.random(df.shape) < 0.05)
    path = tmp_path / "grande.csv"
    df.to_csv(path, sep=";", decimal=",", index=False)
    t0 = time.perf_counter()
    assert window.load_path(str(path))
    load_s = time.perf_counter() - t0
    table = window.data_panel.table
    t0 = time.perf_counter()
    for step in range(20):
        table.verticalScrollBar().setValue(step * table.verticalScrollBar().maximum() // 19)
        table.viewport().repaint()
    scroll_s = time.perf_counter() - t0
    assert load_s < 5 and scroll_s < 3, (load_s, scroll_s)
