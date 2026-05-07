"""Tests for logdrift.throttle."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from logdrift.aggregator import AnomalyEvent
from logdrift.throttle import AnomalyThrottle, ThrottleConfig


def make_event(source: str = "app.log", pattern: str = "error") -> AnomalyEvent:
    return AnomalyEvent(
        source_file=source,
        pattern_name=pattern,
        line="ERROR something went wrong",
        line_number=1,
    )


def test_first_occurrence_emitted():
    throttle = AnomalyThrottle(ThrottleConfig(max_occurrences=3, window_seconds=60))
    assert throttle.should_emit(make_event()) is True


def test_within_limit_all_emitted():
    throttle = AnomalyThrottle(ThrottleConfig(max_occurrences=3, window_seconds=60))
    event = make_event()
    results = [throttle.should_emit(event) for _ in range(3)]
    assert all(results)


def test_exceeding_limit_suppressed():
    throttle = AnomalyThrottle(ThrottleConfig(max_occurrences=2, window_seconds=60))
    event = make_event()
    for _ in range(2):
        throttle.should_emit(event)
    assert throttle.should_emit(event) is False
    assert throttle.should_emit(event) is False


def test_suppressed_count_tracked():
    throttle = AnomalyThrottle(ThrottleConfig(max_occurrences=1, window_seconds=60))
    event = make_event(source="srv.log", pattern="critical")
    throttle.should_emit(event)  # emitted
    throttle.should_emit(event)  # suppressed
    throttle.should_emit(event)  # suppressed
    assert throttle.suppressed_count("srv.log", "critical") == 2


def test_different_keys_tracked_independently():
    throttle = AnomalyThrottle(ThrottleConfig(max_occurrences=1, window_seconds=60))
    e1 = make_event(source="a.log", pattern="error")
    e2 = make_event(source="b.log", pattern="error")
    assert throttle.should_emit(e1) is True
    assert throttle.should_emit(e2) is True
    assert throttle.should_emit(e1) is False
    assert throttle.should_emit(e2) is False


def test_window_expiry_resets_count():
    config = ThrottleConfig(max_occurrences=1, window_seconds=1.0)
    throttle = AnomalyThrottle(config)
    event = make_event()

    base = 0.0
    with patch("logdrift.throttle.time.monotonic", return_value=base):
        assert throttle.should_emit(event) is True
        assert throttle.should_emit(event) is False

    # Advance time beyond the window
    with patch("logdrift.throttle.time.monotonic", return_value=base + 2.0):
        assert throttle.should_emit(event) is True


def test_reset_clears_state():
    throttle = AnomalyThrottle(ThrottleConfig(max_occurrences=1, window_seconds=60))
    event = make_event()
    throttle.should_emit(event)
    throttle.should_emit(event)  # suppressed
    throttle.reset()
    assert throttle.should_emit(event) is True
    assert throttle.suppressed_count("app.log", "error") == 0
