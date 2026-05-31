from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from dbc_compare_tool.core.discovery import discover_dbc_pairs
from dbc_compare_tool.core.models import Change, ComparisonResult, DbcDatabase, Message, Signal
from dbc_compare_tool.core.parser import parse_dbc
from dbc_compare_tool.core.rename import MessageRenameDetector, SignalRenameDetector

FILE_RENAME_THRESHOLD = 0.55


@dataclass(frozen=True)
class _DatabaseCandidate:
    relative_path: str
    database: DbcDatabase


@dataclass(frozen=True)
class _DatabaseMatch:
    old: _DatabaseCandidate
    new: _DatabaseCandidate
    confidence: float
    reasons: tuple[str, ...]


class DbcComparator:
    def __init__(
        self,
        message_rename_detector: MessageRenameDetector | None = None,
        signal_rename_detector: SignalRenameDetector | None = None,
    ) -> None:
        self.message_rename_detector = message_rename_detector or MessageRenameDetector()
        self.signal_rename_detector = signal_rename_detector or SignalRenameDetector()

    def compare_folders(self, old_folder: Path, new_folder: Path) -> ComparisonResult:
        result = ComparisonResult()
        old_only: list[_DatabaseCandidate] = []
        new_only: list[_DatabaseCandidate] = []

        for pair in discover_dbc_pairs(old_folder, new_folder):
            if pair.old_path and pair.new_path:
                old_db = parse_dbc(pair.old_path)
                new_db = parse_dbc(pair.new_path)
                self.compare_databases(pair.relative_path, old_db, new_db, result)
            elif pair.old_path:
                old_only.append(_DatabaseCandidate(pair.relative_path, parse_dbc(pair.old_path)))
            elif pair.new_path:
                new_only.append(_DatabaseCandidate(pair.relative_path, parse_dbc(pair.new_path)))

        file_matches = _match_renamed_databases(old_only, new_only)
        matched_old = {id(match.old) for match in file_matches}
        matched_new = {id(match.new) for match in file_matches}

        for match in file_matches:
            self.compare_databases(
                _format_file_pair_label(match.old.relative_path, match.new.relative_path),
                match.old.database,
                match.new.database,
                result,
            )

        for candidate in old_only:
            if id(candidate) not in matched_old:
                self.compare_databases(
                    candidate.relative_path,
                    candidate.database,
                    DbcDatabase(path=Path(candidate.relative_path)),
                    result,
                )

        for candidate in new_only:
            if id(candidate) not in matched_new:
                self.compare_databases(
                    candidate.relative_path,
                    DbcDatabase(path=Path(candidate.relative_path)),
                    candidate.database,
                    result,
                )
        return result

    def compare_databases(
        self,
        dbc_file: str,
        old_db: DbcDatabase,
        new_db: DbcDatabase,
        result: ComparisonResult | None = None,
    ) -> ComparisonResult:
        result = result or ComparisonResult()

        common_names = sorted(set(old_db.messages) & set(new_db.messages))
        for name in common_names:
            old_message = old_db.messages[name]
            new_message = new_db.messages[name]
            description = _changed_properties(old_message.comparable_properties(), new_message.comparable_properties())
            if description:
                result.message_changes.append(
                    Change(
                        dbc_file=dbc_file,
                        change_type="Modified",
                        old_name=name,
                        new_name=name,
                        confidence=None,
                        description=description,
                        can_id=new_message.can_id,
                    )
                )
            self._compare_signals(dbc_file, old_message, new_message, result)

        unmatched_old = [message for name, message in old_db.messages.items() if name not in new_db.messages]
        unmatched_new = [message for name, message in new_db.messages.items() if name not in old_db.messages]

        rename_matches = self.message_rename_detector.match(unmatched_old, unmatched_new)
        renamed_old = {id(match.old) for match in rename_matches}
        renamed_new = {id(match.new) for match in rename_matches}
        for match in rename_matches:
            result.message_changes.append(
                Change(
                    dbc_file=dbc_file,
                    change_type="Renamed",
                    old_name=match.old.name,
                    new_name=match.new.name,
                    confidence=match.confidence,
                    description="; ".join(match.reasons),
                    can_id=match.new.can_id,
                )
            )
            self._compare_signals(dbc_file, match.old, match.new, result)

        for message in unmatched_old:
            if id(message) not in renamed_old:
                result.message_changes.append(
                    Change(dbc_file, "Removed", message.name, "", None, "Message removed", message.can_id)
                )
                self._append_all_signals(dbc_file, message, "Removed", result)

        for message in unmatched_new:
            if id(message) not in renamed_new:
                result.message_changes.append(
                    Change(dbc_file, "Added", "", message.name, None, "Message added", message.can_id)
                )
                self._append_all_signals(dbc_file, message, "Added", result)

        return result

    def _compare_signals(
        self,
        dbc_file: str,
        old_message: Message,
        new_message: Message,
        result: ComparisonResult,
    ) -> None:
        common_names = sorted(set(old_message.signals) & set(new_message.signals))
        parent_name = new_message.name
        for name in common_names:
            old_signal = old_message.signals[name]
            new_signal = new_message.signals[name]
            description = _changed_properties(old_signal.comparable_properties(), new_signal.comparable_properties())
            if description:
                result.signal_changes.append(
                    Change(dbc_file, "Modified", name, name, None, description, parent_message=parent_name)
                )

        unmatched_old = [signal for name, signal in old_message.signals.items() if name not in new_message.signals]
        unmatched_new = [signal for name, signal in new_message.signals.items() if name not in old_message.signals]

        rename_matches = self.signal_rename_detector.match(unmatched_old, unmatched_new)
        renamed_old = {id(match.old) for match in rename_matches}
        renamed_new = {id(match.new) for match in rename_matches}
        for match in rename_matches:
            result.signal_changes.append(
                Change(
                    dbc_file=dbc_file,
                    parent_message=parent_name,
                    change_type="Renamed",
                    old_name=match.old.name,
                    new_name=match.new.name,
                    confidence=match.confidence,
                    description="; ".join(match.reasons),
                )
            )

        for signal in unmatched_old:
            if id(signal) not in renamed_old:
                result.signal_changes.append(
                    Change(dbc_file, "Removed", signal.name, "", None, "Signal removed", parent_message=parent_name)
                )
        for signal in unmatched_new:
            if id(signal) not in renamed_new:
                result.signal_changes.append(
                    Change(dbc_file, "Added", "", signal.name, None, "Signal added", parent_message=parent_name)
                )

    def _append_all_signals(self, dbc_file: str, message: Message, change_type: str, result: ComparisonResult) -> None:
        for signal in message.signals.values():
            result.signal_changes.append(
                Change(
                    dbc_file=dbc_file,
                    parent_message=message.name,
                    change_type=change_type,
                    old_name=signal.name if change_type == "Removed" else "",
                    new_name=signal.name if change_type == "Added" else "",
                    confidence=None,
                    description=f"Signal {change_type.lower()} with parent message",
                )
            )


