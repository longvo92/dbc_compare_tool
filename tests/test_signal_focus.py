from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from dbc_compare_tool.core.models import DbcDatabase, Message, NodeSelection, Signal
from dbc_compare_tool.core.parser import parse_dbc
from dbc_compare_tool.core.signal_focus import (
    APP_PROPERTY_ORDER,
    NodeSelectionInput,
    _app_properties,
    collect_node_signals,
    compare_signal_focus,
    pair_databases,
    parse_watchlist,
)

APP_NODE = "AppEcu"


def make_signal(
    name: str,
    *,
    start_bit: int = 0,
    length: int = 8,
    factor: float = 1.0,
    offset: float = 0.0,
    minimum: float | None = 0.0,
    maximum: float | None = 255.0,
    unit: str = "",
    value_type: str = "unsigned",
    receivers: tuple[str, ...] = (APP_NODE,),
    value_descriptions: tuple[tuple[int, str], ...] = (),
    raw_initial: float | None = None,
    comment: str = "",
) -> Signal:
    return Signal(
        name=name,
        start_bit=start_bit,
        length=length,
        byte_order=1,
        value_type=value_type,
        is_signed=value_type == "signed",
        factor=factor,
        offset=offset,
        minimum=minimum,
        maximum=maximum,
        unit=unit,
        receivers=receivers,
        value_descriptions=value_descriptions,
        raw_initial=raw_initial,
        comment=comment,
    )


def make_db(*messages: Message, nodes: tuple[str, ...] = ()) -> DbcDatabase:
    database = DbcDatabase(path=Path("Bus_A.dbc"))
    for message in messages:
        database.messages[message.name] = message
    database.nodes = nodes or (APP_NODE, "OtherEcu")
    return database


def make_message(
    name: str,
    can_id: int,
    *signals: Signal,
    senders: tuple[str, ...] = ("OtherEcu",),
) -> Message:
    message = Message(
        name=name,
        can_id=can_id,
        dlc=8,
        transmitter=",".join(senders),
        senders=senders,
    )
    for signal in signals:
        message.signals[signal.name] = signal
    return message


def run_focus(old_db: DbcDatabase, new_db: DbcDatabase, watchlist: list[str] | None = None):
    selection = NodeSelection(
        dbc_file="Bus_A.dbc",
        old_path="Bus_A.dbc",
        new_path="Bus_A.dbc",
        old_node=APP_NODE,
        new_node=APP_NODE,
    )
    return compare_signal_focus(
        [NodeSelectionInput(selection=selection, old_db=old_db, new_db=new_db)],
        watchlist,
    )


def status_of(result, name: str) -> str:
    return next(row.status for row in result.rows if row.signal_name == name)


def row_of(result, name: str):
    return next(row for row in result.rows if row.signal_name == name)


class WatchlistParsingTests(unittest.TestCase):
    def test_strips_comments_blank_lines_and_duplicates(self):
        text = "\n".join([
            "# app signals",
            "VehicleSpeed",
            "",
            "  IgnitionState  // used by SWC_Power",
            "VEHICLESPEED",
            "GearPosition,uint8,Rx",
        ])
        self.assertEqual(
            parse_watchlist(text),
            ["VehicleSpeed", "IgnitionState", "GearPosition"],
        )

    def test_accepts_tab_separated_paste_and_quotes(self):
        text = 'BatterySoc\tPercent\t0-100\n"CoolantTemp";degC'
        self.assertEqual(parse_watchlist(text), ["BatterySoc", "CoolantTemp"])


class NodeScopeTests(unittest.TestCase):
    def test_collects_transmitted_and_received_signals_with_direction(self):
        database = make_db(
            make_message("Status", 0x100, make_signal("RxSignal"), senders=("OtherEcu",)),
            make_message(
                "Command",
                0x200,
                make_signal("TxSignal", receivers=("OtherEcu",)),
                senders=(APP_NODE,),
            ),
        )
        collected = collect_node_signals(database, APP_NODE, "Bus_A.dbc")
        self.assertEqual(collected["RxSignal"][0].direction, "Rx")
        self.assertEqual(collected["TxSignal"][0].direction, "Tx")

    def test_signals_of_other_nodes_are_ignored(self):
        database = make_db(
            make_message("Foreign", 0x300, make_signal("NotMine", receivers=("OtherEcu",)))
        )
        self.assertEqual(collect_node_signals(database, APP_NODE, "Bus_A.dbc"), {})


