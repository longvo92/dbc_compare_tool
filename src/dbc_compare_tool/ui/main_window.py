from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QSettings, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSplitter,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from dbc_compare_tool import __version__
from dbc_compare_tool.core.comparator import DbcComparator
from dbc_compare_tool.core.models import ComparisonResult
from dbc_compare_tool.report.excel import write_excel_report


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
    font-size: 13px;
    color: #1f2430;
}
QLabel#appTitle {
    font-size: 22px;
    font-weight: 700;
    color: #16213a;
}
QLabel#appSubtitle {
    color: #6b7280;
    font-size: 12px;
}
QLabel#versionBadge {
    color: #2563eb;
    background: #e3ecfd;
    border-radius: 9px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 600;
}
QLabel#sectionLabel {
    color: #6b7280;
    font-size: 11px;
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
    font-size: 12px;
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
"""


def _read_resource_text(filename: str) -> str:
    return _resource_path(filename).read_text(encoding="utf-8")


def _filter_result(result: ComparisonResult, selected_types: set[str]) -> ComparisonResult:
    if not selected_types:
        return result
    return ComparisonResult(
        message_changes=[c for c in result.message_changes if c.change_type in selected_types],
        signal_changes=[c for c in result.signal_changes if c.change_type in selected_types],
        file_pairs=result.file_pairs,
    )


class DropLineEdit(QLineEdit):
    """QLineEdit that accepts folder drag-and-drop."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self.setPlaceholderText("Browse or drag & drop a folder here")

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            if Path(url.toLocalFile()).is_dir():
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event) -> None:
        path = Path(event.mimeData().urls()[0].toLocalFile())
        if path.is_dir():
            self.setText(str(path))
            event.acceptProposedAction()


class CompareWorker(QThread):
    log = Signal(str)
    completed = Signal(object, object)
    failed = Signal(str)

    def __init__(
        self,
        old_folder: Path,
        new_folder: Path,
        output_path: Path,
        selected_types: set[str] | None = None,
    ) -> None:
        super().__init__()
        self.old_folder = old_folder
        self.new_folder = new_folder
        self.output_path = output_path
        self.selected_types: set[str] = selected_types or set()

    def run(self) -> None:
        try:
            self.log.emit("Discovering and parsing DBC files...")
            result = DbcComparator().compare_folders(
                self.old_folder,
                self.new_folder,
                progress_callback=lambda msg: self.log.emit(msg),
            )
            if self.selected_types:
                result = _filter_result(result, self.selected_types)
            self.log.emit("Writing Excel report...")
            write_excel_report(result, self.output_path)
            self.completed.emit(self.output_path, result.summary())
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DBC Compare Tool")
        self.resize(860, 660)
        self.setMinimumSize(700, 500)
        self.worker: CompareWorker | None = None
        self.last_report: Path | None = None
        self._settings = QSettings("DbcCompareTool", "DBCCompareTool")

        self.old_input = DropLineEdit()
        self.new_input = DropLineEdit()
        self.output_input = QLineEdit(str(Path.cwd() / "dbc_compare_report.xlsx"))
        self.run_button = QPushButton("Run Comparison")
        self.open_button = QPushButton("Open Report")
        self.progress = QProgressBar()
        self.log_view = QTextEdit()

        # Filter checkboxes
        self.chk_added = QCheckBox("Added")
        self.chk_removed = QCheckBox("Removed")
        self.chk_modified = QCheckBox("Modified")
        self.chk_renamed = QCheckBox("Renamed")
        for chk in (self.chk_added, self.chk_removed, self.chk_modified, self.chk_renamed):
            chk.setChecked(True)

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
        self.run_button.setObjectName("primaryButton")
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addWidget(self.run_button)
        buttons.addWidget(self.open_button)
        buttons.addStretch()

        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.log_view.setObjectName("logView")
        self.log_view.setReadOnly(True)
        self.open_button.setEnabled(False)

        # Top pane: controls
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(16, 12, 16, 8)
        top_layout.setSpacing(10)
        top_layout.addLayout(header)
        top_layout.addWidget(input_group)
        top_layout.addWidget(filter_group)
        top_layout.addLayout(buttons)
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
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        self.setCentralWidget(splitter)

    def _wire_events(self) -> None:
        self.run_button.clicked.connect(self._run_comparison)
        self.open_button.clicked.connect(self._open_report)

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
            types.add("Possible Rename")
        return types

    def _run_comparison(self) -> None:
        old_folder = Path(self.old_input.text().strip())
        new_folder = Path(self.new_input.text().strip())
        output_path = Path(self.output_input.text().strip())
        if not old_folder.is_dir() or not new_folder.is_dir():
            QMessageBox.warning(self, "Invalid Input", "Select valid old and new baseline folders.")
            return
        if output_path.suffix.lower() != ".xlsx":
            QMessageBox.warning(self, "Invalid Output", "Report path must end with .xlsx.")
            return

        selected = self._selected_change_types()
        if not selected:
            QMessageBox.warning(self, "No Filter Selected", "Select at least one change type to include.")
            return

        self.log_view.clear()
        self._log("Starting comparison...")
        self.progress.setRange(0, 0)
        self.run_button.setEnabled(False)
        self.open_button.setEnabled(False)
        self.worker = CompareWorker(old_folder, new_folder, output_path, selected)
        self.worker.log.connect(self._log)
        self.worker.completed.connect(self._completed)
        self.worker.failed.connect(self._failed)
        self.worker.start()

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
        self.run_button.setEnabled(True)
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
        self.run_button.setEnabled(True)
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
        if self.worker and self.worker.isRunning():
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
            # Detach signals, then stop the thread before Qt destroys it,
            # otherwise the app crashes with "QThread destroyed while running".
            self.worker.log.disconnect()
            self.worker.completed.disconnect()
            self.worker.failed.disconnect()
            self.worker.terminate()
            self.worker.wait(3000)
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
    app.setStyleSheet(_STYLESHEET)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
