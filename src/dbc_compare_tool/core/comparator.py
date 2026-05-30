from __future__ import annotations

from pathlib import Path

from dbc_compare_tool.core.discovery import discover_dbc_pairs
from dbc_compare_tool.core.models import Change, ComparisonResult, DbcDatabase, Message, Signal
from dbc_compare_tool.core.parser import parse_dbc
from dbc_compare_tool.core.rename import MessageRenameDetector, SignalRenameDetector


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
        for pair in discover_dbc_pairs(old_folder, new_folder):
            old_db = parse_dbc(pair.old_path) if pair.old_path else DbcDatabase(path=Path(pair.relative_path))
            new_db = parse_dbc(pair.new_path) if pair.new_path else DbcDatabase(path=Path(pair.relative_path))
            self.compare_databases(pair.relative_path, old_db, new_db, result)
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

