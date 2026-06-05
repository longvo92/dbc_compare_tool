from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from dbc_compare_tool.core.comparator import DbcComparator
from dbc_compare_tool.report.excel import write_excel_report


APP_AUTHOR = "LongVT23"


def _resource_path(filename: str) -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "resources" / filename
    return Path(__file__).resolve().parents[3] / "resources" / filename


def _app_icon() -> QIcon:
    icon_path = _resource_path("vinfast_logo.png")
    return QIcon(str(icon_path))


def _read_resource_text(filename: str) -> str:
    return _resource_path(filename).read_text(encoding="utf-8")


class CompareWorker(QThread):
    log = Signal(str)
    completed = Signal(object, object)
    failed = Signal(str)

    def __init__(self, old_folder: Path, new_folder: Path, output_path: Path) -> None:
        super().__init__()
        self.old_folder = old_folder
        self.new_folder = new_folder
        self.output_path = output_path

    def run(self) -> None:
        try:
            self.log.emit("Discovering and parsing DBC files...")
            result = DbcComparator().compare_folders(self.old_folder, self.new_folder)
            self.log.emit("Writing Excel report...")
            write_excel_report(result, self.output_path)
            self.completed.emit(self.output_path, result.summary())
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DBC Compare Tool")
        self.setWindowIcon(_app_icon())
        self.resize(840, 560)
        self.worker: CompareWorker | None = None
        self.last_report: Path | None = None

        self.old_input = QLineEdit()
        self.new_input = QLineEdit()
        self.output_input = QLineEdit(str(Path.cwd() / "dbc_compare_report.xlsx"))
        self.run_button = QPushButton("Run Comparison")
        self.open_button = QPushButton("Open Report")
        self.progress = QProgressBar()
        self.log_view = QTextEdit()

        self._build_menu()
        self._build_layout()
        self._wire_events()

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
        central = QWidget()
        root = QVBoxLayout(central)
        brand_row = QHBoxLayout()
        logo = QLabel()
        logo_pixmap = QPixmap(str(_resource_path("vinfast.jpg")))
        if not logo_pixmap.isNull():
            logo.setPixmap(
                logo_pixmap.scaledToHeight(
                    44,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        logo.setFixedHeight(52)
        logo.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        title = QLabel("DBC Compare Tool")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        author = QLabel(f"Author: {APP_AUTHOR}")
        author.setStyleSheet("color: #555555;")
        title_column = QVBoxLayout()
        title_column.addWidget(title)
        title_column.addWidget(author)
        brand_row.addWidget(logo)
        brand_row.addSpacing(10)
        brand_row.addLayout(title_column)
        brand_row.addStretch()
        form = QGridLayout()

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

        buttons = QHBoxLayout()
        buttons.addWidget(self.run_button)
        buttons.addWidget(self.open_button)
        buttons.addStretch()

        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.log_view.setReadOnly(True)
        self.open_button.setEnabled(False)

        root.addLayout(brand_row)
        root.addLayout(form)
        root.addLayout(buttons)
        root.addWidget(self.progress)
        root.addWidget(QLabel("Execution Log"))
        root.addWidget(self.log_view)
        self.setCentralWidget(central)

    def _wire_events(self) -> None:
        self.run_button.clicked.connect(self._run_comparison)
        self.open_button.clicked.connect(self._open_report)

    def _choose_folder(self, target: QLineEdit) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Baseline Folder")
        if folder:
            target.setText(folder)

    def _choose_report(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save Excel Report", self.output_input.text(), "Excel (*.xlsx)")
        if path:
            if not path.lower().endswith(".xlsx"):
                path += ".xlsx"
            self.output_input.setText(path)

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

        self.log_view.clear()
        self._log("Starting comparison...")
        self.progress.setRange(0, 0)
        self.run_button.setEnabled(False)
        self.open_button.setEnabled(False)
        self.worker = CompareWorker(old_folder, new_folder, output_path)
        self.worker.log.connect(self._log)
        self.worker.completed.connect(self._completed)
        self.worker.failed.connect(self._failed)
        self.worker.start()

    def _completed(self, report_path: Path, summary: dict) -> None:
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.run_button.setEnabled(True)
        self.open_button.setEnabled(True)
        self.last_report = report_path
        self._log(f"Report generated: {report_path}")
        self._log(f"Total changes: {summary['Total Changes']}")

    def _failed(self, message: str) -> None:
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.run_button.setEnabled(True)
        self._log(f"Failed: {message}")
        QMessageBox.critical(self, "Comparison Failed", message)

    def _open_report(self) -> None:
        if self.last_report and self.last_report.exists():
            os.startfile(self.last_report)

    def _show_help_document(self, title: str, filename: str) -> None:
        try:
            content = _read_resource_text(filename)
        except OSError as exc:
            QMessageBox.critical(self, title, f"Unable to open help file: {exc}")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setWindowIcon(_app_icon())
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
    app.setWindowIcon(_app_icon())
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
