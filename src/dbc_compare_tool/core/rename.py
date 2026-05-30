from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Generic, Iterable, Protocol, TypeVar

from dbc_compare_tool.core.models import Message, Signal


T = TypeVar("T")


@dataclass(frozen=True)
class RenameMatch(Generic[T]):
    old: T
    new: T
    confidence: float
    reasons: tuple[str, ...]


class RenameDetector(Protocol[T]):
    threshold: float

    def score(self, old: T, new: T) -> tuple[float, tuple[str, ...]]:
        ...

    def match(self, old_items: Iterable[T], new_items: Iterable[T]) -> list[RenameMatch[T]]:
        ...


class GreedyRenameDetector(Generic[T]):
    threshold = 0.8

    def score(self, old: T, new: T) -> tuple[float, tuple[str, ...]]:
        raise NotImplementedError

    def match(self, old_items: Iterable[T], new_items: Iterable[T]) -> list[RenameMatch[T]]:
        candidates: list[RenameMatch[T]] = []
        for old in old_items:
            for new in new_items:
                confidence, reasons = self.score(old, new)
                if confidence >= self.threshold:
                    candidates.append(RenameMatch(old=old, new=new, confidence=confidence, reasons=reasons))

        candidates.sort(key=lambda item: item.confidence, reverse=True)
        matches: list[RenameMatch[T]] = []
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


class MessageRenameDetector(GreedyRenameDetector[Message]):
    threshold = 0.78

    def score(self, old: Message, new: Message) -> tuple[float, tuple[str, ...]]:
        score = 0.0
        reasons: list[str] = []
        if old.can_id == new.can_id:
            score += 0.35
            reasons.append("CAN ID matched")
        if old.dlc == new.dlc:
            score += 0.12
            reasons.append("DLC matched")
        if old.transmitter == new.transmitter:
            score += 0.08
            reasons.append("Transmitter matched")
        if old.cycle_time_ms is not None and old.cycle_time_ms == new.cycle_time_ms:
            score += 0.08
            reasons.append("Cycle time matched")
        if len(old.signals) == len(new.signals):
            score += 0.10
            reasons.append("Signal count matched")

        layout_score = _jaccard(old.signal_layout(), new.signal_layout())
        if layout_score:
            score += 0.22 * layout_score
            reasons.append(f"Signal layout {layout_score:.0%} matched")

        name_score = _name_similarity(old.name, new.name)
        score += 0.05 * name_score
        if name_score >= 0.5:
            reasons.append("Names are similar")

        return min(score, 1.0), tuple(reasons)


class SignalRenameDetector(GreedyRenameDetector[Signal]):
    threshold = 0.82

    def score(self, old: Signal, new: Signal) -> tuple[float, tuple[str, ...]]:
        score = 0.0
        reasons: list[str] = []
        weighted_checks = [
            (old.start_bit == new.start_bit, 0.18, "Start bit matched"),
            (old.length == new.length, 0.18, "Length matched"),
            (old.byte_order == new.byte_order, 0.10, "Byte order matched"),
            (old.is_signed == new.is_signed, 0.06, "Signedness matched"),
            (old.factor == new.factor, 0.12, "Factor matched"),
            (old.offset == new.offset, 0.12, "Offset matched"),
            (old.unit == new.unit, 0.08, "Unit matched"),
            (old.receivers == new.receivers, 0.11, "Receivers matched"),
        ]
        for matched, weight, reason in weighted_checks:
            if matched:
                score += weight
                reasons.append(reason)

        name_score = _name_similarity(old.name, new.name)
        score += 0.05 * name_score
        if name_score >= 0.5:
            reasons.append("Names are similar")
        return min(score, 1.0), tuple(reasons)


def _name_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, left.lower(), right.lower()).ratio()


def _jaccard(left: set[tuple[object, ...]], right: set[tuple[object, ...]]) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)

