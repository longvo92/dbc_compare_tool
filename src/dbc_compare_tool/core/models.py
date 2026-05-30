from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Signal:
    name: str
    start_bit: int
    length: int
    byte_order: int
    is_signed: bool
    factor: float
    offset: float
    minimum: float | None
    maximum: float | None
    unit: str
    receivers: tuple[str, ...]

    def comparable_properties(self) -> dict[str, Any]:
        return {
            "Start Bit": self.start_bit,
            "Length": self.length,
            "Byte Order": self.byte_order,
            "Signed": self.is_signed,
            "Factor": self.factor,
            "Offset": self.offset,
            "Minimum": self.minimum,
            "Maximum": self.maximum,
            "Unit": self.unit,
            "Receivers": self.receivers,
        }

    def layout_key(self) -> tuple[Any, ...]:
        return (
            self.start_bit,
            self.length,
            self.byte_order,
            self.is_signed,
            self.factor,
            self.offset,
            self.unit,
            self.receivers,
        )


@dataclass
class Message:
    name: str
    can_id: int
    dlc: int
    transmitter: str
    signals: dict[str, Signal] = field(default_factory=dict)
    cycle_time_ms: int | None = None

    def comparable_properties(self) -> dict[str, Any]:
        return {
            "CAN ID": self.can_id,
            "DLC": self.dlc,
            "Transmitter": self.transmitter,
            "Cycle Time": self.cycle_time_ms,
            "Signal Count": len(self.signals),
        }

    def signal_layout(self) -> set[tuple[Any, ...]]:
        return {signal.layout_key() for signal in self.signals.values()}


@dataclass
class DbcDatabase:
    path: Path
    messages: dict[str, Message] = field(default_factory=dict)


@dataclass(frozen=True)
class FilePair:
    relative_path: str
    old_path: Path | None
    new_path: Path | None


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


@dataclass
class ComparisonResult:
    message_changes: list[Change] = field(default_factory=list)
    signal_changes: list[Change] = field(default_factory=list)

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
            metrics[f"Messages {change.change_type}"] += 1
        for change in self.signal_changes:
            metrics[f"Signals {change.change_type}"] += 1
        metrics["Total Changes"] = sum(metrics.values())
        return metrics

