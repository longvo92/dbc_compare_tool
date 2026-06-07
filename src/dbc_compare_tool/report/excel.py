from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from dbc_compare_tool.core.models import Change, ComparisonResult


SUMMARY_ORDER = [
    "Messages Added",
    "Messages Removed",
    "Messages Modified",
    "Messages Renamed",
    "Signals Added",
    "Signals Removed",
    "Signals Modified",
    "Signals Renamed",
    "Total Changes",
]


def write_excel_report(result: ComparisonResult, output_path: Path) -> Path:
    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = "Summary"
    message_sheet = workbook.create_sheet("Message Details")
    signal_sheet = workbook.create_sheet("Signal Details")

    _write_summary(summary_sheet, result)
    _write_message_details(message_sheet, result.message_changes)
    _write_signal_details(signal_sheet, result.signal_changes)

    for sheet in workbook.worksheets:
        _format_sheet(sheet)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)
    return output_path


def _write_summary(sheet, result: ComparisonResult) -> None:
    sheet.append(["Metric", "Count"])
    summary = result.summary()
    for metric in SUMMARY_ORDER:
        sheet.append([metric, summary[metric]])


def _write_message_details(sheet, changes: list[Change]) -> None:
    sheet.append([
        "DBC File",
        "Change Type",
        "Old Message Name",
        "New Message Name",
        "CAN ID",
        "Confidence Score",
        "Confidence Level",
        "Change Description",
    ])
    for change in changes:
        sheet.append([
            change.dbc_file,
            change.change_type,
            change.old_name,
            change.new_name,
            change.can_id if change.can_id is not None else "",
            _format_confidence(change.confidence),
            change.confidence_level,
            change.description,
        ])


def _write_signal_details(sheet, changes: list[Change]) -> None:
    sheet.append([
        "DBC File",
        "Parent Message",
        "Change Type",
        "Old Signal Name",
        "New Signal Name",
        "Confidence Score",
        "Confidence Level",
        "Changed Properties",
    ])
    for change in changes:
        sheet.append([
            change.dbc_file,
            change.parent_message,
            change.change_type,
            change.old_name,
            change.new_name,
            _format_confidence(change.confidence),
            change.confidence_level,
            change.description,
        ])


def _format_sheet(sheet) -> None:
    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(color="FFFFFF", bold=True)
    for cell in sheet[1]:
        cell.fill = header_fill
        cell.font = header_font
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for row in sheet.iter_rows():
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    for column_cells in sheet.columns:
        max_length = max(len(str(cell.value or "")) for cell in column_cells)
        column_letter = get_column_letter(column_cells[0].column)
        sheet.column_dimensions[column_letter].width = min(max(max_length + 2, 12), 70)


def _format_confidence(confidence: float | None) -> str:
    return "" if confidence is None else f"{confidence:.2f}"