class SignalFocusStatusTests(unittest.TestCase):
    def test_signal_moved_to_another_message_is_not_removed(self):
        old_db = make_db(make_message("OldCarrier", 0x100, make_signal("VehicleSpeed")))
        new_db = make_db(make_message("NewCarrier", 0x321, make_signal("VehicleSpeed", start_bit=24)))

        row = row_of(run_focus(old_db, new_db), "VehicleSpeed")
        self.assertEqual(row.status, "Moved")
        self.assertEqual(row.property_diffs, ())
        self.assertIn("OldCarrier", row.note)
        self.assertIn("NewCarrier", row.note)

    def test_scaling_change_is_modified(self):
        old_db = make_db(make_message("Status", 0x100, make_signal("VehicleSpeed", factor=0.01)))
        new_db = make_db(make_message("Status", 0x100, make_signal("VehicleSpeed", factor=0.1)))

        row = row_of(run_focus(old_db, new_db), "VehicleSpeed")
        self.assertEqual(row.status, "Modified")
        self.assertEqual(row.property_diffs, (("Factor", "0.01", "0.1"),))

    def test_length_and_value_type_changes_are_modified(self):
        old_db = make_db(make_message("Status", 0x100, make_signal("Torque", length=8)))
        new_db = make_db(
            make_message("Status", 0x100, make_signal("Torque", length=16, value_type="signed"))
        )

        row = row_of(run_focus(old_db, new_db), "Torque")
        self.assertEqual(row.status, "Modified")
        self.assertEqual(
            dict((prop, (old, new)) for prop, old, new in row.property_diffs),
            {"Length": ("8", "16"), "Value Type": ("unsigned", "signed")},
        )

    def test_every_compared_property_reaches_the_diff(self):
        """`_app_properties` and `APP_PROPERTY_ORDER` have to stay in step.

        The diff is built by walking `APP_PROPERTY_ORDER`, so a property added
        to one and not the other is compared but never reported, or reported
        under a name that is never compared.
        """
        reference = _app_properties(make_signal("Any"))
        self.assertEqual(set(APP_PROPERTY_ORDER), set(reference))

    def test_unit_min_max_and_description_changes_are_reported(self):
        old_db = make_db(make_message("Status", 0x100, make_signal(
            "Level", unit="%", minimum=0.0, maximum=100.0, comment="State of charge.",
        )))
        new_db = make_db(make_message("Status", 0x100, make_signal(
            "Level", unit="percent", minimum=-10.0, maximum=110.0, comment="State of charge, extended.",
        )))

        row = row_of(run_focus(old_db, new_db), "Level")
        self.assertEqual(row.status, "Modified")
        self.assertEqual(
            {prop: (old, new) for prop, old, new in row.property_diffs},
            {
                "Min": ("0", "-10"),
                "Max": ("100", "110"),
                "Unit": ("%", "percent"),
                "Description": ("State of charge.", "State of charge, extended."),
            },
        )

    def test_initial_value_change_is_modified(self):
        old_db = make_db(make_message("Status", 0x100, make_signal("Soc", raw_initial=0)))
        new_db = make_db(make_message("Status", 0x100, make_signal("Soc", raw_initial=255)))

        row = row_of(run_focus(old_db, new_db), "Soc")
        self.assertEqual(row.status, "Modified")
        self.assertEqual(row.property_diffs, (("Initial Value", "0", "255"),))

    def test_start_bit_only_change_is_unchanged(self):
        old_db = make_db(make_message("Status", 0x100, make_signal("VehicleSpeed", start_bit=0)))
        new_db = make_db(make_message("Status", 0x100, make_signal("VehicleSpeed", start_bit=32)))

        self.assertEqual(status_of(run_focus(old_db, new_db), "VehicleSpeed"), "Unchanged")

    def test_value_table_diff_splits_relabel_add_and_remove(self):
        old_table = ((0, "Off"), (1, "On"), (2, "Reserved"))
        new_table = ((0, "Off"), (2, "Charging"), (3, "Fault"))
        old_db = make_db(
            make_message("Status", 0x100, make_signal("Mode", value_descriptions=old_table))
        )
        new_db = make_db(
            make_message("Status", 0x100, make_signal("Mode", value_descriptions=new_table))
        )

        row = row_of(run_focus(old_db, new_db), "Mode")
        self.assertEqual(row.status, "Modified")
        self.assertEqual(
            row.value_table_diffs,
            (
                ("1", "On", "", "Value Removed"),
                ("2", "Reserved", "Charging", "Relabeled"),
                ("3", "", "Fault", "Value Added"),
            ),
        )

    def test_direction_flip_is_reported(self):
        old_db = make_db(
            make_message("Status", 0x100, make_signal("Request"), senders=("OtherEcu",))
        )
        new_db = make_db(
            make_message(
                "Status",
                0x100,
                make_signal("Request", receivers=("OtherEcu",)),
                senders=(APP_NODE,),
            )
        )

        row = row_of(run_focus(old_db, new_db), "Request")
        self.assertEqual(row.status, "Direction Changed")
        self.assertIn("Rx -> Tx", row.note)

    def test_signal_dropped_from_node_but_kept_in_dbc_is_out_of_scope(self):
        old_db = make_db(make_message("Status", 0x100, make_signal("VehicleSpeed")))
        new_db = make_db(
            make_message("Status", 0x100, make_signal("VehicleSpeed", receivers=("OtherEcu",)))
        )

        row = row_of(run_focus(old_db, new_db), "VehicleSpeed")
        self.assertEqual(row.status, "Out Of Node Scope")
        self.assertIn("no longer sent to or from", row.note)

    def test_signal_gone_from_dbc_is_removed(self):
        old_db = make_db(make_message("Status", 0x100, make_signal("VehicleSpeed")))
        new_db = make_db(make_message("Status", 0x100, make_signal("Other")))

        self.assertEqual(status_of(run_focus(old_db, new_db), "VehicleSpeed"), "Removed")

    def test_removed_signal_points_at_an_identical_new_signal(self):
        old_db = make_db(make_message("Status", 0x100, make_signal("VehicleSpeed", factor=0.01)))
        new_db = make_db(make_message("Status", 0x100, make_signal("VehSpd", factor=0.01)))

        result = run_focus(old_db, new_db)
        removed = row_of(result, "VehicleSpeed")
        self.assertEqual(removed.status, "Removed")
        self.assertIn("Possibly renamed to: VehSpd", removed.note)

        added = row_of(result, "VehSpd")
        self.assertEqual(added.status, "Added")
        self.assertIn("Possibly renamed from: VehicleSpeed", added.note)

    def test_no_rename_hint_when_properties_differ(self):
        old_db = make_db(make_message("Status", 0x100, make_signal("VehicleSpeed", factor=0.01)))
        new_db = make_db(make_message("Status", 0x100, make_signal("VehSpd", factor=0.5)))

        self.assertNotIn("Possibly renamed", row_of(run_focus(old_db, new_db), "VehicleSpeed").note)

    def test_new_signal_is_added(self):
        old_db = make_db(make_message("Status", 0x100, make_signal("VehicleSpeed")))
        new_db = make_db(
            make_message("Status", 0x100, make_signal("VehicleSpeed"), make_signal("BatterySoc"))
        )

        self.assertEqual(status_of(run_focus(old_db, new_db), "BatterySoc"), "Added")

    def test_duplicate_name_with_different_properties_is_ambiguous(self):
        old_db = make_db(make_message("Status", 0x100, make_signal("Counter", length=4)))
        new_db = make_db(
            make_message("Status", 0x100, make_signal("Counter", length=4)),
            make_message("Extra", 0x101, make_signal("Counter", length=8)),
        )

        row = row_of(run_focus(old_db, new_db), "Counter")
        self.assertEqual(row.status, "Ambiguous")
        self.assertIn("Status", row.note)
        self.assertIn("Extra", row.note)

    def test_duplicate_name_with_identical_properties_is_merged(self):
        old_db = make_db(make_message("Status", 0x100, make_signal("Counter")))
        new_db = make_db(
            make_message("Status", 0x100, make_signal("Counter")),
            make_message("Extra", 0x101, make_signal("Counter")),
        )

        row = row_of(run_focus(old_db, new_db), "Counter")
        self.assertEqual(row.status, "Moved")
        self.assertIn("defined in 2 messages", row.note)


