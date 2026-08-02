from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QComboBox, QLineEdit


class NoWheelComboBox(QComboBox):
    """QComboBox that ignores wheel events.

    Used inside tables: scrolling the table must not silently change a
    selection, and the ignored event lets the table scroll instead.
    """

    def wheelEvent(self, event) -> None:
        event.ignore()


class DropLineEdit(QLineEdit):
    """QLineEdit that accepts folder drag-and-drop."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self.setPlaceholderText("Browse or drag & drop a folder here")
        # Without this the field demands room for the placeholder, which pushes
        # a horizontal scrollbar onto every layout it sits in.
        self.setMinimumWidth(160)

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
