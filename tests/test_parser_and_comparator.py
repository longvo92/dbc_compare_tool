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

RENAMED_AND_MIN_MAX_CHANGED_DBC = """VERSION ""
BO_ 100 Body_Status: 8 BCM
 SG_ VehSpd : 0|16@1+ (0.01,0) [7|260] "km/h" ECM,IC
 SG_ IgnitionState : 16|2@1+ (1,0) [0|3] "" ECM
BA_ "GenMsgCycleTime" BO_ 100 10;
"""

RENAMED_AND_DLC_CHANGED_DBC = """VERSION ""
BO_ 100 Body_Status: 6 BCM
 SG_ VehicleSpeed : 0|16@1+ (0.01,0) [0|250] "km/h" ECM,IC
 SG_ IgnitionState : 16|2@1+ (1,0) [0|3] "" ECM
BA_ "GenMsgCycleTime" BO_ 100 10;
"""

NAMESPACE_AND_ENV_DBC = """VERSION ""
NS_ :
    SG_
    BO_
BS_:
BU_: Vector__XXX BCM ECM IC
EV_ IgnitionEnv : 0 [0|1] "" 0 0 DUMMY_NODE_VECTOR0 Vector__XXX;
BO_ 100 BCM_Status: 8 BCM
 SG_ VehicleSpeed : 0|16@1+ (0.01,0) [0|250] "km/h" ECM,IC
"""

EXTENDED_MUX_DBC = """VERSION ""
BO_ 2147483912 EXT_MSG: 8 Vector__XXX
 SG_ Mode M : 0|4@1+ (1,0) [0|15] "" Vector__XXX
 SG_ BigEndianValue m1 : 8|8@0- (0.5,-1) [-1|127] "u" ECU1,ECU2
"""

MODIFIED_DBC = """VERSION ""
BO_ 100 BCM_Status: 8 BCM
 SG_ VehicleSpeed : 0|16@1+ (0.02,0) [0|250] "km/h" ECM,IC
 SG_ IgnitionState : 16|2@1+ (1,0) [0|3] "" ECM
BO_ 200 New_Message: 8 ECU
 SG_ NewSignal : 0|8@1+ (1,0) [0|255] "" Vector__XXX
"""

DIFFERENT_ID_DBC = """VERSION ""
BO_ 101 BCM_Status: 8 BCM
 SG_ VehicleSpeed : 0|16@1+ (0.01,0) [0|250] "km/h" ECM,IC
"""

DIFFERENT_BYTE_ORDER_SIGNAL_DBC = """VERSION ""
BO_ 100 BCM_Status: 8 BCM
 SG_ VehSpd : 0|16@0+ (0.01,0) [0|250] "km/h" ECM,IC
"""

