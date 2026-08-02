from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QSettings, QThread, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from dbc_compare_tool import __version__
from dbc_compare_tool.core.comparator import DbcComparator, filter_result, reject_signal_renames
from dbc_compare_tool.core.discovery import collect_dbc_files
from dbc_compare_tool.core.models import Change, ComparisonResult
from dbc_compare_tool.report.excel import write_excel_report
from dbc_compare_tool.ui.signal_focus_panel import SignalFocusPanel
from dbc_compare_tool.ui.widgets import DropLineEdit, NoWheelComboBox


def _resource_path(filename: str) -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "resources" / filename
    return Path(__file__).resolve().parents[3] / "resources" / filename


_STYLESHEET = """
QMainWindow, QDialog {
    background-color: #f4f6fb;
}
QWidget {
    font-family: 'Segoe UI', sans-serif;
    font-size: 10pt;
    color: #1f2430;
}
QLabel#appTitle {
    font-size: 17pt;
    font-weight: 700;
    color: #16213a;
}
QLabel#appSubtitle {
    color: #6b7280;
    font-size: 9pt;
}
QLabel#versionBadge {
    color: #2563eb;
    background: #e3ecfd;
    border-radius: 9px;
    padding: 2px 10px;
    font-size: 8pt;
    font-weight: 600;
}
QLabel#sectionLabel {
    color: #6b7280;
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 1px;
}
QLineEdit {
    background: #ffffff;
    border: 1px solid #d4d9e4;
    border-radius: 6px;
    padding: 7px 10px;
    selection-background-color: #bfd3f8;
}
QLineEdit:focus {
    border: 1px solid #2563eb;
}
QPushButton {
    background: #ffffff;
    border: 1px solid #d4d9e4;
    border-radius: 6px;
    padding: 7px 16px;
}
QPushButton:hover { background: #eef2fb; }
QPushButton:pressed { background: #e0e7f7; }
QPushButton:disabled { color: #9aa2b1; background: #f0f1f5; }
QPushButton#primaryButton {
    background: #2563eb;
    border: none;
    color: #ffffff;
    font-weight: 600;
    padding: 8px 22px;
}
QPushButton#primaryButton:hover { background: #1d4fd7; }
QPushButton#primaryButton:pressed { background: #1a46bd; }
QPushButton#primaryButton:disabled { background: #a5bdf2; color: #eef2fb; }
QGroupBox {
    background: #ffffff;
    border: 1px solid #e1e5ee;
    border-radius: 8px;
    margin-top: 10px;
    padding: 10px 12px 6px 12px;
    font-weight: 600;
    color: #4b5563;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
}
QCheckBox {
    spacing: 6px;
    font-weight: 400;
}
QProgressBar {
    background: #e5e9f2;
    border: none;
    border-radius: 4px;
    max-height: 8px;
    text-align: center;
}
QProgressBar::chunk {
    background: #2563eb;
    border-radius: 4px;
}
QTextEdit#logView {
    background: #1e2430;
    color: #d6e2f3;
    border: none;
    border-radius: 8px;
    font-family: 'Cascadia Mono', 'Consolas', monospace;
    font-size: 9pt;
    padding: 6px;
}
QTextBrowser {
    background: #ffffff;
    border: 1px solid #e1e5ee;
    border-radius: 8px;
    padding: 10px;
}
QMenuBar {
    background: #f4f6fb;
}
QMenuBar::item {
    padding: 6px 10px;
    border-radius: 4px;
}
QMenuBar::item:selected { background: #e3ecfd; }
QMenu {
    background: #ffffff;
    border: 1px solid #d4d9e4;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item {
    padding: 6px 24px;
    border-radius: 4px;
}
QMenu::item:selected { background: #e3ecfd; }
QStatusBar {
    background: #eef1f8;
    color: #4b5563;
}
QSplitter::handle { background: transparent; }
QTableWidget {
    background: #ffffff;
    border: 1px solid #e1e5ee;
    border-radius: 6px;
    gridline-color: #edf0f7;
}
QHeaderView::section {
    background: #eef2fb;
    border: none;
    border-bottom: 1px solid #d4d9e4;
    padding: 6px 8px;
    font-weight: 600;
    color: #4b5563;
}
QComboBox {
    background: #ffffff;
    border: 1px solid #d4d9e4;
    border-radius: 6px;
    padding: 4px 8px;
}
QComboBox:focus { border: 1px solid #2563eb; }
QComboBox QAbstractItemView {
    background: #ffffff;
    border: 1px solid #d4d9e4;
    selection-background-color: #e3ecfd;
    selection-color: #1f2430;
}
QLabel#hintLabel {
    color: #6b7280;
    font-size: 9pt;
}
QTabWidget::pane {
    border: 1px solid #e1e5ee;
    border-radius: 8px;
    background: #f8f9fc;
    top: -1px;
}
QTabBar::tab {
    background: #e8ecf6;
    border: 1px solid #e1e5ee;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 7px 18px;
    margin-right: 2px;
    color: #4b5563;
}
QTabBar::tab:selected {
    background: #f8f9fc;
    color: #16213a;
    font-weight: 600;
}
QTabBar::tab:hover:!selected { background: #eef2fb; }
QPlainTextEdit {
    background: #ffffff;
    border: 1px solid #d4d9e4;
    border-radius: 6px;
    padding: 6px 8px;
    font-family: 'Cascadia Mono', 'Consolas', monospace;
    font-size: 9pt;
}
QPlainTextEdit:focus { border: 1px solid #2563eb; }
QScrollArea {
    background: transparent;
    border: none;
}
"""


