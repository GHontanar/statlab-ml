"""Panel de datos: tabla con roles por columna, selección de filas y barras flotantes.

Gestos:
- clic en una cabecera o número de fila → selecciona la columna o fila;
- arrastrar por cabeceras / números de fila → varias; Mayús+clic rango; Ctrl/⌘+clic añade o quita;
- clic derecho en una cabecera → menú de rol;
- atajos M D I L (modelo, descriptiva, identificador, log) y Esc (limpiar selección).
"""
from __future__ import annotations

from PySide6.QtCore import QItemSelection, QItemSelectionModel, QPoint, Qt, QTimer
from PySide6.QtGui import QFontMetrics, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from statlab import strings_es as S
from statlab.core.dataset import Rol, column_summary
from statlab.ui import clusters as cl
from statlab.ui import theme
from statlab.ui.data_table.delegates import ClusterDelegate
from statlab.ui.data_table.float_bars import ColumnBar, RowBar
from statlab.ui.data_table.headers import PAD_X, RoleHeader, RowHeader
from statlab.ui.data_table.model import DataFrameModel
from statlab.ui.session import SessionController

MAX_COL_WIDTH = 260
WIDTH_SAMPLE = 400
TOAST_MS = 7000


class DataTableView(QTableView):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("DataTable")
        self.setHorizontalHeader(RoleHeader(self))
        self.setVerticalHeader(RowHeader(self))
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setWordWrap(False)
        self.setCornerButtonEnabled(False)
        self.setFont(theme.tabular_font())

    def fit_columns(self) -> None:
        """Ancho por columna a partir de la cabecera y una muestra de filas (rápido con 5.000)."""
        model: DataFrameModel = self.model()
        fm = QFontMetrics(self.font())
        header: RoleHeader = self.horizontalHeader()
        rows = min(model.rowCount(), WIDTH_SAMPLE)
        for col in range(model.columnCount()):
            texts = [model.cell_text(r, col) for r in range(rows)] + ["NA"]
            cells = max(fm.horizontalAdvance(t) for t in texts) + 2 * PAD_X
            self.setColumnWidth(col, min(max(cells, header.width_for(col)), MAX_COL_WIDTH))