class WatchlistDrivenTests(unittest.TestCase):
    def test_unknown_watchlist_entry_is_reported_not_dropped(self):
        old_db = make_db(make_message("Status", 0x100, make_signal("VehicleSpeed")))
        new_db = make_db(make_message("Status", 0x100, make_signal("VehicleSpeed")))

        result = run_focus(old_db, new_db, ["VehicleSpeed", "TypoSignal"])
        self.assertEqual([row.signal_name for row in result.rows], ["VehicleSpeed", "TypoSignal"])
        self.assertEqual(status_of(result, "TypoSignal"), "Not In DBC")
        self.assertIn("check the spelling", row_of(result, "TypoSignal").note)

    def test_watchlist_order_is_preserved_and_limits_the_rows(self):
        old_db = make_db(
            make_message("Status", 0x100, make_signal("A"), make_signal("B"), make_signal("C"))
        )
        new_db = make_db(
            make_message("Status", 0x100, make_signal("A"), make_signal("B"), make_signal("C"))
        )

        result = run_focus(old_db, new_db, ["C", "A"])
        self.assertEqual([row.signal_name for row in result.rows], ["C", "A"])
        self.assertTrue(all(row.in_watchlist for row in result.rows))

    def test_empty_watchlist_audits_every_node_signal(self):
        old_db = make_db(make_message("Status", 0x100, make_signal("A"), make_signal("B")))
        new_db = make_db(make_message("Status", 0x100, make_signal("A"), make_signal("B")))

        result = run_focus(old_db, new_db)
        self.assertEqual([row.signal_name for row in result.rows], ["A", "B"])
        self.assertFalse(any(row.in_watchlist for row in result.rows))

    def test_case_insensitive_match_is_reported(self):
        old_db = make_db(make_message("Status", 0x100, make_signal("VehicleSpeed")))
        new_db = make_db(make_message("Status", 0x100, make_signal("VehicleSpeed")))

        row = row_of(run_focus(old_db, new_db, ["vehiclespeed"]), "vehiclespeed")
        self.assertEqual(row.status, "Unchanged")
        self.assertIn("case-insensitively", row.note)

    def test_summary_counts_only_actionable_statuses_as_needs_review(self):
        old_db = make_db(
            make_message("Status", 0x100, make_signal("Kept"), make_signal("Gone"))
        )
        new_db = make_db(make_message("Status", 0x100, make_signal("Kept")))

        summary = run_focus(old_db, new_db).summary()
        self.assertEqual(summary["Removed"], 1)
        self.assertEqual(summary["Unchanged"], 1)
        self.assertEqual(summary["Needs Review"], 1)
        self.assertEqual(summary["Total Signals"], 2)


