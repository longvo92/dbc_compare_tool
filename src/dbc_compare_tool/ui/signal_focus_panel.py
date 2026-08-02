"""Signal Focus tab: compare DBC baselines from an ECU node's point of view.

Workflow: pick both baseline folders, pair the DBC files, choose the ECU node
on each side of every pair, optionally paste the application's signal list,
then review the result and export it.

The result lives in its own resizable window rather than in the tab: a signal
list of any realistic size needs the whole screen, and squeezing it under the
setup controls left it one row tall.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QSettings, QThread, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from dbc_compare_tool.core.models import (
    SIGNAL_FOCUS_ATTENTION_STATUSES,
    NodeSelection,
    SignalFocusResult,
)
from dbc_compare_tool.core.signal_focus import (
    NodeSelectionInput,
    PairedDatabases,
    compare_signal_focus,
    pair_databases,
    parse_watchlist,
)
from dbc_compare_tool.report.signal_focus_excel import write_signal_focus_report
from dbc_compare_tool.ui.widgets import DropLineEdit, NoWheelComboBox

_SKIP_LABEL = "— none —"

# Same palette as the Excel report so screen and file tell the same story.
_STATUS_COLOR: dict[str, str] = {
    "Removed":           "#FFC7CE",
    "Modified":          "#FFF2CC",
    "Added":             "#E2EFDA",
    "Direction Changed": "#FCE4D6",
    "Out Of Node Scope": "#FCE4D6",
    "Ambiguous":         "#E4DFEC",
    "Not In DBC":        "#E4DFEC",
    "Moved":             "#F2F2F2",
}

_PAIR_STATUS_COLOR: dict[str, str] = {
    "Matched":     "#F2F2F2",
    "DBC Renamed": "#DDEBF7",
    "DBC Added":   "#E2EFDA",
    "DBC Removed": "#FCE4D6",
    "Parse Error": "#FFC7CE",
}

_RESULT_HEADERS = (
    "Signal",
    "Status",
    "In List",
    "Direction",
    "Changed Properties",
    "Carrier (Old)",
    "Carrier (New)",
    "Note",
)


class PairWorker(QThread):
    log = Signal(str)
    paired = Signal(object)
    failed = Signal(str)

    def __init__(self, old_folder: Path, new_folder: Path) -> None:
        super().__init__()
        self.old_folder = old_folder
        self.new_folder = new_folder

    def run(self) -> None:
        try:
            pairs = pair_databases(
                self.old_folder,
                self.new_folder,
                progress_callback=lambda msg: self.log.emit(msg),
            )
            self.paired.emit(pairs)
        except Exception as exc:
            self.failed.emit(str(exc))


class FocusWorker(QThread):
    compared = Signal(object)
    failed = Signal(str)

    def __init__(self, inputs: list[NodeSelectionInput], watchlist: list[str]) -> None:
        super().__init__()
        self.inputs = inputs
        self.watchlist = watchlist

    def run(self) -> None:
        try:
            self.compared.emit(compare_signal_focus(self.inputs, self.watchlist))
        except Exception as exc:
            self.failed.emit(str(exc))


class FocusExportWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, result: SignalFocusResult, output_path: Path) -> None:
        super().__init__()
        self.result = result
        self.output_path = output_path

    def run(self) -> None:
        try:
            write_signal_focus_report(self.result, self.output_path)
            self.completed.emit(self.output_path)
        except Exception as exc:
            self.failed.emit(str(exc))


class SignalFocusResultWindow(QDialog):
    """Comparison result in a window of its own, non-modal so the tab stays usable."""

    export_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Signal Focus Results")
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setSizeGripEnabled(True)
        self.resize(1180, 620)
        self._settings = QSettings("DbcCompareTool", "DBCCompareTool")
        self._result: SignalFocusResult | None = None

        self.summary_label = QLabel("No comparison has been run yet.")
        self.summary_label.setWordWrap(True)
        self.only_review_check = QCheckBox("Show only signals needing review")
        self.export_button = QPushButton("Export Excel")
        self.export_button.setObjectName("primaryButton")
        self.table = QTableWidget(0, len(_RESULT_HEADERS))

        self.table.setHorizontalHeaderLabels(list(_RESULT_HEADERS))
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setWordWrap(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        # Sorting on demand only. Qt's built-in sorting would re-order the rows
        # the moment it is enabled, and the default order has to stay the order
        # of the signal list the user handed in.
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        header.sectionClicked.connect(self._sort_by_column)
        self._sort_column = -1
        self._sort_order = Qt.SortOrder.AscendingOrder

        top_row = QHBoxLayout()
        top_row.addWidget(self.only_review_check)
        top_row.addStretch()
        top_row.addWidget(self.export_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        layout.addWidget(self.summary_label)
        layout.addLayout(top_row)
        layout.addWidget(self.table)

        self.only_review_check.toggled.connect(self._render)
        self.export_button.clicked.connect(self.export_requested)

        if geometry := self._settings.value("signal_focus_window_geometry"):
            self.restoreGeometry(geometry)

    def show_result(self, result: SignalFocusResult) -> None:
        self._result = result
        summary = result.summary()
        scope = (
            f"{summary['Total Signals']} signal(s) from the list"
            if result.watchlist_size
            else f"{summary['Total Signals']} signal(s) — full node audit"
        )
        nodes = ", ".join(
            f"{selection.dbc_file}: {selection.old_node or '—'} → {selection.new_node or '—'}"
            for selection in result.selections
        )
        self.summary_label.setText(
            f"{scope} · {summary['Needs Review']} need review — "
            f"Removed {summary['Removed']}, Modified {summary['Modified']}, "
            f"Added {summary['Added']}, Direction Changed {summary['Direction Changed']}, "
            f"Out Of Node Scope {summary['Out Of Node Scope']}, "
            f"Ambiguous {summary['Ambiguous']}, Not In DBC {summary['Not In DBC']}, "
            f"Moved {summary['Moved']}, Unchanged {summary['Unchanged']}\n{nodes}"
        )
        self.export_button.setEnabled(True)
        self._render()
        self.show()
        self.raise_()
        self.activateWindow()

    def _sort_by_column(self, column: int) -> None:
        if column == self._sort_column and self._sort_order == Qt.SortOrder.AscendingOrder:
            self._sort_order = Qt.SortOrder.DescendingOrder
        else:
            self._sort_order = Qt.SortOrder.AscendingOrder
        self._sort_column = column
        self.table.horizontalHeader().setSortIndicator(column, self._sort_order)
        self.table.sortItems(column, self._sort_order)

    def _render(self) -> None:
        rows = self._result.rows if self._result else []
        if self.only_review_check.isChecked():
            rows = [row for row in rows if row.status in SIGNAL_FOCUS_ATTENTION_STATUSES]

        self._sort_column = -1
        self.table.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        self.table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            changed = "; ".join(f"{prop}: {old} -> {new}" for prop, old, new in row.property_diffs)
            value_changes = "; ".join(
                f"Value {raw}: {old or '—'} -> {new or '—'} ({kind})"
                for raw, old, new, kind in row.value_table_diffs
            )
            cells = (
                row.signal_name,
                row.status,
                "Yes" if row.in_watchlist else "",
                f"{_direction(row.old_refs)} -> {_direction(row.new_refs)}",
                "; ".join(part for part in (changed, value_changes) if part),
                _carriers(row.old_refs),
                _carriers(row.new_refs),
                row.note.replace("\n", " · "),
            )
            color = _STATUS_COLOR.get(row.status)
            for column, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setToolTip(text or row.note)
                if color:
                    item.setBackground(QColor(color))
                self.table.setItem(index, column, item)
        self.table.resizeColumnsToContents()
        for column in range(self.table.columnCount()):
            if self.table.columnWidth(column) > 420:
                self.table.setColumnWidth(column, 420)

    def closeEvent(self, event) -> None:
        self._settings.setValue("signal_focus_window_geometry", self.saveGeometry())
        super().closeEvent(event)


class SignalFocusPanel(QWidget):
    """Node- and signal-centric comparison, independent of the baseline tab."""

    log = Signal(str)
    busy_changed = Signal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._settings = QSettings("DbcCompareTool", "DBCCompareTool")
        self._pairs: list[PairedDatabases] = []
        self._result: SignalFocusResult | None = None
        self._result_window: SignalFocusResultWindow | None = None
        self._pair_worker: PairWorker | None = None
        self._focus_worker: FocusWorker | None = None
        self._export_worker: FocusExportWorker | None = None

        self.old_input = DropLineEdit()
        self.new_input = DropLineEdit()
        self.pair_button = QPushButton("Load && Pair DBC")
        self.apply_node_button = QPushButton("Apply First Node To All")
        self.watchlist_edit = QPlainTextEdit()
        self.import_button = QPushButton("Import .txt…")
        self.clear_button = QPushButton("Clear")
        self.count_label = QLabel("0 signal(s) — full node audit")
        self.run_button = QPushButton("Run Signal Compare")
        self.show_result_button = QPushButton("Show Results")
        self.pair_table = QTableWidget(0, 4)

        self._build_layout()
        self._wire_events()
        self._restore_state()
        self._update_button_states()

    # -- layout ------------------------------------------------------------

    def _build_layout(self) -> None:
        folders = QGroupBox()
        grid = QGridLayout(folders)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(1, 1)

        grid.addWidget(QLabel("Old Baseline Folder"), 0, 0)
        grid.addWidget(self.old_input, 0, 1)
        old_browse = QPushButton("Browse")
        old_browse.clicked.connect(lambda: self._choose_folder(self.old_input))
        grid.addWidget(old_browse, 0, 2)

        grid.addWidget(QLabel("New Baseline Folder"), 1, 0)
        grid.addWidget(self.new_input, 1, 1)
        new_browse = QPushButton("Browse")
        new_browse.clicked.connect(lambda: self._choose_folder(self.new_input))
        grid.addWidget(new_browse, 1, 2)

        pair_row = QHBoxLayout()
        self.pair_button.setObjectName("primaryButton")
        self.pair_button.setToolTip(
            "Discover and pair the .dbc files of both folders, then load their ECU nodes."
        )
        pair_row.addWidget(self.pair_button)
        pair_row.addStretch()
        grid.addLayout(pair_row, 2, 1, 1, 2)

        nodes_group = QGroupBox("ECU Node Per DBC Pair")
        nodes_group.setToolTip(
            "Pick the node your application runs on. Signals the node sends or receives "
            "are compared; everything else is ignored."
        )
        nodes_layout = QVBoxLayout(nodes_group)

        self.pair_table.setHorizontalHeaderLabels(["DBC File", "Pairing", "Old Node", "New Node"])
        self.pair_table.verticalHeader().setVisible(False)
        self.pair_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.pair_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.pair_table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        header = self.pair_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._resize_pair_table()
        nodes_layout.addWidget(self.pair_table)

        self.apply_node_button.setToolTip(
            "Copy the node selected in the first row to every other pair that offers the same node name."
        )
        apply_row = QHBoxLayout()
        apply_row.addWidget(self.apply_node_button)
        apply_row.addStretch()
        nodes_layout.addLayout(apply_row)

        signals_group = QGroupBox("Application Signal List")
        signals_group.setToolTip(
            "Paste one signal name per line, or import a .txt file. Comment lines (#, //) "
            "and extra columns are ignored. Leave empty to audit every signal of the node."
        )
        signals_layout = QVBoxLayout(signals_group)

        self.watchlist_edit.setPlaceholderText("VehicleSpeed\nIgnitionState\nBatterySoc")
        self.watchlist_edit.setMinimumHeight(84)
        signals_layout.addWidget(self.watchlist_edit)

        signal_buttons = QHBoxLayout()
        signal_buttons.addWidget(self.import_button)
        signal_buttons.addWidget(self.clear_button)
        self.count_label.setObjectName("hintLabel")
        signal_buttons.addWidget(self.count_label)
        signal_buttons.addStretch()
        signals_layout.addLayout(signal_buttons)

        actions = QHBoxLayout()
        self.run_button.setObjectName("primaryButton")
        self.run_button.setToolTip("Compare the selected nodes and open the result window.")
        self.show_result_button.setToolTip("Bring the result window back to the front.")
        actions.addWidget(self.run_button)
        actions.addWidget(self.show_result_button)
        actions.addStretch()

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)
        content_layout.addWidget(folders)
        content_layout.addWidget(nodes_group)
        content_layout.addWidget(signals_group)
        content_layout.addStretch()

        # A scroll area instead of a splitter: when the window gets small the
        # groups keep their natural size and the panel scrolls, rather than
        # every group being squeezed until its content is unreadable.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.viewport().setAutoFillBackground(False)
        content.setAutoFillBackground(False)
        scroll.setWidget(content)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(scroll)
        # Outside the scroll area: Run must stay reachable however small the window.
        layout.addLayout(actions)

    def _wire_events(self) -> None:
        self.pair_button.clicked.connect(self._load_pairs)
        self.apply_node_button.clicked.connect(self._apply_first_node_to_all)
        self.import_button.clicked.connect(self._import_watchlist)
        self.clear_button.clicked.connect(self.watchlist_edit.clear)
        self.watchlist_edit.textChanged.connect(self._update_watchlist_count)
        self.run_button.clicked.connect(self._run_compare)
        self.show_result_button.clicked.connect(self._show_result_window)
        self.old_input.textChanged.connect(self._invalidate_pairs)
        self.new_input.textChanged.connect(self._invalidate_pairs)

    # -- public API used by the main window --------------------------------

    def prefill_folders(self, old_folder: str, new_folder: str) -> None:
        """Adopt the baseline tab's folders while this tab is still untouched."""
        if not self.old_input.text().strip() and old_folder:
            self.old_input.setText(old_folder)
        if not self.new_input.text().strip() and new_folder:
            self.new_input.setText(new_folder)

    def running_workers(self) -> list[QThread]:
        workers = (self._pair_worker, self._focus_worker, self._export_worker)
        return [worker for worker in workers if worker and worker.isRunning()]

    def save_state(self) -> None:
        self._settings.setValue("signal_focus_old_folder", self.old_input.text())
        self._settings.setValue("signal_focus_new_folder", self.new_input.text())
        self._settings.setValue("signal_focus_watchlist", self.watchlist_edit.toPlainText())
        if self._result_window is not None:
            self._result_window.close()

    # -- pairing -----------------------------------------------------------

    def _choose_folder(self, target) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Baseline Folder")
        if folder:
            target.setText(folder)

    def _invalidate_pairs(self) -> None:
        if self._pairs:
            self._pairs = []
            self.pair_table.setRowCount(0)
            self._update_button_states()
            self.log.emit("Baseline folder changed — reload the DBC pairs.")

    def _load_pairs(self) -> None:
        old_text = self.old_input.text().strip()
        new_text = self.new_input.text().strip()
        # Guard empty text explicitly: Path("") is ".", which is_dir() accepts.
        if not old_text or not new_text or not Path(old_text).is_dir() or not Path(new_text).is_dir():
            QMessageBox.warning(self, "Invalid Input", "Select valid old and new baseline folders.")
            return

        self._set_busy(True)
        self.log.emit("Pairing DBC files and loading ECU nodes...")
        self._pair_worker = PairWorker(Path(old_text), Path(new_text))
        self._pair_worker.log.connect(self.log)
        self._pair_worker.paired.connect(self._on_paired)
        self._pair_worker.failed.connect(self._on_failed)
        self._pair_worker.start()

    def _on_paired(self, pairs: list[PairedDatabases]) -> None:
        self._set_busy(False)
        self._pairs = pairs
        self._fill_pair_table()
        usable = sum(1 for pair in pairs if pair.status != "Parse Error")
        self.log.emit(f"Loaded {usable} DBC pair(s). Select the ECU node for each pair.")
        self._update_button_states()

    def _fill_pair_table(self) -> None:
        self.pair_table.setRowCount(len(self._pairs))
        for row, pair in enumerate(self._pairs):
            file_item = QTableWidgetItem(pair.dbc_file)
            file_item.setToolTip(f"Old: {pair.old_path or '—'}\nNew: {pair.new_path or '—'}")
            status_item = QTableWidgetItem(pair.status)
            color = _PAIR_STATUS_COLOR.get(pair.status)
            if color:
                file_item.setBackground(QColor(color))
                status_item.setBackground(QColor(color))
            self.pair_table.setItem(row, 0, file_item)
            self.pair_table.setItem(row, 1, status_item)
            self.pair_table.setCellWidget(row, 2, self._node_combo(pair.old_db))
            self.pair_table.setCellWidget(row, 3, self._node_combo(pair.new_db))
            self._preselect_common_node(row, pair)
        self._resize_pair_table()

    def _resize_pair_table(self) -> None:
        """Keep the table as tall as its rows, so it never leaves a blank block.

        Both bounds are set: the table's size policy is Expanding, so a minimum
        alone would still let it stretch to fill the group.
        """
        header = self.pair_table.horizontalHeader().height()
        rows = sum(self.pair_table.rowHeight(row) for row in range(self.pair_table.rowCount()))
        height = min(max(header + rows + 8, 76), 240)
        self.pair_table.setMinimumHeight(height)
        self.pair_table.setMaximumHeight(height)

    def _node_combo(self, database) -> NoWheelComboBox:
        combo = NoWheelComboBox()
        combo.addItem(_SKIP_LABEL, "")
        for node in (database.nodes if database is not None else ()):
            combo.addItem(node, node)
        combo.setEnabled(combo.count() > 1)
        return combo

    def _preselect_common_node(self, row: int, pair: PairedDatabases) -> None:
        """Pick the node already used elsewhere, so one choice covers every pair."""
        chosen = self._first_selected_node()
        if not chosen:
            return
        for column, database in ((2, pair.old_db), (3, pair.new_db)):
            if database is not None and chosen in database.nodes:
                combo = self.pair_table.cellWidget(row, column)
                combo.setCurrentIndex(combo.findData(chosen))

    def _first_selected_node(self) -> str:
        for row in range(self.pair_table.rowCount()):
            for column in (3, 2):
                combo = self.pair_table.cellWidget(row, column)
                if combo and combo.currentData():
                    return str(combo.currentData())
        return ""

    def _apply_first_node_to_all(self) -> None:
        chosen = self._first_selected_node()
        if not chosen:
            QMessageBox.information(
                self,
                "No Node Selected",
                "Select the ECU node in the first row, then apply it to the other pairs.",
            )
            return
        applied = 0
        for row in range(self.pair_table.rowCount()):
            for column in (2, 3):
                combo = self.pair_table.cellWidget(row, column)
                index = combo.findData(chosen) if combo else -1
                if index >= 0 and combo.currentIndex() != index:
                    combo.setCurrentIndex(index)
                    applied += 1
        self.log.emit(f"Node '{chosen}' applied to {applied} more selection(s).")

    # -- watchlist ---------------------------------------------------------

    def _import_watchlist(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Signal List", "", "Text files (*.txt *.csv);;All files (*)"
        )
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            QMessageBox.critical(self, "Import Failed", f"Unable to read the signal list: {exc}")
            return
        self.watchlist_edit.setPlainText(text)
        self._settings.setValue("signal_focus_watchlist_path", path)
        self.log.emit(f"Signal list imported: {path}")

    def _watchlist(self) -> list[str]:
        return parse_watchlist(self.watchlist_edit.toPlainText())

    def _update_watchlist_count(self) -> None:
        count = len(self._watchlist())
        self.count_label.setText(
            f"{count} signal(s)" if count else "0 signal(s) — full node audit"
        )

    # -- comparison --------------------------------------------------------

    def _selected_inputs(self) -> list[NodeSelectionInput]:
        inputs: list[NodeSelectionInput] = []
        for row, pair in enumerate(self._pairs):
            old_combo = self.pair_table.cellWidget(row, 2)
            new_combo = self.pair_table.cellWidget(row, 3)
            old_node = str(old_combo.currentData() or "") if old_combo else ""
            new_node = str(new_combo.currentData() or "") if new_combo else ""
            if not old_node and not new_node:
                continue
            inputs.append(NodeSelectionInput(
                selection=NodeSelection(
                    dbc_file=pair.dbc_file,
                    old_path=pair.old_path,
                    new_path=pair.new_path,
                    old_node=old_node,
                    new_node=new_node,
                ),
                old_db=pair.old_db,
                new_db=pair.new_db,
            ))
        return inputs

    def _run_compare(self) -> None:
        inputs = self._selected_inputs()
        if not inputs:
            QMessageBox.warning(
                self,
                "No Node Selected",
                "Select the ECU node for at least one DBC pair before comparing.",
            )
            return

        watchlist = self._watchlist()
        scope = f"{len(watchlist)} signal(s) from the list" if watchlist else "every node signal"
        self.log.emit(f"Comparing {scope} across {len(inputs)} DBC pair(s)...")
        self._set_busy(True)
        self._focus_worker = FocusWorker(inputs, watchlist)
        self._focus_worker.compared.connect(self._on_compared)
        self._focus_worker.failed.connect(self._on_failed)
        self._focus_worker.start()

    def _on_compared(self, result: SignalFocusResult) -> None:
        self._set_busy(False)
        self._result = result
        summary = result.summary()
        self.log.emit(
            f"Signal focus: {summary['Total Signals']} signal(s), "
            f"{summary['Needs Review']} need review "
            f"(Removed {summary['Removed']}, Modified {summary['Modified']}, "
            f"Out Of Node Scope {summary['Out Of Node Scope']}, "
            f"Not In DBC {summary['Not In DBC']})."
        )
        self._update_button_states()
        self._show_result_window()

    def _show_result_window(self) -> None:
        if self._result is None:
            return
        if self._result_window is None:
            self._result_window = SignalFocusResultWindow(self.window())
            self._result_window.export_requested.connect(self._export)
        self._result_window.show_result(self._result)

    # -- export ------------------------------------------------------------

    def _export(self) -> None:
        if self._result is None:
            return
        default = self._settings.value("signal_focus_report_path") or str(
            Path.cwd() / "signal_focus_report.xlsx"
        )
        parent = self._result_window or self
        path, _ = QFileDialog.getSaveFileName(
            parent, "Save Signal Focus Report", str(default), "Excel (*.xlsx)"
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        self._settings.setValue("signal_focus_report_path", path)

        self._set_busy(True)
        self.log.emit("Writing signal focus report...")
        self._export_worker = FocusExportWorker(self._result, Path(path))
        self._export_worker.completed.connect(self._on_exported)
        self._export_worker.failed.connect(self._on_failed)
        self._export_worker.start()

    def _on_exported(self, path: Path) -> None:
        self._set_busy(False)
        self.log.emit(f"Signal focus report generated: {path}")
        self._update_button_states()

    # -- shared ------------------------------------------------------------

    def _on_failed(self, message: str) -> None:
        self._set_busy(False)
        self.log.emit(f"Failed: {message}")
        self._update_button_states()
        QMessageBox.critical(self, "Signal Focus Failed", message)

    def _set_busy(self, busy: bool) -> None:
        for button in (self.pair_button, self.run_button):
            button.setEnabled(not busy)
        if self._result_window is not None:
            self._result_window.export_button.setEnabled(not busy)
        self.busy_changed.emit(busy)
        if not busy:
            self._update_button_states()

    def _update_button_states(self) -> None:
        has_pairs = bool(self._pairs)
        self.run_button.setEnabled(has_pairs)
        self.apply_node_button.setEnabled(has_pairs)
        self.show_result_button.setEnabled(self._result is not None)

    def _restore_state(self) -> None:
        if value := self._settings.value("signal_focus_old_folder"):
            self.old_input.setText(str(value))
        if value := self._settings.value("signal_focus_new_folder"):
            self.new_input.setText(str(value))
        if value := self._settings.value("signal_focus_watchlist"):
            self.watchlist_edit.setPlainText(str(value))
        self._update_watchlist_count()


def _direction(refs) -> str:
    if not refs:
        return "—"
    directions = {ref.direction for ref in refs}
    if directions == {"Tx"}:
        return "Tx"
    if directions == {"Rx"}:
        return "Rx"
    return "Tx/Rx"


def _carriers(refs) -> str:
    seen: list[str] = []
    for ref in refs:
        label = f"{ref.message_name} (0x{ref.can_id:X})"
        if label not in seen:
            seen.append(label)
    return ", ".join(seen) or "—"