def _changed_properties(old: dict[str, object], new: dict[str, object]) -> str:
    changes: list[str] = []
    for key in sorted(set(old) | set(new)):
        old_value = old.get(key)
        new_value = new.get(key)
        if old_value != new_value:
            changes.append(f"{key} changed from {old_value!r} to {new_value!r}")
    return "; ".join(changes)


def _match_renamed_databases(
    old_candidates: list[_DatabaseCandidate],
    new_candidates: list[_DatabaseCandidate],
) -> list[_DatabaseMatch]:
    candidates: list[_DatabaseMatch] = []
    for old in old_candidates:
        for new in new_candidates:
            confidence, reasons = _score_database_pair(old, new)
            if confidence >= FILE_RENAME_THRESHOLD:
                candidates.append(_DatabaseMatch(old, new, confidence, reasons))

    candidates.sort(key=lambda item: item.confidence, reverse=True)
    matches: list[_DatabaseMatch] = []
    used_old: set[int] = set()
    used_new: set[int] = set()
    for candidate in candidates:
        old_id = id(candidate.old)
        new_id = id(candidate.new)
        if old_id in used_old or new_id in used_new:
            continue
        matches.append(candidate)
        used_old.add(old_id)
        used_new.add(new_id)
    return matches


def _score_database_pair(old: _DatabaseCandidate, new: _DatabaseCandidate) -> tuple[float, tuple[str, ...]]:
    old_messages = old.database.messages
    new_messages = new.database.messages
    if not old_messages or not new_messages:
        return 0.0, ()

    old_by_id = {message.can_id: message for message in old_messages.values()}
    new_by_id = {message.can_id: message for message in new_messages.values()}
    common_ids = set(old_by_id) & set(new_by_id)
    if not common_ids:
        return 0.0, ()

    reasons: list[str] = []
    score = 0.0

    id_overlap = len(common_ids) / max(len(old_by_id), len(new_by_id))
    score += 0.55 * id_overlap
    reasons.append(f"DBC CAN ID overlap {id_overlap:.0%}")

    name_overlap = len(set(old_messages) & set(new_messages)) / max(len(old_messages), len(new_messages))
    if name_overlap:
        score += 0.15 * name_overlap
        reasons.append(f"Message names overlap {name_overlap:.0%}")

    structure_score = _common_message_structure_score(old_by_id, new_by_id, common_ids)
    if structure_score:
        score += 0.25 * structure_score
        reasons.append(f"Common CAN ID structures {structure_score:.0%} matched")

    file_name_score = SequenceMatcher(None, old.relative_path.lower(), new.relative_path.lower()).ratio()
    score += 0.05 * file_name_score
    if file_name_score >= 0.5:
        reasons.append("DBC file names are similar")

    return min(score, 1.0), tuple(reasons)


def _common_message_structure_score(
    old_by_id: dict[int, Message],
    new_by_id: dict[int, Message],
    common_ids: set[int],
) -> float:
    message_scores: list[float] = []
    for can_id in common_ids:
        old = old_by_id[can_id]
        new = new_by_id[can_id]
        score = 0.0
        if old.dlc == new.dlc:
            score += 0.20
        if old.transmitter == new.transmitter:
            score += 0.15
        if old.cycle_time_ms == new.cycle_time_ms:
            score += 0.10
        if len(old.signals) == len(new.signals):
            score += 0.15
        score += 0.40 * _jaccard(old.signal_layout(), new.signal_layout())
        message_scores.append(score)
    return sum(message_scores) / len(message_scores)


def _format_file_pair_label(old_relative_path: str, new_relative_path: str) -> str:
    if old_relative_path == new_relative_path:
        return old_relative_path
    return f"{old_relative_path} -> {new_relative_path}"


def _jaccard(left: set[tuple[Any, ...]], right: set[tuple[Any, ...]]) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)