def _read_resource_text(filename: str) -> str:
    return _resource_path(filename).read_text(encoding="utf-8")


def _scrollable(content: QWidget) -> QScrollArea:
    """Wrap a tab's content so a small window scrolls instead of crushing it."""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    scroll.viewport().setAutoFillBackground(False)
    content.setAutoFillBackground(False)
    scroll.setWidget(content)
    return scroll


class CompareWorker(QThread):
    log = Signal(str)
    compared = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        old_folder: Path,
        new_folder: Path,
        pair_map: dict[str, str | None] | None = None,
    ) -> None:
        super().__init__()
        self.old_folder = old_folder
        self.new_folder = new_folder
        self.pair_map = pair_map

    def run(self) -> None:
        try:
            self.log.emit("Discovering and parsing DBC files...")
            comparator = DbcComparator()
            if self.pair_map is None:
                result = comparator.compare_folders(
                    self.old_folder,
                    self.new_folder,
                    progress_callback=lambda msg: self.log.emit(msg),
                )
            else:
                result = comparator.compare_manual(
                    self.old_folder,
                    self.new_folder,
                    self.pair_map,
                    progress_callback=lambda msg: self.log.emit(msg),
                )
            self.compared.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class ExportWorker(QThread):
    log = Signal(str)
    completed = Signal(object, object)
    failed = Signal(str)

    def __init__(self, result: ComparisonResult, output_path: Path) -> None:
        super().__init__()
        self.result = result
        self.output_path = output_path

    def run(self) -> None:
        try:
            self.log.emit("Writing Excel report...")
            write_excel_report(self.result, self.output_path)
            self.completed.emit(self.output_path, self.result.summary())
        except Exception as exc:
            self.failed.emit(str(exc))


