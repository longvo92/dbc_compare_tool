from __future__ import annotations

import re
from pathlib import Path

from dbc_compare_tool.core.models import DbcDatabase, Message, Signal


MESSAGE_RE = re.compile(r"^BO_\s+(?P<id>\d+)\s+(?P<name>[A-Za-z0-9_]+)\s*:\s*(?P<dlc>\d+)\s+(?P<tx>\S+)")
SIGNAL_RE = re.compile(
    r"^\s*SG_\s+(?P<name>[A-Za-z0-9_]+)"
    r"(?:\s+(?P<mux>M|m\d+))?\s*:\s*"
    r"(?P<start>\d+)\|(?P<length>\d+)@(?P<byte_order>[01])(?P<sign>[+-])\s*"
    r"\((?P<factor>[-+0-9.eE]+),(?P<offset>[-+0-9.eE]+)\)\s*"
    r"\[(?P<min>[-+0-9.eE]+)\|(?P<max>[-+0-9.eE]+)\]\s*"
    r'"(?P<unit>[^"]*)"\s*(?P<receivers>.*)$'
)
CYCLE_TIME_RE = re.compile(r'^BA_\s+"GenMsgCycleTime"\s+BO_\s+(?P<id>\d+)\s+(?P<cycle>\d+)\s*;')


class DbcParseError(ValueError):
    pass


def parse_dbc(path: Path) -> DbcDatabase:
    database = DbcDatabase(path=path)
    current_message: Message | None = None
    messages_by_id: dict[int, Message] = {}

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        raise DbcParseError(f"Unable to read DBC file: {path}") from exc

    for line_number, line in enumerate(lines, start=1):
        message_match = MESSAGE_RE.match(line)
        if message_match:
            message = Message(
                name=message_match.group("name"),
                can_id=int(message_match.group("id")),
                dlc=int(message_match.group("dlc")),
                transmitter=message_match.group("tx"),
            )
            database.messages[message.name] = message
            messages_by_id[message.can_id] = message
            current_message = message
            continue

        signal_match = SIGNAL_RE.match(line)
        if signal_match and current_message is not None:
            signal = _parse_signal(signal_match)
            current_message.signals[signal.name] = signal
            continue

        cycle_match = CYCLE_TIME_RE.match(line)
        if cycle_match:
            message = messages_by_id.get(int(cycle_match.group("id")))
            if message is not None:
                message.cycle_time_ms = int(cycle_match.group("cycle"))
            continue

        if line.lstrip().startswith("SG_") and current_message is None:
            raise DbcParseError(f"Signal found before message in {path} at line {line_number}")

    return database


def _parse_signal(match: re.Match[str]) -> Signal:
    receivers_text = match.group("receivers").strip()
    receivers = tuple(part.strip() for part in receivers_text.split(",") if part.strip())
    return Signal(
        name=match.group("name"),
        start_bit=int(match.group("start")),
        length=int(match.group("length")),
        byte_order=int(match.group("byte_order")),
        is_signed=match.group("sign") == "-",
        factor=float(match.group("factor")),
        offset=float(match.group("offset")),
        minimum=float(match.group("min")),
        maximum=float(match.group("max")),
        unit=match.group("unit"),
        receivers=receivers,
    )

