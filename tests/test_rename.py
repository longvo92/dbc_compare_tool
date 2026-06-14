"""Unit tests for rename detection logic."""

import unittest

from dbc_compare_tool.core.models import Message, Signal
from dbc_compare_tool.core.rename import (
    EventMessageDetector,
    MessageRenameDetector,
    SignalRenameDetector,
)


def _make_signal(name: str, start_bit: int = 0, length: int = 8, **kwargs) -> Signal:
    defaults = dict(
        byte_order=1, value_type="unsigned", is_signed=False,
        factor=1.0, offset=0.0, minimum=0.0, maximum=255.0,
        unit="", receivers=(),
    )
    defaults.update(kwargs)
    return Signal(name=name, start_bit=start_bit, length=length, **defaults)


def _make_message(name: str, can_id: int, signals: dict[str, Signal] | None = None) -> Message:
    return Message(name=name, can_id=can_id, dlc=8, transmitter="ECU", signals=signals or {})


class TestSignalRenameDetector(unittest.TestCase):
    def setUp(self):
        self.detector = SignalRenameDetector()

    def test_identical_layout_matches(self):
        old = _make_signal("EngineTemp", start_bit=16, length=8)
        new = _make_signal("CoolantTemp", start_bit=16, length=8)
        matches = self.detector.match([old], [new])
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].old.name, "EngineTemp")
        self.assertEqual(matches[0].new.name, "CoolantTemp")

    def test_different_layout_no_match(self):
        old = _make_signal("SigA", start_bit=0, length=8)
        new = _make_signal("SigB", start_bit=24, length=16)
        matches = self.detector.match([old], [new])
        self.assertEqual(len(matches), 0)

    def test_exact_same_signal_high_confidence(self):
        old = _make_signal("Speed", start_bit=0, length=16, factor=0.01, unit="km/h")
        new = _make_signal("VehicleSpeed", start_bit=0, length=16, factor=0.01, unit="km/h")
        matches = self.detector.match([old], [new])
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].confidence_level, "High")

    def test_one_to_one_greedy(self):
        old1 = _make_signal("A", start_bit=0, length=8)
        old2 = _make_signal("B", start_bit=8, length=8)
        new1 = _make_signal("X", start_bit=0, length=8)
        new2 = _make_signal("Y", start_bit=8, length=8)
        matches = self.detector.match([old1, old2], [new1, new2])
        self.assertEqual(len(matches), 2)

    def test_confidence_levels(self):
        self.assertEqual(self.detector.get_confidence_level(0.95), "High")
        self.assertEqual(self.detector.get_confidence_level(0.80), "Medium")
        self.assertEqual(self.detector.get_confidence_level(0.65), "Low")


class TestSignalRenameDetectorEventMode(unittest.TestCase):
    def test_event_mode_uses_lower_threshold(self):
        detector = SignalRenameDetector(is_event_like=True)
        self.assertEqual(detector.threshold, detector.event_threshold)

    def test_event_mode_name_similarity_drives_match(self):
        detector = SignalRenameDetector(is_event_like=True)
        old = _make_signal("Event_Door_Open", start_bit=0, length=1)
        new = _make_signal("Door_Opened", start_bit=0, length=1)
        matches = detector.match([old], [new])
        self.assertEqual(len(matches), 1)


class TestMessageRenameDetector(unittest.TestCase):
    def setUp(self):
        self.detector = MessageRenameDetector()

    def test_same_can_id_matches(self):
        old = _make_message("BCM_Status", can_id=100)
        new = _make_message("Body_Status", can_id=100)
        matches = self.detector.match([old], [new])
        self.assertEqual(len(matches), 1)

    def test_different_can_id_no_match(self):
        old = _make_message("MsgA", can_id=100)
        new = _make_message("MsgB", can_id=999)
        matches = self.detector.match([old], [new])
        self.assertEqual(len(matches), 0)


class TestEventMessageDetector(unittest.TestCase):
    def _make_event_signals(self, count: int) -> dict[str, Signal]:
        return {
            f"Event_{i}": _make_signal(f"Event_{i}", start_bit=i, length=1)
            for i in range(count)
        }

    def test_event_like_with_many_short_signals(self):
        msg = _make_message("EventMatrix", can_id=200, signals=self._make_event_signals(8))
        self.assertTrue(EventMessageDetector.is_event_like(msg))

    def test_not_event_like_with_few_signals(self):
        msg = _make_message("Normal", can_id=100, signals={
            "Speed": _make_signal("Speed", length=16),
        })
        self.assertFalse(EventMessageDetector.is_event_like(msg))

    def test_warning_message_is_string(self):
        self.assertIsInstance(EventMessageDetector.get_warning(), str)
        self.assertGreater(len(EventMessageDetector.get_warning()), 0)


if __name__ == "__main__":
    unittest.main()
