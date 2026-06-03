from __future__ import annotations

from pathlib import Path
from typing import Any

import cantools.database
from cantools.database.errors import UnsupportedDatabaseFormatError

from dbc_compare_tool.core.models import DbcDatabase, Message, Signal


EXTENDED_FRAME_FLAG = 0x80000000
FRAME_ID_MASK = 0x1FFFFFFF
LEGACY_CYCLE_TIME_DEFINITION = 'BA_DEF_ BO_ "GenMsgCycleTime" INT 0 65535;\n'


class DbcParseError(ValueError):
    pass


def parse_dbc(path: Path) -> DbcDatabase:
    try:
        cantools_db = _load_cantools_database(path)
    except OSError as exc:
        raise DbcParseError(f"Unable to read DBC file: {path}") from exc
    except UnsupportedDatabaseFormatError as exc:
        raise DbcParseError(f"Unable to parse DBC file: {path}: {exc}") from exc

    database = DbcDatabase(path=path)
    for cantools_message in getattr(cantools_db, "messages", []):
        message = _map_message(cantools_message)
        database.messages[message.name] = message
    return database


def _load_cantools_database(path: Path) -> Any:
    try:
        return cantools.database.load_file(
            path,
            database_format="dbc",
            encoding="utf-8",
            strict=False,
            sort_signals=None,
        )
    except UnsupportedDatabaseFormatError as exc:
        if "GenMsgCycleTime" not in str(exc):
            raise

        text = path.read_text(encoding="utf-8", errors="replace")
        if 'BA_DEF_ BO_ "GenMsgCycleTime"' not in text:
            text = LEGACY_CYCLE_TIME_DEFINITION + text
        return cantools.database.load_string(
            text,
            database_format="dbc",
            strict=False,
            sort_signals=None,
        )


def _map_message(cantools_message: Any) -> Message:
    message = Message(
        name=cantools_message.name,
        can_id=_normalize_frame_id(cantools_message.frame_id),
        dlc=cantools_message.length,
        transmitter=_format_senders(cantools_message.senders),
        is_extended_frame=bool(cantools_message.is_extended_frame),
        cycle_time_ms=cantools_message.cycle_time,
    )
    for cantools_signal in cantools_message.signals:
        signal = _map_signal(cantools_signal)
        message.signals[signal.name] = signal
    return message


def _map_signal(cantools_signal: Any) -> Signal:
    return Signal(
        name=cantools_signal.name,
        start_bit=cantools_signal.start,
        length=cantools_signal.length,
        byte_order=_map_byte_order(cantools_signal.byte_order),
        value_type=_map_value_type(cantools_signal),
        is_signed=bool(cantools_signal.is_signed),
        factor=float(cantools_signal.scale),
        offset=float(cantools_signal.offset),
        minimum=cantools_signal.minimum,
        maximum=cantools_signal.maximum,
        unit=cantools_signal.unit or "",
        receivers=tuple(cantools_signal.receivers or ()),
        is_multiplexer=bool(cantools_signal.is_multiplexer),
        multiplexer_ids=tuple(cantools_signal.multiplexer_ids or ()),
        multiplexer_signal=cantools_signal.multiplexer_signal,
    )


def _normalize_frame_id(frame_id: int) -> int:
    if frame_id & EXTENDED_FRAME_FLAG:
        return frame_id & FRAME_ID_MASK
    return frame_id


def _map_byte_order(byte_order: str) -> int:
    return 1 if byte_order == "little_endian" else 0


def _map_value_type(cantools_signal: Any) -> str:
    if getattr(cantools_signal, "is_float", False):
        return "float"
    return "signed" if cantools_signal.is_signed else "unsigned"


def _format_senders(senders: list[str] | tuple[str, ...]) -> str:
    return ",".join(senders) if senders else "Vector__XXX"