class Toast(QLabel):
    """Aviso breve sobre la tabla; se cierra solo o con un clic."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setWordWrap(True)
        self.setMaximumWidth(560)
        self._timer = QTimer(self, singleShot=True, interval=TOAST_MS)
        self._timer.timeout.connect(self.hide)
        self.hide()

    def show_message(self, text: str) -> None:
        self.setText(text)
        self.adjustSize()
        self.show()
        self.raise_()
        self._timer.start()

    def mousePressEvent(self, event) -> None:
        self.hide()


class ColumnSummaryDialog(QDialog):
    def __init__(self, title: str, rows: list[tuple[str, str]], parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(6)
        for i, (label, value) in enumerate(rows):
            name = QLabel(label)
            name.setObjectName("Muted")
            val = QLabel(value)
            val.setFont(theme.tabular_font())
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            grid.addWidget(name, i, 0)
            grid.addWidget(val, i, 1)
        layout.addLayout(grid)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText(S.CLOSE)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class DataPanel(QFrame):
    def __init__(self, session: SessionController, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Panel")
        self.session = session
        self.model: DataFrameModel | None = None

        self.title = QLabel()
        self.title.setObjectName("DataTitle")
        self.na_label = QLabel()
        self.na_label.setObjectName("NaBadge")
        top = QHBoxLayout()
        top.setContentsMargins(16, 10, 16, 10)
        top.setSpacing(12)
        top.addWidget(self.title)
        top.addWidget(self.na_label)
        top.addStretch(1)
        self.highlight_bar = QWidget()
        self.highlight_row = QHBoxLayout(self.highlight_bar)
        self.highlight_row.setContentsMargins(0, 0, 0, 0)
        self.highlight_row.setSpacing(4)
        self.highlight_buttons: list[QPushButton] = []
        self.highlight_bar.hide()
        top.addWidget(self.highlight_bar)

        self.table = DataTableView()
        self._cluster_delegate = ClusterDelegate(self.table)
        self._results_key = None
        col = QVBoxLayout(self)
        col.setContentsMargins(1, 0, 1, 1)
        col.setSpacing(0)
        col.addLayout(top)
        col.addWidget(self.table, 1)

        self.column_bar = ColumnBar(self)
        self.row_bar = RowBar(self)
        self.toast = Toast(self)

        self.column_bar.model_clicked.connect(lambda: self.apply_role(Rol.MODELO))
        self.column_bar.descr_clicked.connect(lambda: self.apply_role(Rol.DESCRIPTIVA))
        self.column_bar.log_clicked.connect(self.toggle_log)
        self.column_bar.clear_clicked.connect(lambda: self.apply_role(None))
        self.row_bar.only_clicked.connect(lambda: self.session.analyze_only(self.selected_rows()))
        self.row_bar.exclude_clicked.connect(self._exclude_selected)
        self.row_bar.subgroup_clicked.connect(self._save_subgroup)
        self.row_bar.clear_clicked.connect(self.clear_selection)

        header = self.table.horizontalHeader()
        header.customContextMenuRequested.connect(self._header_menu)

        for key, slot in (
            ("M", lambda: self.apply_role(Rol.MODELO)),
            ("D", lambda: self.apply_role(Rol.DESCRIPTIVA)),
            ("I", lambda: self.apply_role(Rol.IDENTIFICADOR)),
            ("L", self.toggle_log),
            ("Esc", self.clear_selection),
        ):
            shortcut = QShortcut(QKeySequence(key), self.table)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(slot)

        session.dataset_changed.connect(self._on_dataset)
        session.roles_changed.connect(self._on_roles)
        session.rows_changed.connect(self._on_rows)
        session.message.connect(self.show_message)
        session.step_updated.connect(lambda p: p == "modelo_final" and self._sync_results())
        session.flow_changed.connect(self._sync_results)
        session.rows_selection_requested.connect(self.select_and_show_rows)

    # --- Datos -----------------------------------------------------------
    def _on_dataset(self) -> None:
        ds = self.session.dataset
        old = self.model
        self.model = DataFrameModel(ds, self)
        self.table.setModel(self.model)
        if old is not None:
            old.deleteLater()
        self.table.selectionModel().selectionChanged.connect(self._update_bars)
        self.table.fit_columns()
        self._results_key = None
        self._build_highlight_bar(0)
        self.title.setText(S.DATA_SUMMARY.format(name=ds.fuente, rows=ds.n_filas, cols=len(ds.columnas)))
        na = self.model.na_count()
        self.na_label.setText(S.DATA_NA.format(n=na))
        self.na_label.setVisible(na > 0)
        self._update_bars()

    # --- Resultados del modelo final ------------------------------------
    def _sync_results(self) -> None:
        """Añade (o quita) las columnas cluster y silueta según el resultado del modelo final."""
        if self.model is None:
            return
        r = self.session.estado.resultados.get("modelo_final")
        key = id(r) if r and "error" not in r else None
        if key == self._results_key:
            return
        self._results_key = key
        if key is None:
            self.model.clear_results()
            self.table.setItemDelegateForColumn(0, None)
            self._build_highlight_bar(0)
        else:
            self.model.set_results(r["filas"], r["etiquetas"], r["silueta_obs"])
            self.table.setItemDelegateForColumn(0, self._cluster_delegate)
            self._build_highlight_bar(r["k"])
        self.table.fit_columns()

    def _build_highlight_bar(self, k: int) -> None:
        while self.highlight_row.count():
            item = self.highlight_row.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        self.highlight_buttons = []
        self.highlight_bar.setVisible(k > 0)
        if k == 0:
            return
        label = QLabel(S.HIGHLIGHT)
        label.setObjectName("FieldLabel")
        self.highlight_row.addWidget(label)
        for c in [*range(k), None]:
            text = f"{cl.glyph(c)} {cl.name(c)}" if c is not None else S.HIGHLIGHT_ALL
            button = QPushButton(text)
            button.setObjectName("HighlightButton")
            button.setCheckable(True)
            button.setChecked(c is None)
            button.clicked.connect(lambda _=False, c=c: self.set_highlight(c))
            self.highlight_row.addWidget(button)
            self.highlight_buttons.append(button)

    def set_highlight(self, cluster: int | None) -> None:
        self.model.set_highlight(cluster)
        last = len(self.highlight_buttons) - 1
        for i, b in enumerate(self.highlight_buttons):
            b.setChecked(i == (last if cluster is None else cluster))

    def select_and_show_rows(self, rows: list[int]) -> None:
        """Selección hecha desde un gráfico (clic o lazo en el PCA)."""
        if self.model is None or not rows:
            return
        self.select_rows(rows)
        first = min(self.model.view_row(r) for r in rows)
        self.table.scrollTo(self.model.index(first, 0))

    def show_message(self, text: str) -> None:
        self.toast.show_message(text)
        self._place_overlays()

    def _on_roles(self) -> None:
        self.model.roles_changed()

    def _on_rows(self) -> None:
        self.model.rows_changed()
        self.table.verticalHeader().viewport().update()

    def refresh_theme(self) -> None:
        self.table.viewport().update()
        self.table.horizontalHeader().viewport().update()
        self.table.verticalHeader().viewport().update()

    # --- Selección -------------------------------------------------------
    def selected_columns(self) -> list[str]:
        if self.model is None:
            return []
        cols = sorted(i.column() for i in self.table.selectionModel().selectedColumns())
        # Las columnas de resultado (cluster, silueta) no tienen rol
        return [self.model.column_name(c) for c in cols if not self.model.is_result_column(c)]

    def selected_rows(self) -> list[int]:
        if self.model is None:
            return []
        return sorted(self.model.source_row(i.row()) for i in self.table.selectionModel().selectedRows())

    def select_columns(self, names: list[str]) -> None:
        """Selecciona columnas completas por nombre."""
        last = self.model.rowCount() - 1
        selection = QItemSelection()
        for name in names:
            c = self.model.column_index(name)
            selection.select(self.model.index(0, c), self.model.index(last, c))
        self.table.selectionModel().select(selection, QItemSelectionModel.SelectionFlag.ClearAndSelect)

    def select_rows(self, source_rows: list[int]) -> None:
        """Selecciona filas completas por su posición original."""
        last = self.model.columnCount() - 1
        selection = QItemSelection()
        for src in source_rows:
            r = self.model.view_row(src)
            selection.select(self.model.index(r, 0), self.model.index(r, last))
        self.table.selectionModel().select(selection, QItemSelectionModel.SelectionFlag.ClearAndSelect)

    def clear_selection(self) -> None:
        self.table.clearSelection()

    def _update_bars(self, *_args) -> None:
        cols = self.selected_columns()
        rows = self.selected_rows()
        show_cols = bool(cols) and not rows
        show_rows = bool(rows) and not cols
        if show_cols:
            self.column_bar.set_count(len(cols))
        if show_rows:
            self.row_bar.set_count(len(rows))
        self.column_bar.setVisible(show_cols)
        self.row_bar.setVisible(show_rows)
        self._place_overlays()
        self.table.horizontalHeader().viewport().update()
        self.table.verticalHeader().viewport().update()

    # --- Acciones --------------------------------------------------------
    def apply_role(self, rol: Rol | None) -> None:
        cols = self.selected_columns()
        if cols:
            self.session.set_role(cols, rol)

    def toggle_log(self) -> None:
        cols = self.selected_columns()
        if cols:
            self.session.toggle_log(cols)

    def _exclude_selected(self) -> None:
        self.session.exclude(self.selected_rows())
        self.clear_selection()

    def _save_subgroup(self) -> None:
        rows = self.selected_rows()
        name, ok = QInputDialog.getText(self, S.SUBGROUP_TITLE, S.SUBGROUP_PROMPT.format(n=len(rows)))
        if ok and name.strip():
            self.session.save_subgroup(name, rows)

    def show_summary(self, col: str) -> None:
        rows = column_summary(self.session.dataset.df[col])
        ColumnSummaryDialog(S.SUM_TITLE.format(col=col), rows, self).exec()

    def _header_menu(self, pos: QPoint) -> None:
        header = self.table.horizontalHeader()
        logical = header.logicalIndexAt(pos)
        if logical < 0 or self.model is None:
            return
        self.build_header_menu(logical).exec(header.mapToGlobal(pos))

    def build_header_menu(self, logical: int) -> QMenu:
        """Menú de rol de una columna (selecciona la columna si no lo estaba)."""
        if self.model.is_result_column(logical):
            menu = QMenu(self)
            menu.addAction(S.SORT_ASC, lambda: self._sort(logical, Qt.SortOrder.AscendingOrder))
            menu.addAction(S.SORT_DESC, lambda: self._sort(logical, Qt.SortOrder.DescendingOrder))
            menu.addAction(S.SORT_CLEAR, lambda: self._sort(-1, Qt.SortOrder.AscendingOrder))
            return menu
        name = self.model.column_name(logical)
        if name not in self.selected_columns():
            self.table.selectColumn(logical)
        ds = self.session.dataset
        menu = QMenu(self)
        for text, rol in (
            (S.ROLE_USE_MODEL, Rol.MODELO),
            (S.ROLE_USE_DESCR, Rol.DESCRIPTIVA),
            (S.ROLE_USE_ID, Rol.IDENTIFICADOR),
        ):
            action = menu.addAction(text, lambda r=rol: self.apply_role(r))
            action.setCheckable(True)
            action.setChecked(ds.roles.get(name) == rol)
        log = menu.addAction(S.ROLE_TOGGLE_LOG, self.toggle_log)
        log.setCheckable(True)
        log.setChecked(name in ds.log)
        none = menu.addAction(S.ROLE_CLEAR, lambda: self.apply_role(None))
        none.setCheckable(True)
        none.setChecked(name not in ds.roles)
        menu.addSeparator()
        menu.addAction(S.ROLE_SUMMARY, lambda: self.show_summary(name))
        menu.addSeparator()
        menu.addAction(S.SORT_ASC, lambda: self._sort(logical, Qt.SortOrder.AscendingOrder))
        menu.addAction(S.SORT_DESC, lambda: self._sort(logical, Qt.SortOrder.DescendingOrder))
        menu.addAction(S.SORT_CLEAR, lambda: self._sort(-1, Qt.SortOrder.AscendingOrder))
        return menu

    def _sort(self, col: int, order: Qt.SortOrder) -> None:
        self.table.clearSelection()
        self.model.sort(col, order)
        self.table.horizontalHeader().viewport().update()

    # --- Superposiciones -------------------------------------------------
    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._place_overlays()

    def _place_overlays(self) -> None:
        table = self.table.geometry()
        cx = table.center().x()
        bar = self.column_bar
        if bar.isVisible():
            bar.adjustSize()
            bar.move(cx - bar.width() // 2, table.top() + RoleHeader.HEIGHT + 12)
            bar.raise_()
        bar = self.row_bar
        if bar.isVisible():
            bar.adjustSize()
            bar.move(cx - bar.width() // 2, table.bottom() - bar.height() - 16)
            bar.raise_()
        if self.toast.isVisible():
            self.toast.move(cx - self.toast.width() // 2, table.top() + RoleHeader.HEIGHT + 64)