DETAILED_MODIFIED_SIGNAL_DBC = """VERSION ""
BO_ 100 BCM_Status: 8 BCM
 SG_ VehicleSpeed : 8|8@0+ (0.02,1) [7|260] "mph" ECM,IC
 SG_ IgnitionState : 16|2@1+ (1,0) [0|3] "" ECM
BA_ "GenMsgCycleTime" BO_ 100 10;
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

    def test_parse_ignores_namespace_signals_before_messages_and_environment_variables(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "Bus_A.dbc"
            path.write_text(NAMESPACE_AND_ENV_DBC, encoding="utf-8")

            database = parse_dbc(path)

        self.assertIn("BCM_Status", database.messages)
        self.assertIn("VehicleSpeed", database.messages["BCM_Status"].signals)

    def test_parse_extended_frame_id_and_multiplexed_signals(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "Ext.dbc"
            path.write_text(EXTENDED_MUX_DBC, encoding="utf-8")

            database = parse_dbc(path)

        message = database.messages["EXT_MSG"]
        self.assertEqual(message.can_id, 264)
        self.assertTrue(message.is_extended_frame)
        self.assertTrue(message.signals["Mode"].is_multiplexer)
        muxed_signal = message.signals["BigEndianValue"]
        self.assertEqual(muxed_signal.byte_order, 0)
        self.assertEqual(muxed_signal.value_type, "signed")
        self.assertEqual(muxed_signal.multiplexer_ids, (1,))
        self.assertEqual(muxed_signal.multiplexer_signal, "Mode")

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

    def test_signal_rename_description_also_shows_changed_properties(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            old_folder = root / "old"
            new_folder = root / "new"
            old_folder.mkdir()
            new_folder.mkdir()
            (old_folder / "Bus_A.dbc").write_text(OLD_DBC, encoding="utf-8")
            (new_folder / "Bus_A.dbc").write_text(RENAMED_AND_MIN_MAX_CHANGED_DBC, encoding="utf-8")

            result = DbcComparator().compare_folders(old_folder, new_folder)

        renamed_signal = next(change for change in result.signal_changes if change.change_type == "Renamed")
        self.assertEqual(renamed_signal.old_name, "VehicleSpeed")
        self.assertEqual(renamed_signal.new_name, "VehSpd")
        self.assertIn("Signal Name: VehicleSpeed -> VehSpd", renamed_signal.description)
        self.assertIn("Min: 0 -> 7", renamed_signal.description)
        self.assertIn("Max: 250 -> 260", renamed_signal.description)
        self.assertEqual(result.summary()["Signals Renamed"], 1)
        self.assertEqual(result.summary()["Signals Removed"], 0)
        self.assertEqual(result.summary()["Signals Added"], 0)

    def test_message_rename_description_also_shows_changed_properties(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            old_folder = root / "old"
            new_folder = root / "new"
            old_folder.mkdir()
            new_folder.mkdir()
            (old_folder / "Bus_A.dbc").write_text(OLD_DBC, encoding="utf-8")
            (new_folder / "Bus_A.dbc").write_text(RENAMED_AND_DLC_CHANGED_DBC, encoding="utf-8")

            result = DbcComparator().compare_folders(old_folder, new_folder)

        renamed_message = next(change for change in result.message_changes if change.change_type == "Renamed")
        self.assertEqual(renamed_message.old_name, "BCM_Status")
        self.assertEqual(renamed_message.new_name, "Body_Status")
        self.assertIn("Message Name: BCM_Status -> Body_Status", renamed_message.description)
        self.assertIn("DLC: 8 -> 6", renamed_message.description)
        self.assertEqual(result.summary()["Messages Renamed"], 1)

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

    def test_message_rename_requires_same_frame_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            old_folder = root / "old"
            new_folder = root / "new"
            old_folder.mkdir()
            new_folder.mkdir()
            (old_folder / "Bus_A.dbc").write_text(OLD_DBC, encoding="utf-8")
            (new_folder / "Bus_A.dbc").write_text(DIFFERENT_ID_DBC, encoding="utf-8")

            result = DbcComparator().compare_folders(old_folder, new_folder)

        self.assertEqual(result.summary()["Messages Renamed"], 0)
        self.assertEqual(result.summary()["Messages Removed"], 1)
        self.assertEqual(result.summary()["Messages Added"], 1)

    def test_signal_rename_requires_same_byte_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            old_folder = root / "old"
            new_folder = root / "new"
            old_folder.mkdir()
            new_folder.mkdir()
            (old_folder / "Bus_A.dbc").write_text(OLD_DBC, encoding="utf-8")
            (new_folder / "Bus_A.dbc").write_text(DIFFERENT_BYTE_ORDER_SIGNAL_DBC, encoding="utf-8")

            result = DbcComparator().compare_folders(old_folder, new_folder)

        self.assertEqual(result.summary()["Messages Renamed"], 0)
        self.assertEqual(result.summary()["Signals Renamed"], 0)
        self.assertEqual(result.summary()["Signals Removed"], 2)
        self.assertEqual(result.summary()["Signals Added"], 1)

    def test_modified_signal_description_shows_detailed_old_to_new_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            old_folder = root / "old"
            new_folder = root / "new"
            old_folder.mkdir()
            new_folder.mkdir()
            (old_folder / "Bus_A.dbc").write_text(OLD_DBC, encoding="utf-8")
            (new_folder / "Bus_A.dbc").write_text(DETAILED_MODIFIED_SIGNAL_DBC, encoding="utf-8")

            result = DbcComparator().compare_folders(old_folder, new_folder)

        self.assertEqual(result.summary()["Signals Modified"], 1)
        description = result.signal_changes[0].description
        self.assertIn(
            "Layout changed: Start Bit: 0 -> 8, Length: 16 -> 8, "
            "Byte Order: Intel/little-endian (1) -> Motorola/big-endian (0)",
            description,
        )
        self.assertIn("Min: 0 -> 7", description)
        self.assertIn("Max: 250 -> 260", description)
        self.assertIn("Factor: 0.01 -> 0.02", description)
        self.assertIn("Offset: 0 -> 1", description)
        self.assertIn("Unit: km/h -> mph", description)


if __name__ == "__main__":
    unittest.main()