class ManualPairingDialog(QDialog):
    """Lets the user choose which new-baseline file each old-baseline file pairs with.

    The chosen pairing is returned via pair_map() after Save.
    """

    def __init__(
        self,
        parent,
        old_folder: Path,
        new_folder: Path,
        previous: dict[str, str | None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Manual DBC Pairing")
        self.resize(780, 520)
        self._pair_map: dict[str, str | None] = {}

        old_files = sorted(collect_dbc_files(old_folder))
        new_files = sorted(collect_dbc_files(new_folder))

        layout = QVBoxLayout(self)
        hint = QLabel(
            "Pick the new-baseline file for each old-baseline file. Old files set to "
            "\"— Removed (no pair) —\" are reported as removed; new files not selected "
            "in any pair are reported as added."
        )
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        counts = QLabel(f"{len(old_files)} old file(s)  ·  {len(new_files)} new file(s)")
        counts.setObjectName("hintLabel")
        layout.addWidget(counts)

        self.table = QTableWidget(len(old_files), 2)
        self.table.setHorizontalHeaderLabels(["Old Baseline DBC", "New Baseline DBC"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        for row, old_rel in enumerate(old_files):
            old_item = QTableWidgetItem(old_rel)
            old_item.setToolTip(old_rel)
            self.table.setItem(row, 0, old_item)

            combo = NoWheelComboBox()
            combo.addItem("— Removed (no pair) —", None)
            for new_rel in new_files:
                combo.addItem(new_rel, new_rel)
            # Restore the previously saved choice; otherwise default to the
            # same relative path, mirroring auto pairing.
            if previous is not None and old_rel in previous:
                target = previous[old_rel]
            elif old_rel in new_files:
                target = old_rel
            else:
                target = None
            if target is not None and target in new_files:
                combo.setCurrentIndex(1 + new_files.index(target))
            self.table.setCellWidget(row, 1, combo)

        layout.addWidget(self.table)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_save(self) -> None:
        pair_map: dict[str, str | None] = {}
        used_new: dict[str, str] = {}
        duplicates: list[str] = []
        for row in range(self.table.rowCount()):
            old_rel = self.table.item(row, 0).text()
            new_rel = self.table.cellWidget(row, 1).currentData()
            pair_map[old_rel] = new_rel
            if new_rel:
                if new_rel in used_new:
                    duplicates.append(f"{new_rel} (paired with {used_new[new_rel]} and {old_rel})")
                else:
                    used_new[new_rel] = old_rel
        if duplicates:
            QMessageBox.warning(
                self,
                "Duplicate Pairing",
                "Each new DBC file can only be paired once:\n" + "\n".join(duplicates),
            )
            return
        self._pair_map = pair_map
        self.accept()

    def pair_map(self) -> dict[str, str | None]:
        return dict(self._pair_map)


class RenameReviewDialog(QDialog):
    """Lets the user accept or reject each auto-detected signal rename.

    Rejected renames are exported as a Removed + Added pair instead.
    """

    def __init__(self, parent, renames: list[Change]) -> None:
        super().__init__(parent)
        self.setWindowTitle("Review Renamed Signals")
        self.resize(880, 480)

        layout = QVBoxLayout(self)
        hint = QLabel(
            "Uncheck a row to reject the rename — it will be reported as a "
            "Removed + Added signal in the Excel report. Hover a row for details."
        )
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        headers = ["Accept", "DBC File", "Message", "Old Signal", "New Signal", "Confidence", "Level"]
        self.table = QTableWidget(len(renames), len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        for row, change in enumerate(renames):
            accept_item = QTableWidgetItem()
            accept_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            accept_item.setCheckState(Qt.CheckState.Checked)
            confidence = "" if change.confidence is None else f"{change.confidence:.2f}"
            cells = [
                accept_item,
                QTableWidgetItem(change.dbc_file),
                QTableWidgetItem(change.parent_message),
                QTableWidgetItem(change.old_name),
                QTableWidgetItem(change.new_name),
                QTableWidgetItem(confidence),
                QTableWidgetItem(change.confidence_level),
            ]
            for col, item in enumerate(cells):
                if change.description:
                    item.setToolTip(change.description)
                self.table.setItem(row, col, item)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setStretchLastSection(False)
        layout.addWidget(self.table)

        accept_all = QPushButton("Accept All")
        reject_all = QPushButton("Reject All")
        accept_all.clicked.connect(lambda: self._set_all(Qt.CheckState.Checked))
        reject_all.clicked.connect(lambda: self._set_all(Qt.CheckState.Unchecked))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        button_row = QHBoxLayout()
        button_row.addWidget(accept_all)
        button_row.addWidget(reject_all)
        button_row.addStretch()
        button_row.addWidget(buttons)
        layout.addLayout(button_row)

    def _set_all(self, state: Qt.CheckState) -> None:
        for row in range(self.table.rowCount()):
            self.table.item(row, 0).setCheckState(state)

    def rejected_indices(self) -> set[int]:
        return {
            row
            for row in range(self.table.rowCount())
            if self.table.item(row, 0).checkState() != Qt.CheckState.Checked
        }


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DBC Compare Tool")
        self.resize(1000, 780)
        self.setMinimumSize(720, 520)
        self.worker: CompareWorker | None = None
        self.export_worker: ExportWorker | None = None
        self._pending_output_path: Path | None = None
        self.last_report: Path | None = None
        self._settings = QSettings("DbcCompareTool", "DBCCompareTool")

        self.old_input = DropLineEdit()
        self.new_input = DropLineEdit()
        self.output_input = QLineEdit(str(Path.cwd() / "dbc_compare_report.xlsx"))
        self.run_auto_button = QPushButton("Run Auto Compare")
        self.run_manual_button = QPushButton("Run Manual Compare")
        self.manual_pair_button = QPushButton("Manual Pairing…")
        self.open_button = QPushButton("Open Report")
        self.progress = QProgressBar()
        self.log_view = QTextEdit()
        self.signal_focus_panel = SignalFocusPanel(self)

        # Manual pairing saved from the Manual Pairing dialog, plus the folder
        # inputs it was built for; invalidated when either folder changes.
        self._saved_pair_map: dict[str, str | None] | None = None
        self._saved_pair_folders: tuple[str, str] | None = None

        # Filter checkboxes
        self.chk_added = QCheckBox("Added")
        self.chk_removed = QCheckBox("Removed")
        self.chk_modified = QCheckBox("Modified")
        self.chk_renamed = QCheckBox("Renamed")
        for chk in (self.chk_added, self.chk_removed, self.chk_modified, self.chk_renamed):
            chk.setChecked(True)

        # Manual runs always review detected signal renames before export.
        self._review_renames_this_run = False

        self._build_menu()
        self._build_layout()
        self._wire_events()
        self._restore_paths()
        self.statusBar().showMessage("Ready")

    def _build_menu(self) -> None:
        help_menu = self.menuBar().addMenu("Help")
        user_guide_action = help_menu.addAction("User Guide")
        release_notes_action = help_menu.addAction("Release Notes")
        about_action = help_menu.addAction("About")
        user_guide_action.triggered.connect(
            lambda: self._show_help_document("User Guide", "help/user_guide.md")
        )
        release_notes_action.triggered.connect(
            lambda: self._show_help_document("Release Notes", "help/release_notes.md")
        )
        about_action.triggered.connect(lambda: self._show_help_document("About", "help/about.md"))

    def _build_layout(self) -> None:
        # Header
        title = QLabel("DBC Compare Tool")
        title.setObjectName("appTitle")

        version_label = QLabel(f"v{__version__}")
        version_label.setObjectName("versionBadge")

        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        title_row.addWidget(title)
        title_row.addWidget(version_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        title_row.addStretch()

        subtitle = QLabel("Compare CAN DBC baselines and export an Excel change report")
        subtitle.setObjectName("appSubtitle")

        header = QVBoxLayout()
        header.setSpacing(2)
        header.addLayout(title_row)
        header.addWidget(subtitle)

        # Input form
        input_group = QGroupBox("Baselines && Report")
        form = QGridLayout(input_group)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)

        form.addWidget(QLabel("Old Baseline Folder"), 0, 0)
        form.addWidget(self.old_input, 0, 1)
        old_button = QPushButton("Browse")
        old_button.clicked.connect(lambda: self._choose_folder(self.old_input))
        form.addWidget(old_button, 0, 2)

        form.addWidget(QLabel("New Baseline Folder"), 1, 0)
        form.addWidget(self.new_input, 1, 1)
        new_button = QPushButton("Browse")
        new_button.clicked.connect(lambda: self._choose_folder(self.new_input))
        form.addWidget(new_button, 1, 2)

        form.addWidget(QLabel("Report Path"), 2, 0)
        form.addWidget(self.output_input, 2, 1)
        output_button = QPushButton("Browse")
        output_button.clicked.connect(self._choose_report)
        form.addWidget(output_button, 2, 2)

        # Filter group
        filter_group = QGroupBox("Include Change Types")
        filter_layout = QHBoxLayout(filter_group)
        for chk in (self.chk_added, self.chk_removed, self.chk_modified, self.chk_renamed):
            filter_layout.addWidget(chk)
        filter_layout.addStretch()

        # Action buttons
        self.run_auto_button.setObjectName("primaryButton")
        self.run_auto_button.setToolTip(
            "Pair DBC files automatically by relative path and content similarity, then compare."
        )
        self.run_manual_button.setToolTip(
            "Compare using the saved manual pairing (or auto pairing if none is saved), "
            "then review each detected signal rename before the report is written."
        )
        self.manual_pair_button.setToolTip(
            "Choose which new-baseline file each old-baseline file is compared against."
        )
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addWidget(self.run_auto_button)
        buttons.addWidget(self.run_manual_button)
        buttons.addWidget(self.manual_pair_button)
        buttons.addWidget(self.open_button)
        buttons.addStretch()

        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.log_view.setObjectName("logView")
        self.log_view.setReadOnly(True)
        self.open_button.setEnabled(False)

        # Tab 1 — the folder-to-folder baseline comparison
        baseline_content = QWidget()
        baseline_layout = QVBoxLayout(baseline_content)
        baseline_layout.setContentsMargins(0, 0, 0, 0)
        baseline_layout.setSpacing(10)
        baseline_layout.addWidget(input_group)
        baseline_layout.addWidget(filter_group)
        baseline_layout.addLayout(buttons)
        baseline_layout.addStretch()
        baseline_tab = _scrollable(baseline_content)

        # Tab 2 — application-layer signal view
        focus_tab = QWidget()
        focus_layout = QVBoxLayout(focus_tab)
        focus_layout.setContentsMargins(12, 12, 12, 12)
        focus_layout.addWidget(self.signal_focus_panel)

        self.tabs = QTabWidget()
        self.tabs.addTab(baseline_tab, "Baseline Compare")
        self._focus_tab_index = self.tabs.addTab(focus_tab, "Signal Focus")
        self.tabs.setTabToolTip(0, "Compare two baselines message by message and export the full change report.")
        self.tabs.setTabToolTip(
            1,
            "Compare the signals of one ECU node — data type, scaling, range, value table, "
            "init value — ignoring frames and timing.",
        )

        # Top pane: controls
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(16, 12, 16, 8)
        top_layout.setSpacing(10)
        top_layout.addLayout(header)
        top_layout.addWidget(self.tabs)
        top_layout.addWidget(self.progress)

        # Bottom pane: log
        log_label = QLabel("EXECUTION LOG")
        log_label.setObjectName("sectionLabel")
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(16, 4, 16, 12)
        log_layout.setSpacing(6)
        log_layout.addWidget(log_label)
        log_layout.addWidget(self.log_view)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(top_widget)
        splitter.addWidget(log_widget)
        # The controls take the space; the log is a status strip, not the view.
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([620, 120])
        self.log_view.setMinimumHeight(80)
        log_widget.setMinimumHeight(110)

        self.setCentralWidget(splitter)

    def _wire_events(self) -> None:
        self.run_auto_button.clicked.connect(self._run_auto)
        self.run_manual_button.clicked.connect(self._run_manual)
        self.manual_pair_button.clicked.connect(self._open_manual_pairing)
        self.open_button.clicked.connect(self._open_report)
        self.old_input.textChanged.connect(self._invalidate_saved_pairing)
        self.new_input.textChanged.connect(self._invalidate_saved_pairing)
        self.signal_focus_panel.log.connect(self._log)
        self.signal_focus_panel.busy_changed.connect(self._on_focus_busy)
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index: int) -> None:
        if index == self._focus_tab_index:
            self.signal_focus_panel.prefill_folders(*self._current_folder_inputs())

    def _on_focus_busy(self, busy: bool) -> None:
        if busy:
            self.progress.setRange(0, 0)
        else:
            self.progress.setRange(0, 1)
            self.progress.setValue(1)
        self._set_actions_enabled(not busy)

    def _current_folder_inputs(self) -> tuple[str, str]:
        return (self.old_input.text().strip(), self.new_input.text().strip())

    def _invalidate_saved_pairing(self) -> None:
        if self._saved_pair_folders and self._saved_pair_folders != self._current_folder_inputs():
            self._saved_pair_map = None
            self._saved_pair_folders = None
            self._log("Baseline folder changed — saved manual pairing discarded.")

    def _open_manual_pairing(self) -> bool:
        """Open the pairing dialog; returns True if a pairing was saved."""
        old_text, new_text = self._current_folder_inputs()
        # Guard empty text explicitly: Path("") is ".", which is_dir() accepts.
        if not old_text or not new_text or not Path(old_text).is_dir() or not Path(new_text).is_dir():
            QMessageBox.warning(self, "Invalid Input", "Select valid old and new baseline folders first.")
            return False
        old_folder = Path(old_text)
        new_folder = Path(new_text)

        previous = self._saved_pair_map if self._saved_pair_folders == self._current_folder_inputs() else None
        try:
            dialog = ManualPairingDialog(self, old_folder, new_folder, previous=previous)
        except OSError as exc:
            QMessageBox.critical(self, "Load Failed", f"Unable to scan folders: {exc}")
            return False

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False

        self._saved_pair_map = dialog.pair_map()
        self._saved_pair_folders = self._current_folder_inputs()
        paired = sum(1 for new_rel in self._saved_pair_map.values() if new_rel)
        removed = len(self._saved_pair_map) - paired
        self._log(f"Manual pairing saved: {paired} pair(s), {removed} old file(s) marked removed.")
        self.statusBar().showMessage("Manual pairing saved — click Run Manual Compare to use it")
        return True

    def _choose_folder(self, target: QLineEdit) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Baseline Folder")
        if folder:
            target.setText(folder)

    def _choose_report(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Excel Report", self.output_input.text(), "Excel (*.xlsx)"
        )
        if path:
            if not path.lower().endswith(".xlsx"):
                path += ".xlsx"
            self.output_input.setText(path)

    def _selected_change_types(self) -> set[str]:
        types: set[str] = set()
        if self.chk_added.isChecked():
            types.add("Added")
        if self.chk_removed.isChecked():
            types.add("Removed")
        if self.chk_modified.isChecked():
            types.add("Modified")
        if self.chk_renamed.isChecked():
            types.add("Renamed")
        return types

    def _run_auto(self) -> None:
        self._start_compare(pair_map=None, review_renames=False)

    def _run_manual(self) -> None:
        # Use the saved manual pairing when available; otherwise fall back to
        # auto pairing. Either way, signal renames are reviewed before export.
        if self._saved_pair_map is not None and self._saved_pair_folders == self._current_folder_inputs():
            pair_map = self._saved_pair_map
        else:
            pair_map = None
        self._start_compare(pair_map=pair_map, review_renames=True)

    def _start_compare(self, pair_map: dict[str, str | None] | None, review_renames: bool) -> None:
        old_text, new_text = self._current_folder_inputs()
        output_path = Path(self.output_input.text().strip())
        # Guard empty text explicitly: Path("") is ".", which is_dir() accepts.
        if not old_text or not new_text or not Path(old_text).is_dir() or not Path(new_text).is_dir():
            QMessageBox.warning(self, "Invalid Input", "Select valid old and new baseline folders.")
            return
        old_folder = Path(old_text)
        new_folder = Path(new_text)
        if output_path.suffix.lower() != ".xlsx":
            QMessageBox.warning(self, "Invalid Output", "Report path must end with .xlsx.")
            return

        selected = self._selected_change_types()
        if not selected:
            QMessageBox.warning(self, "No Filter Selected", "Select at least one change type to include.")
            return

        self._pending_output_path = output_path
        self._review_renames_this_run = review_renames
        self.log_view.clear()
        pairing = "manual pairing" if pair_map is not None else "auto pairing"
        review = ", rename review" if review_renames else ""
        self._log(f"Starting comparison ({pairing}{review})...")
        self.progress.setRange(0, 0)
        self._set_actions_enabled(False)
        self.open_button.setEnabled(False)
        self.worker = CompareWorker(old_folder, new_folder, pair_map)
        self.worker.log.connect(self._log)
        self.worker.compared.connect(self._on_compared)
        self.worker.failed.connect(self._failed)
        self.worker.start()

    def _set_actions_enabled(self, enabled: bool) -> None:
        self.run_auto_button.setEnabled(enabled)
        self.run_manual_button.setEnabled(enabled)
        self.manual_pair_button.setEnabled(enabled)

    def _on_compared(self, result: ComparisonResult) -> None:
        if self._review_renames_this_run:
            renames = [c for c in result.signal_changes if c.change_type == "Renamed"]
            if renames:
                dialog = RenameReviewDialog(self, renames)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    rejected = dialog.rejected_indices()
                    if rejected:
                        result = reject_signal_renames(result, rejected)
                        self._log(
                            f"Rename review: {len(rejected)} of {len(renames)} signal rename(s) "
                            "rejected — exported as Removed + Added."
                        )
                    else:
                        self._log(f"Rename review: all {len(renames)} signal rename(s) accepted.")
                else:
                    self._log("Rename review cancelled — keeping all detected renames.")
            else:
                self._log("Rename review: no renamed signals detected.")

        result = filter_result(result, self._selected_change_types())
        self.export_worker = ExportWorker(result, self._pending_output_path)
        self.export_worker.log.connect(self._log)
        self.export_worker.completed.connect(self._completed)
        self.export_worker.failed.connect(self._failed)
        self.export_worker.start()

    def _restore_paths(self) -> None:
        if val := self._settings.value("last_old_folder"):
            self.old_input.setText(str(val))
        if val := self._settings.value("last_new_folder"):
            self.new_input.setText(str(val))
        if val := self._settings.value("last_report_path"):
            self.output_input.setText(str(val))

    def _save_paths(self) -> None:
        self._settings.setValue("last_old_folder", self.old_input.text())
        self._settings.setValue("last_new_folder", self.new_input.text())
        self._settings.setValue("last_report_path", self.output_input.text())

    def _completed(self, report_path: Path, summary: dict) -> None:
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self._set_actions_enabled(True)
        self.open_button.setEnabled(True)
        self.last_report = report_path
        self._log(f"Report generated: {report_path}")
        self._log(f"Total changes: {summary['Total Changes']}")
        self._save_paths()
        ts = datetime.now().strftime("%H:%M")
        self.statusBar().showMessage(
            f"Last run: {summary['Total Changes']} total changes  ·  {ts}"
        )

    def _failed(self, message: str) -> None:
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self._set_actions_enabled(True)
        self._log(f"Failed: {message}")
        self.statusBar().showMessage("Failed — see log for details")
        QMessageBox.critical(self, "Comparison Failed", message)

    def _open_report(self) -> None:
        if self.last_report and self.last_report.exists():
            os.startfile(self.last_report)
        else:
            QMessageBox.information(
                self, "Report Not Found", "The report file no longer exists. Run the comparison again."
            )

    def closeEvent(self, event) -> None:
        running = [w for w in (self.worker, self.export_worker) if w and w.isRunning()]
        running += self.signal_focus_panel.running_workers()
        if running:
            reply = QMessageBox.question(
                self,
                "Comparison Running",
                "A comparison is still running. Quit anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            # Detach signals, then stop the threads before Qt destroys them,
            # otherwise the app crashes with "QThread destroyed while running".
            for worker in running:
                worker.disconnect()
                worker.terminate()
                worker.wait(3000)
        self.signal_focus_panel.save_state()
        event.accept()

    def _show_help_document(self, title: str, filename: str) -> None:
        try:
            content = _read_resource_text(filename).replace("{version}", __version__)
        except OSError as exc:
            QMessageBox.critical(self, title, f"Unable to open help file: {exc}")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(720, 560)
        layout = QVBoxLayout(dialog)
        viewer = QTextBrowser()
        viewer.setOpenExternalLinks(True)
        viewer.setMarkdown(content)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(viewer)
        layout.addWidget(buttons)
        dialog.exec()

    def _log(self, message: str) -> None:
        self.log_view.append(message)


def main() -> int:
    app = QApplication(sys.argv)
    icon_path = _resource_path("app.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    app.setStyleSheet(_STYLESHEET)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
