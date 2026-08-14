from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def jaccard(left: set[tuple[Any, ...]], right: set[tuple[Any, ...]]) -> float:
    """Jaccard similarity of two sets. Two empty sets count as identical."""
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


@dataclass(frozen=True)
class Signal:
    name: str
    start_bit: int
    length: int
    byte_order: int
    value_type: str
    is_signed: bool
    factor: float
    offset: float
    minimum: float | None
    maximum: float | None
    unit: str
    receivers: tuple[str, ...]
    is_multiplexer: bool = False
    multiplexer_ids: tuple[int, ...] = ()
    multiplexer_signal: str | None = None
    value_descriptions: tuple[tuple[int, str], ...] = ()
    comment: str = ""
    raw_initial: float | None = None

    def comparable_properties(self) -> dict[str, Any]:
        return {
            "Start Bit": self.start_bit,
            "Length": self.length,
            "Byte Order": self.byte_order,
            "Value Type": self.value_type,
            "Signed": self.is_signed,
            "Factor": self.factor,
            "Offset": self.offset,
            "Minimum": self.minimum,
            "Maximum": self.maximum,
            "Unit": self.unit,
            "Receivers": self.receivers,
            "Multiplexer": self.is_multiplexer,
            "Multiplexer IDs": self.multiplexer_ids,
            "Multiplexer Signal": self.multiplexer_signal,
            "Value Descriptions": self.value_descriptions,
            "Description": self.comment,
        }

    def layout_key(self) -> tuple[Any, ...]:
        return (self.start_bit, self.length, self.byte_order)

    def signal_key(self) -> tuple[Any, ...]:
        return (self.start_bit, self.length)


@dataclass
class Message:
    name: str
    can_id: int
    dlc: int
    transmitter: str
    is_extended_frame: bool = False
    signals: dict[str, Signal] = field(default_factory=dict)
    cycle_time_ms: int | None = None
    comment: str = ""
    # Senders as a list; `transmitter` keeps the comma-joined form the
    # baseline comparison reports, which cannot be split back reliably.
    senders: tuple[str, ...] = ()

    def comparable_properties(self) -> dict[str, Any]:
        return {
            "CAN ID": self.can_id,
            "DLC": self.dlc,
            "Transmitter": self.transmitter,
            "Extended Frame": self.is_extended_frame,
            "Cycle Time": self.cycle_time_ms,
            "Signal Count": len(self.signals),
            "Description": self.comment,
        }

    def signal_layout(self) -> set[tuple[Any, ...]]:
        return {signal.layout_key() for signal in self.signals.values()}


@dataclass
class DbcDatabase:
    path: Path
    messages: dict[str, Message] = field(default_factory=dict)
    nodes: tuple[str, ...] = ()


@dataclass(frozen=True)
class FilePair:
    relative_path: str
    old_path: Path | None
    new_path: Path | None


@dataclass(frozen=True)
class FilePairSummary:
    dbc_file: str
    status: str  # "Matched" | "DBC Added" | "DBC Removed" | "DBC Renamed"
    old_path: str
    new_path: str
    pairing_confidence: float | None
    message_count_old: int
    message_count_new: int
    signal_count_old: int
    signal_count_new: int


@dataclass(frozen=True)
class Change:
    dbc_file: str
    change_type: str
    old_name: str
    new_name: str
    confidence: float | None
    description: str
    can_id: int | None = None
    parent_message: str = ""
    confidence_level: str = ""  # "High", "Medium", "Low", or ""
    property_diffs: tuple[tuple[str, str, str], ...] = ()  # (property_name, old_value, new_value)


@dataclass(frozen=True)
class SignalRef:
    """Where a signal sits, seen from one selected ECU node."""

    signal: Signal
    dbc_file: str
    message_name: str
    can_id: int
    direction: str  # "Tx" | "Rx" | "Tx/Rx"


@dataclass(frozen=True)
class NodeSelection:
    """One paired DBC plus the node picked on each side."""

    dbc_file: str
    old_path: str
    new_path: str
    old_node: str  # "" when the file exists on the new side only
    new_node: str  # "" when the file exists on the old side only


@dataclass(frozen=True)
class SignalFocusRow:
    signal_name: str
    status: str
    in_watchlist: bool
    old_refs: tuple[SignalRef, ...] = ()
    new_refs: tuple[SignalRef, ...] = ()
    property_diffs: tuple[tuple[str, str, str], ...] = ()
    value_table_diffs: tuple[tuple[str, str, str, str], ...] = ()  # raw, old label, new label, kind
    note: str = ""


@dataclass
class SignalFocusResult:
    selections: list[NodeSelection] = field(default_factory=list)
    rows: list[SignalFocusRow] = field(default_factory=list)
    watchlist_size: int = 0

    def summary(self) -> dict[str, int]:
        metrics = {status: 0 for status in SIGNAL_FOCUS_STATUSES}
        for row in self.rows:
            metrics[row.status] = metrics.get(row.status, 0) + 1
        metrics["Total Signals"] = len(self.rows)
        metrics["Needs Review"] = sum(
            metrics.get(status, 0) for status in SIGNAL_FOCUS_ATTENTION_STATUSES
        )
        return metrics


SIGNAL_FOCUS_STATUSES = (
    "Removed",
    "Modified",
    "Added",
    "Direction Changed",
    "Out Of Node Scope",
    "Ambiguous",
    "Not In DBC",
    "Moved",
    "Unchanged",
)

# Statuses an application-layer engineer has to act on: the signal is gone,
# its interpretation changed, or the tool cannot answer without a decision.
SIGNAL_FOCUS_ATTENTION_STATUSES = (
    "Removed",
    "Modified",
    "Direction Changed",
    "Out Of Node Scope",
    "Ambiguous",
    "Not In DBC",
)


@dataclass
class ComparisonResult:
    message_changes: list[Change] = field(default_factory=list)
    signal_changes: list[Change] = field(default_factory=list)
    file_pairs: list[FilePairSummary] = field(default_factory=list)

    def summary(self) -> dict[str, int]:
        metrics = {
            "Messages Added": 0,
            "Messages Removed": 0,
            "Messages Modified": 0,
            "Messages Renamed": 0,
            "Signals Added": 0,
            "Signals Removed": 0,
            "Signals Modified": 0,
            "Signals Renamed": 0,
        }
        for change in self.message_changes:
            key = f"Messages {change.change_type}"
            metrics[key] = metrics.get(key, 0) + 1
        for change in self.signal_changes:
            key = f"Signals {change.change_type}"
            metrics[key] = metrics.get(key, 0) + 1
        metrics["Total Changes"] = sum(metrics.values())
        return metrics
