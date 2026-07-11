"""Message rename detection wired into compare_databases (CAN ID change + name change)."""

import tempfile
import unittest
from pathlib import Path

from dbc_compare_tool.core.comparator import DbcComparator
from dbc_compare_tool.core.parser import parse_dbc

_OLD_DBC = """VERSION ""

BO_ 100 WheelSpeeds: 8 ABS
 SG_ FL_Speed : 0|16@1+ (0.01,0) [0|250] "km/h" ECM
 SG_ FR_Speed : 16|16@1+ (0.01,0) [0|250] "km/h" ECM
BA_ "GenMsgCycleTime" BO_ 100 20;
"""

_NEW_DBC = """VERSION ""

BO_ 400 WhlSpeeds: 8 ABS
 SG_ FL_Speed : 0|16@1+ (0.01,0) [0|250] "km/h" ECM
 SG_ FR_Speed : 16|16@1+ (0.01,0) [0|250] "km/h" ECM
BA_ "GenMsgCycleTime" BO_ 400 20;
"""


class TestMessageRenameViaCanIdChange(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        tmp_dir = Path(self._tmp_dir.name)
        old_path = tmp_dir / "old.dbc"
        new_path = tmp_dir / "new.dbc"
        old_path.write_text(_OLD_DBC, encoding="utf-8")
        new_path.write_text(_NEW_DBC, encoding="utf-8")

        old_db = parse_dbc(old_path)
        new_db = parse_dbc(new_path)
        self.result = DbcComparator().compare_databases("test.dbc", old_db, new_db)

    def test_message_detected_as_renamed(self):
        renames = [c for c in self.result.message_changes if c.change_type == "Renamed"]
        self.assertEqual(len(renames), 1)
        self.assertEqual(renames[0].old_name, "WheelSpeeds")
        self.assertEqual(renames[0].new_name, "WhlSpeeds")

    def test_no_removed_or_added_messages(self):
        added = [c for c in self.result.message_changes if c.change_type == "Added"]
        removed = [c for c in self.result.message_changes if c.change_type == "Removed"]
        self.assertEqual(len(added), 0)
        self.assertEqual(len(removed), 0)

    def test_rename_has_confidence(self):
        renames = [c for c in self.result.message_changes if c.change_type == "Renamed"]
        self.assertIsNotNone(renames[0].confidence)
        self.assertIn(renames[0].confidence_level, {"High", "Medium", "Low"})

    def test_signals_compared_under_renamed_message(self):
        # Signals kept identical layout, so no spurious signal changes should appear.
        self.assertEqual(len(self.result.signal_changes), 0)


if __name__ == "__main__":
    unittest.main()