class AddedOrRemovedDbcTests(unittest.TestCase):
    def test_missing_old_database_reports_every_signal_as_added(self):
        new_db = make_db(make_message("Status", 0x100, make_signal("VehicleSpeed")))
        selection = NodeSelection(
            dbc_file="Bus_A.dbc",
            old_path="",
            new_path="Bus_A.dbc",
            old_node="",
            new_node=APP_NODE,
        )
        result = compare_signal_focus(
            [NodeSelectionInput(selection=selection, old_db=None, new_db=new_db)]
        )
        self.assertEqual(status_of(result, "VehicleSpeed"), "Added")

    def test_signal_moving_between_two_dbc_files_is_moved(self):
        bus_a_old = make_db(make_message("Status", 0x100, make_signal("VehicleSpeed")))
        bus_a_new = make_db(make_message("Status", 0x100, make_signal("Other")))
        bus_b_old = make_db(make_message("Info", 0x400, make_signal("Other2")))
        bus_b_new = make_db(make_message("Info", 0x400, make_signal("VehicleSpeed")))

        inputs = [
            NodeSelectionInput(
                selection=NodeSelection("Bus_A.dbc", "Bus_A.dbc", "Bus_A.dbc", APP_NODE, APP_NODE),
                old_db=bus_a_old,
                new_db=bus_a_new,
            ),
            NodeSelectionInput(
                selection=NodeSelection("Bus_B.dbc", "Bus_B.dbc", "Bus_B.dbc", APP_NODE, APP_NODE),
                old_db=bus_b_old,
                new_db=bus_b_new,
            ),
        ]
        result = compare_signal_focus(inputs, ["VehicleSpeed"])
        self.assertEqual(status_of(result, "VehicleSpeed"), "Moved")


DBC_WITH_NODES = """VERSION ""

BU_: AppEcu OtherEcu Gateway

BO_ 256 Status: 8 OtherEcu
 SG_ VehicleSpeed : 0|16@1+ (0.01,0) [0|250] "km/h" AppEcu,Gateway

BA_DEF_ SG_  "GenSigStartValue" INT 0 65535;
BA_DEF_DEF_  "GenSigStartValue" 0;
BA_ "GenSigStartValue" SG_ 256 VehicleSpeed 500;
"""

