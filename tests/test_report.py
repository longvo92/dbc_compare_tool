"""Excel report tests.

Both writers are exercised end to end — written to disk, reopened with
openpyxl, and read back. Without this the report layer can crash or drop a
sheet while the whole suite stays green, which is exactly what a release build
would then ship.
"""

import tempfile
import unittest
from pathlib import Path

from openpyxl import load_workbook

from dbc_compare_tool.core.comparator import DbcComparator
from dbc_compare_tool.core.models import (
    DbcDatabase,
    Message,
    NodeSelection,
    Signal,
)
from dbc_compare_tool.core.signal_focus import NodeSelectionInput, compare_signal_focus
from dbc_compare_tool.report.excel import write_excel_report
from dbc_compare_tool.report.signal_focus_excel import write_signal_focus_report

_EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
_OLD_FOLDER = _EXAMPLES / "old"
_NEW_FOLDER = _EXAMPLES / "new"

APP_NODE = "AppEcu"


def _rows(sheet) -> list[list]:
    return [list(row) for row in sheet.iter_rows(min_row=2, values_only=True)]


def _signal(name: str, **kwargs) -> Signal:
    defaults = dict(
        start_bit=0, length=8, byte_order=1, value_type="unsigned", is_signed=False,
        factor=1.0, offset=0.0, minimum=0.0, maximum=255.0, unit="",
        receivers=(APP_NODE,),
    )
    defaults.update(kwargs)
    return Signal(name=name, **defaults)


def _database(*signals: Signal) -> DbcDatabase:
    message = Message(
        name="Status", can_id=0x100, dlc=8, transmitter="OtherEcu", senders=("OtherEcu",)
    )
    for signal in signals:
        message.signals[signal.name] = signal
    database = DbcDatabase(path=Path("Bus_A.dbc"))
    database.messages[message.name] = message
    database.nodes = (APP_NODE, "OtherEcu")
    return database


class BaselineReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = DbcComparator().compare_folders(_OLD_FOLDER, _NEW_FOLDER)

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.output = Path(self._tmp.name) / "report.xlsx"
        write_excel_report(self.result, self.output)
        self.workbook = load_workbook(self.output)
        self.addCleanup(self.workbook.close)

    def test_workbook_has_the_five_documented_sheets_in_order(self):
        self.assertEqual(
            self.workbook.sheetnames,
            ["Summary", "DBC Overview", "Message Details", "Signal Details", "Property Diff"],
        )

    def test_summary_total_matches_the_result(self):
        sheet = self.workbook["Summary"]
        totals = {row[0]: row[1] for row in sheet.iter_rows(min_row=4, values_only=True)}
        self.assertEqual(totals["Total Changes"], self.result.summary()["Total Changes"])
        self.assertEqual(totals["Messages Renamed"], self.result.summary()["Messages Renamed"])

    def test_every_signal_change_reaches_the_signal_sheet(self):
        rows = _rows(self.workbook["Signal Details"])
        self.assertEqual(len(rows), len(self.result.signal_changes))
        renamed = {(row[3], row[4]) for row in rows if row[2] == "Renamed"}
        self.assertIn(("VehicleSpeed", "VehSpd"), renamed)

    def test_can_id_is_written_in_hexadecimal(self):
        rows = _rows(self.workbook["Message Details"])
        self.assertTrue(rows)
        self.assertTrue(all(str(row[4]).startswith("0x") for row in rows if row[4]))

    def test_property_diff_carries_old_and_new_values(self):
        rows = _rows(self.workbook["Property Diff"])
        self.assertTrue(rows)
        factor_rows = [row for row in rows if row[6] == "Factor"]
        self.assertTrue(factor_rows, "the EngineRPM factor change should appear")
        self.assertNotEqual(factor_rows[0][7], factor_rows[0][8])

    def test_overview_lists_every_file_pair(self):
        rows = _rows(self.workbook["DBC Overview"])
        self.assertEqual(len(rows), len(self.result.file_pairs))
        self.assertEqual(rows[0][1], "Matched")

    def test_missing_parent_directory_is_created(self):
        nested = Path(self._tmp.name) / "a" / "b" / "report.xlsx"
        write_excel_report(self.result, nested)
        self.assertTrue(nested.is_file())


class SignalFocusReportTests(unittest.TestCase):
    def setUp(self):
        old_db = _database(
            _signal("VehicleSpeed", factor=0.01),
            _signal("Mode", value_descriptions=((0, "Off"), (1, "On"), (2, "Reserved"))),
            _signal("Dropped"),
        )
        new_db = _database(
            _signal("VehicleSpeed", factor=0.1),
            _signal("Mode", value_descriptions=((0, "Off"), (2, "Charging"), (3, "Fault"))),
            _signal("Fresh"),
        )
        selection = NodeSelection("Bus_A.dbc", "Bus_A.dbc", "Bus_A.dbc", APP_NODE, APP_NODE)
        self.result = compare_signal_focus(
            [NodeSelectionInput(selection=selection, old_db=old_db, new_db=new_db)],
            ["VehicleSpeed", "Mode", "Dropped", "Fresh", "Typo"],
        )

        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.output = Path(self._tmp.name) / "signal_focus.xlsx"
        write_signal_focus_report(self.result, self.output)
        self.workbook = load_workbook(self.output)
        self.addCleanup(self.workbook.close)

    def test_workbook_has_the_four_documented_sheets_in_order(self):
        self.assertEqual(
            self.workbook.sheetnames,
            ["Signal Focus Summary", "Signal Focus", "Property Diff (App)", "Value Table Diff"],
        )

    def test_one_row_per_requested_signal_in_list_order(self):
        rows = _rows(self.workbook["Signal Focus"])
        self.assertEqual(
            [row[0] for row in rows],
            ["VehicleSpeed", "Mode", "Dropped", "Fresh", "Typo"],
        )
        self.assertEqual([row[1] for row in rows][:3], ["Modified", "Modified", "Removed"])

    def test_summary_sheet_reports_the_node_and_the_review_count(self):
        sheet = self.workbook["Signal Focus Summary"]
        cells = [row[0] for row in sheet.iter_rows(values_only=True)]
        self.assertIn("Bus_A.dbc", cells)
        counts = {
            row[0]: row[1]
            for row in sheet.iter_rows(values_only=True)
            if row[0] in ("Needs Review", "Total Signals", "Removed")
        }
        self.assertEqual(counts["Total Signals"], 5)
        self.assertEqual(counts["Needs Review"], self.result.summary()["Needs Review"])

    def test_property_diff_sheet_lists_the_scaling_change(self):
        rows = _rows(self.workbook["Property Diff (App)"])
        factor = [row for row in rows if row[0] == "VehicleSpeed" and row[3] == "Factor"]
        self.assertEqual(len(factor), 1)
        self.assertEqual((factor[0][4], factor[0][5]), ("0.01", "0.1"))

    def test_value_table_sheet_classifies_every_changed_entry(self):
        rows = _rows(self.workbook["Value Table Diff"])
        self.assertEqual(
            {(row[1], row[4]) for row in rows},
            {("1", "Value Removed"), ("2", "Relabeled"), ("3", "Value Added")},
        )


if __name__ == "__main__":
    unittest.main()
