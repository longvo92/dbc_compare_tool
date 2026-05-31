from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from dbc_compare_tool.core.comparator import DbcComparator
from dbc_compare_tool.core.parser import parse_dbc


OLD_DBC = """VERSION ""
BO_ 100 BCM_Status: 8 BCM
 SG_ VehicleSpeed : 0|16@1+ (0.01,0) [0|250] "km/h" ECM,IC
 SG_ IgnitionState : 16|2@1+ (1,0) [0|3] "" ECM
BA_ "GenMsgCycleTime" BO_ 100 10;
"""

NEW_DBC = """VERSION ""
BO_ 100 Body_Status: 8 BCM
 SG_ VehSpd : 0|16@1+ (0.01,0) [0|250] "km/h" ECM,IC
 SG_ IgnitionState : 16|2@1+ (1,0) [0|3] "" ECM
BA_ "GenMsgCycleTime" BO_ 100 10;
"""

MODIFIED_DBC = """VERSION ""
BO_ 100 BCM_Status: 8 BCM
 SG_ VehicleSpeed : 0|16@1+ (0.02,0) [0|250] "km/h" ECM,IC
 SG_ IgnitionState : 16|2@1+ (1,0) [0|3] "" ECM
BO_ 200 New_Message: 8 ECU
 SG_ NewSignal : 0|8@1+ (1,0) [0|255] "" Vector__XXX
"""


class ParserAndComparatorTests(unittest.TestCase):
    def test_parse_basic_dbc(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "Bus_A.dbc"
            path.write_text(OLD_DBC, encoding="utf-8")

            database = parse_dbc(path)

        message = database.messages["BCM_Status"]
        self.assertEqual(message.can_id, 100)
        self.assertEqual(message.dlc, 8)
        self.assertEqual(message.cycle_time_ms, 10)
        self.assertEqual(message.signals["VehicleSpeed"].factor, 0.01)

    def test_detects_message_and_signal_renames_structurally(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            old_folder = root / "old"
            new_folder = root / "new"
            old_folder.mkdir()
            new_folder.mkdir()
            (old_folder / "Bus_A.dbc").write_text(OLD_DBC, encoding="utf-8")
            (new_folder / "Bus_A.dbc").write_text(NEW_DBC, encoding="utf-8")

            result = DbcComparator().compare_folders(old_folder, new_folder)

        self.assertEqual(result.summary()["Messages Renamed"], 1)
        self.assertEqual(result.summary()["Signals Renamed"], 1)
        self.assertEqual(result.summary()["Messages Removed"], 0)
        self.assertEqual(result.summary()["Messages Added"], 0)

    def test_detects_renames_when_dbc_file_is_renamed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            old_folder = root / "old"
            new_folder = root / "new"
            old_folder.mkdir()
            new_folder.mkdir()
            (old_folder / "PCANv1.dbc").write_text(OLD_DBC, encoding="utf-8")
            (new_folder / "PCANv2.dbc").write_text(NEW_DBC, encoding="utf-8")

            result = DbcComparator().compare_folders(old_folder, new_folder)

        self.assertEqual(result.summary()["Messages Renamed"], 1)
        self.assertEqual(result.summary()["Signals Renamed"], 1)
        self.assertEqual(result.summary()["Messages Removed"], 0)
        self.assertEqual(result.summary()["Messages Added"], 0)
        self.assertEqual(result.message_changes[0].dbc_file, "PCANv1.dbc -> PCANv2.dbc")

    def test_detects_modified_and_added_items(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            old_folder = root / "old"
            new_folder = root / "new"
            old_folder.mkdir()
            new_folder.mkdir()
            (old_folder / "Bus_A.dbc").write_text(OLD_DBC, encoding="utf-8")
            (new_folder / "Bus_A.dbc").write_text(MODIFIED_DBC, encoding="utf-8")

            result = DbcComparator().compare_folders(old_folder, new_folder)

        self.assertEqual(result.summary()["Signals Modified"], 1)
        self.assertEqual(result.summary()["Messages Added"], 1)
        self.assertEqual(result.summary()["Signals Added"], 1)


if __name__ == "__main__":
    unittest.main()
