"""Signal-focused comparison for AUTOSAR application-layer work.

The baseline comparison in :mod:`dbc_compare_tool.core.comparator` is
message-centric: signals are matched inside the message that carries them, so
moving a signal to another frame reads as a removal plus an addition.

An application-layer SWC does not see frames. It reads and writes signals
through the RTE, and only the signal contract matters: width, value type,
scaling, range, unit, value table, init value, and whether the ECU sends or
receives it. This module compares exactly that contract, keyed by signal name
within one selected ECU node per DBC file, and treats frame layout, CAN ID,
DLC, cycle time and byte order as transport details that never make a signal
"modified".
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dbc_compare_tool.core.comparator import DatabaseCandidate, match_renamed_databases
from dbc_compare_tool.core.discovery import discover_dbc_pairs
from dbc_compare_tool.core.models import (
    DbcDatabase,
    NodeSelection,
    Signal,
    SignalFocusResult,
    SignalFocusRow,
    SignalRef,
)
from dbc_compare_tool.core.parser import DbcParseError, parse_dbc

# Properties the application layer is contractually bound to. Byte order is
# deliberately absent: bit packing is the COM layer's problem, and reporting it
# would bury real findings under endianness churn.
APP_PROPERTY_ORDER = (
    "Length",
    "Value Type",
    "Factor",
    "Offset",
    "Min",
    "Max",
    "Unit",
    "Initial Value",
    "Description",
)

_SKIP_NODE = ""
_LIST_SEPARATORS = re.compile(r"[,;\t|]")


@dataclass(frozen=True)
class NodeSelectionInput:
    """A paired DBC with both databases already parsed."""

    selection: NodeSelection
    old_db: DbcDatabase | None
    new_db: DbcDatabase | None


@dataclass(frozen=True)
class PairedDatabases:
    """One old/new DBC pair, parsed, ready for the user to pick nodes on."""

    dbc_file: str
    status: str  # "Matched" | "DBC Renamed" | "DBC Added" | "DBC Removed" | "Parse Error"
    old_path: str
    new_path: str
    old_db: DbcDatabase | None
    new_db: DbcDatabase | None


def pair_databases(
    old_folder: Path,
    new_folder: Path,
    progress_callback: Callable[[str], None] | None = None,
) -> list[PairedDatabases]:
    """Discover and pair the DBC files of two baseline folders.

    Uses the same pairing rules as the baseline comparison — relative path
    first, then CAN ID and structure overlap for renamed files — so both tabs
    agree on what "the same DBC" means.
    """
    def report(message: str) -> None:
        if progress_callback:
            progress_callback(message)

    paired: list[PairedDatabases] = []
    old_only: list[DatabaseCandidate] = []
    new_only: list[DatabaseCandidate] = []

    for pair in discover_dbc_pairs(old_folder, new_folder):
        try:
            old_db = parse_dbc(pair.old_path) if pair.old_path else None
            new_db = parse_dbc(pair.new_path) if pair.new_path else None
        except DbcParseError as exc:
            report(f"Parse error, skipped: {pair.relative_path} ({exc})")
            paired.append(PairedDatabases(
                dbc_file=pair.relative_path,
                status="Parse Error",
                old_path=pair.relative_path if pair.old_path else "",
                new_path=pair.relative_path if pair.new_path else "",
                old_db=None,
                new_db=None,
            ))
            continue

        if old_db is not None and new_db is not None:
            report(f"Paired: {pair.relative_path}")
            paired.append(PairedDatabases(
                dbc_file=pair.relative_path,
                status="Matched",
                old_path=pair.relative_path,
                new_path=pair.relative_path,
                old_db=old_db,
                new_db=new_db,
            ))
        elif old_db is not None:
            old_only.append(DatabaseCandidate(pair.relative_path, old_db))
        elif new_db is not None:
            new_only.append(DatabaseCandidate(pair.relative_path, new_db))

    matches = match_renamed_databases(old_only, new_only)
    matched_old = {id(match.old) for match in matches}
    matched_new = {id(match.new) for match in matches}

    for match in matches:
        label = f"{match.old.relative_path} -> {match.new.relative_path}"
        report(f"Paired renamed DBC: {label}")
        paired.append(PairedDatabases(
            dbc_file=label,
            status="DBC Renamed",
            old_path=match.old.relative_path,
            new_path=match.new.relative_path,
            old_db=match.old.database,
            new_db=match.new.database,
        ))

    for candidate in old_only:
        if id(candidate) in matched_old:
            continue
        report(f"DBC removed: {candidate.relative_path}")
        paired.append(PairedDatabases(
            dbc_file=candidate.relative_path,
            status="DBC Removed",
            old_path=candidate.relative_path,
            new_path="",
            old_db=candidate.database,
            new_db=None,
        ))

    for candidate in new_only:
        if id(candidate) in matched_new:
            continue
        report(f"DBC added: {candidate.relative_path}")
        paired.append(PairedDatabases(
            dbc_file=candidate.relative_path,
            status="DBC Added",
            old_path="",
            new_path=candidate.relative_path,
            old_db=None,
            new_db=candidate.database,
        ))

    return paired


def list_nodes(database: DbcDatabase | None) -> tuple[str, ...]:
    return () if database is None else database.nodes


def parse_watchlist(text: str) -> list[str]:
    """Signal names from a pasted block or an imported .txt file.

    Tolerates what engineers actually paste: comment lines, blank lines,
    trailing comments, and rows copied out of Excel or a CSV where the signal
    name is the first column. Duplicates collapse, input order is kept.
    """
    names: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].split("//", 1)[0].strip()
        if not line:
            continue
        name = _LIST_SEPARATORS.split(line, 1)[0].strip().strip('"').strip("'")
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        names.append(name)
    return names


def collect_node_signals(
    database: DbcDatabase | None,
    node: str,
    dbc_file: str,
) -> dict[str, list[SignalRef]]:
    """Every signal the given node sends or receives, keyed by signal name."""
    collected: dict[str, list[SignalRef]] = {}
    if database is None or node == _SKIP_NODE:
        return collected

    for message in database.messages.values():
        sends = node in message.senders
        for signal in message.signals.values():
            receives = node in signal.receivers
            if not sends and not receives:
                continue
            direction = "Tx/Rx" if sends and receives else ("Tx" if sends else "Rx")
            collected.setdefault(signal.name, []).append(
                SignalRef(
                    signal=signal,
                    dbc_file=dbc_file,
                    message_name=message.name,
                    can_id=message.can_id,
                    direction=direction,
                )
            )
    return collected


def collect_all_signal_names(database: DbcDatabase | None) -> set[str]:
    if database is None:
        return set()
    return {
        signal.name
        for message in database.messages.values()
        for signal in message.signals.values()
    }


def compare_signal_focus(
    inputs: list[NodeSelectionInput],
    watchlist: list[str] | None = None,
) -> SignalFocusResult:
    """Compare the selected nodes signal by signal.

    With a watchlist, one row per requested signal is produced in the order the
    list was given, so the report can be read against the application's own
    signal list. Without one, every signal of the selected nodes is audited.
    """
    watchlist = watchlist or []

    old_scope: dict[str, list[SignalRef]] = {}
    new_scope: dict[str, list[SignalRef]] = {}
    old_all: set[str] = set()
    new_all: set[str] = set()

    for item in inputs:
        label = item.selection.dbc_file
        _merge_refs(old_scope, collect_node_signals(item.old_db, item.selection.old_node, label))
        _merge_refs(new_scope, collect_node_signals(item.new_db, item.selection.new_node, label))
        old_all |= collect_all_signal_names(item.old_db)
        new_all |= collect_all_signal_names(item.new_db)

    if watchlist:
        requested = [(name, True) for name in watchlist]
    else:
        requested = [(name, False) for name in sorted(set(old_scope) | set(new_scope))]

    old_orphans = {name: refs for name, refs in old_scope.items() if name not in new_scope}
    new_orphans = {name: refs for name, refs in new_scope.items() if name not in old_scope}

    result = SignalFocusResult(
        selections=[item.selection for item in inputs],
        watchlist_size=len(watchlist),
    )
    for name, in_watchlist in requested:
        result.rows.append(
            _build_row(
                name,
                in_watchlist,
                old_scope,
                new_scope,
                old_all,
                new_all,
                old_orphans,
                new_orphans,
            )
        )
    return result


def _rename_candidates(
    signal: Signal,
    orphans: dict[str, list[SignalRef]],
    exclude: str,
) -> list[str]:
    """Signals on the other side that carry the exact same application contract.

    A renamed signal breaks the application either way, so this never changes
    the status — it only saves the engineer from grepping the whole DBC to find
    what the signal became.
    """
    reference = _app_properties(signal)
    return sorted(
        name
        for name, refs in orphans.items()
        if name != exclude and _app_properties(refs[0].signal) == reference
    )


def _merge_refs(target: dict[str, list[SignalRef]], addition: dict[str, list[SignalRef]]) -> None:
    for name, refs in addition.items():
        target.setdefault(name, []).extend(refs)


def _build_row(
    name: str,
    in_watchlist: bool,
    old_scope: dict[str, list[SignalRef]],
    new_scope: dict[str, list[SignalRef]],
    old_all: set[str],
    new_all: set[str],
    old_orphans: dict[str, list[SignalRef]],
    new_orphans: dict[str, list[SignalRef]],
) -> SignalFocusRow:
    notes: list[str] = []

    old_key = _resolve_name(name, old_scope)
    new_key = _resolve_name(name, new_scope)
    if (old_key and old_key != name) or (new_key and new_key != name):
        notes.append(f"Matched case-insensitively ({old_key or '-'} / {new_key or '-'})")

    old_refs = tuple(old_scope.get(old_key, ())) if old_key else ()
    new_refs = tuple(new_scope.get(new_key, ())) if new_key else ()

    if not old_refs and not new_refs:
        return SignalFocusRow(
            signal_name=name,
            status="Not In DBC",
            in_watchlist=in_watchlist,
            note=_join_notes(notes + [_out_of_scope_note(name, old_all, new_all)]),
        )

    ambiguous_side = _ambiguity_note(old_refs, new_refs)
    if ambiguous_side:
        return SignalFocusRow(
            signal_name=name,
            status="Ambiguous",
            in_watchlist=in_watchlist,
            old_refs=old_refs,
            new_refs=new_refs,
            note=_join_notes(notes + [ambiguous_side]),
        )

    if old_refs and len(old_refs) > 1:
        notes.append(f"Old: defined in {len(old_refs)} messages ({_locations(old_refs)})")
    if new_refs and len(new_refs) > 1:
        notes.append(f"New: defined in {len(new_refs)} messages ({_locations(new_refs)})")

    if not old_refs:
        if _resolve_name_in(name, old_all):
            notes.append("Present in the old baseline but not routed to the selected node")
        candidates = _rename_candidates(new_refs[0].signal, old_orphans, name)
        if candidates:
            notes.append(f"Possibly renamed from: {', '.join(candidates)} (same properties)")
        return SignalFocusRow(
            signal_name=name,
            status="Added",
            in_watchlist=in_watchlist,
            new_refs=new_refs,
            note=_join_notes(notes),
        )

    if not new_refs:
        if _resolve_name_in(name, new_all):
            notes.append("Still in the new DBC, but no longer sent to or from the selected node")
            status = "Out Of Node Scope"
        else:
            status = "Removed"
            candidates = _rename_candidates(old_refs[0].signal, new_orphans, name)
            if candidates:
                notes.append(f"Possibly renamed to: {', '.join(candidates)} (same properties)")
        return SignalFocusRow(
            signal_name=name,
            status=status,
            in_watchlist=in_watchlist,
            old_refs=old_refs,
            note=_join_notes(notes),
        )

    old_signal = old_refs[0].signal
    new_signal = new_refs[0].signal
    property_diffs = _app_property_diffs(old_signal, new_signal)
    value_table_diffs = _value_table_diffs(old_signal, new_signal)

    old_direction = _merged_direction(old_refs)
    new_direction = _merged_direction(new_refs)
    direction_changed = old_direction != new_direction
    if direction_changed:
        notes.append(f"Direction {old_direction} -> {new_direction}")

    moved_note = _moved_note(old_refs, new_refs)

    if property_diffs or value_table_diffs:
        status = "Modified"
        if moved_note:
            notes.append(moved_note)
    elif direction_changed:
        status = "Direction Changed"
        if moved_note:
            notes.append(moved_note)
    elif moved_note:
        status = "Moved"
        notes.append(moved_note)
    else:
        status = "Unchanged"

    return SignalFocusRow(
        signal_name=name,
        status=status,
        in_watchlist=in_watchlist,
        old_refs=old_refs,
        new_refs=new_refs,
        property_diffs=property_diffs,
        value_table_diffs=value_table_diffs,
        note=_join_notes(notes),
    )


def _resolve_name(name: str, scope: dict[str, list[SignalRef]]) -> str:
    if name in scope:
        return name
    lowered = name.lower()
    for candidate in scope:
        if candidate.lower() == lowered:
            return candidate
    return ""


def _resolve_name_in(name: str, names: set[str]) -> str:
    if name in names:
        return name
    lowered = name.lower()
    for candidate in names:
        if candidate.lower() == lowered:
            return candidate
    return ""


def _out_of_scope_note(name: str, old_all: set[str], new_all: set[str]) -> str:
    in_old = bool(_resolve_name_in(name, old_all))
    in_new = bool(_resolve_name_in(name, new_all))
    if in_old and in_new:
        return "Exists in both DBC files but in neither selected node"
    if in_new:
        return "Exists in the new DBC but not in the selected node"
    if in_old:
        return "Exists in the old DBC but not in the selected node"
    return "Not found in any compared DBC — check the spelling in the signal list"


def _ambiguity_note(old_refs: tuple[SignalRef, ...], new_refs: tuple[SignalRef, ...]) -> str:
    for label, refs in (("old", old_refs), ("new", new_refs)):
        if len(refs) < 2:
            continue
        first = _app_properties(refs[0].signal)
        if any(_app_properties(ref.signal) != first for ref in refs[1:]):
            return (
                f"Same name defined more than once on the {label} side with different "
                f"properties ({_locations(refs)}) — pick the intended one manually"
            )
    return ""


def _locations(refs: tuple[SignalRef, ...]) -> str:
    return ", ".join(f"{ref.dbc_file}:{ref.message_name}" for ref in refs)


def _merged_direction(refs: tuple[SignalRef, ...]) -> str:
    directions = {ref.direction for ref in refs}
    if directions == {"Tx"}:
        return "Tx"
    if directions == {"Rx"}:
        return "Rx"
    return "Tx/Rx"


def _moved_note(old_refs: tuple[SignalRef, ...], new_refs: tuple[SignalRef, ...]) -> str:
    old_places = {(ref.message_name, ref.can_id) for ref in old_refs}
    new_places = {(ref.message_name, ref.can_id) for ref in new_refs}
    if old_places == new_places:
        return ""
    return (
        f"Carrier changed: {_format_places(old_places)} -> {_format_places(new_places)} "
        "(application interface unaffected)"
    )


def _format_places(places: set[tuple[str, int]]) -> str:
    return ", ".join(f"{name} (0x{can_id:X})" for name, can_id in sorted(places))


def _app_properties(signal: Signal) -> dict[str, Any]:
    return {
        "Length": signal.length,
        "Value Type": signal.value_type,
        "Factor": signal.factor,
        "Offset": signal.offset,
        "Min": signal.minimum,
        "Max": signal.maximum,
        "Unit": signal.unit,
        "Initial Value": signal.raw_initial,
        "Description": signal.comment,
    }


def _app_property_diffs(old_signal: Signal, new_signal: Signal) -> tuple[tuple[str, str, str], ...]:
    old = _app_properties(old_signal)
    new = _app_properties(new_signal)
    return tuple(
        (key, format_app_value(old[key]), format_app_value(new[key]))
        for key in APP_PROPERTY_ORDER
        if old[key] != new[key]
    )


def _value_table_diffs(
    old_signal: Signal,
    new_signal: Signal,
) -> tuple[tuple[str, str, str, str], ...]:
    """Per-entry VAL_ diff.

    A relabelled raw value is the dangerous case: existing application code
    still compiles and still reads the same number, but the number now means
    something else.
    """
    old_table = dict(old_signal.value_descriptions)
    new_table = dict(new_signal.value_descriptions)
    diffs: list[tuple[str, str, str, str]] = []
    for raw in sorted(set(old_table) | set(new_table)):
        old_label = old_table.get(raw)
        new_label = new_table.get(raw)
        if old_label == new_label:
            continue
        if old_label is None:
            kind = "Value Added"
        elif new_label is None:
            kind = "Value Removed"
        else:
            kind = "Relabeled"
        diffs.append((str(raw), old_label or "", new_label or "", kind))
    return tuple(diffs)


def format_app_value(value: Any) -> str:
    if value is None:
        return "blank"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float):
        return f"{value:g}"
    if isinstance(value, tuple):
        return ", ".join(str(item) for item in value) if value else "blank"
    text = str(value)
    return text if text else "blank"


def format_value_table(signal: Signal | None) -> str:
    if signal is None or not signal.value_descriptions:
        return ""
    return ", ".join(f"{raw}={label}" for raw, label in signal.value_descriptions)


def _join_notes(notes: list[str]) -> str:
    return "\n".join(note for note in notes if note)