DBC_WITHOUT_NODE_SECTION = """VERSION ""

BO_ 256 Status: 8 OtherEcu
 SG_ VehicleSpeed : 0|16@1+ (0.01,0) [0|250] "km/h" AppEcu,Gateway
"""

DBC_UNRELATED = """VERSION ""

BU_: Charger AppEcu

BO_ 999 ChargeState: 4 Charger
 SG_ ChargePower : 0|12@1+ (0.1,0) [0|400] "kW" AppEcu
"""


class PairDatabasesTests(unittest.TestCase):
    def _folders(self, old_files: dict[str, str], new_files: dict[str, str]):
        # unittest.TestCase.enterContext needs Python 3.11+; the repo supports 3.9.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for folder, files in (("old", old_files), ("new", new_files)):
            (root / folder).mkdir()
            for name, text in files.items():
                (root / folder / name).write_text(text, encoding="utf-8")
        return root / "old", root / "new"

    def test_same_path_files_are_matched_and_parsed(self):
        old_folder, new_folder = self._folders(
            {"Bus_A.dbc": DBC_WITH_NODES}, {"Bus_A.dbc": DBC_WITH_NODES}
        )
        pairs = pair_databases(old_folder, new_folder)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0].status, "Matched")
        self.assertEqual(pairs[0].old_db.nodes, ("AppEcu", "Gateway", "OtherEcu"))
        self.assertEqual(pairs[0].new_db.nodes, ("AppEcu", "Gateway", "OtherEcu"))

    def test_renamed_file_is_paired_by_content(self):
        old_folder, new_folder = self._folders(
            {"Bus_A.dbc": DBC_WITH_NODES}, {"Bus_A_v2.dbc": DBC_WITH_NODES}
        )
        pairs = pair_databases(old_folder, new_folder)
        self.assertEqual([pair.status for pair in pairs], ["DBC Renamed"])
        self.assertEqual(pairs[0].old_path, "Bus_A.dbc")
        self.assertEqual(pairs[0].new_path, "Bus_A_v2.dbc")

    def test_added_and_removed_files_keep_the_side_they_exist_on(self):
        # Unrelated content, so the rename matcher cannot pair the two files.
        old_folder, new_folder = self._folders(
            {"Gone.dbc": DBC_WITH_NODES}, {"Fresh.dbc": DBC_UNRELATED}
        )
        pairs = {pair.status: pair for pair in pair_databases(old_folder, new_folder)}
        self.assertEqual(set(pairs), {"DBC Removed", "DBC Added"})
        self.assertIsNone(pairs["DBC Removed"].new_db)
        self.assertIsNone(pairs["DBC Added"].old_db)

    def test_unparsable_file_is_flagged_and_does_not_stop_the_others(self):
        old_folder, new_folder = self._folders(
            {"Good.dbc": DBC_WITH_NODES, "Broken.dbc": "not a dbc at all"},
            {"Good.dbc": DBC_WITH_NODES, "Broken.dbc": "still not a dbc"},
        )
        pairs = {pair.dbc_file: pair.status for pair in pair_databases(old_folder, new_folder)}
        self.assertEqual(pairs["Broken.dbc"], "Parse Error")
        self.assertEqual(pairs["Good.dbc"], "Matched")


class ParserNodeTests(unittest.TestCase):
    def _parse(self, text: str):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sample.dbc"
            path.write_text(text, encoding="utf-8")
            return parse_dbc(path)

    def test_nodes_come_from_the_bu_section(self):
        database = self._parse(DBC_WITH_NODES)
        self.assertEqual(database.nodes, ("AppEcu", "Gateway", "OtherEcu"))

    def test_nodes_fall_back_to_senders_and_receivers(self):
        database = self._parse(DBC_WITHOUT_NODE_SECTION)
        self.assertEqual(database.nodes, ("AppEcu", "Gateway", "OtherEcu"))

    def test_senders_are_kept_as_a_list(self):
        database = self._parse(DBC_WITH_NODES)
        self.assertEqual(database.messages["Status"].senders, ("OtherEcu",))
        self.assertEqual(database.messages["Status"].transmitter, "OtherEcu")

    def test_initial_value_is_parsed(self):
        database = self._parse(DBC_WITH_NODES)
        signal = database.messages["Status"].signals["VehicleSpeed"]
        self.assertEqual(signal.raw_initial, 500.0)


if __name__ == "__main__":
    unittest.main()
