"""Tests for logdrift.correlation."""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from logdrift.aggregator import AnomalyEvent
from logdrift.correlation import CorrelationConfig, EventCorrelator, Incident


def make_event(pattern_name: str = "error", filepath: str = "/var/log/app.log") -> AnomalyEvent:
    return AnomalyEvent(
        filepath=filepath,
        line="ERROR something bad",
        pattern_name=pattern_name,
    )


# ---------------------------------------------------------------------------
# Incident dataclass
# ---------------------------------------------------------------------------

def test_incident_size():
    ev = make_event()
    inc = Incident(key="error", events=[ev, ev])
    assert inc.size == 2


# ---------------------------------------------------------------------------
# EventCorrelator — basic
# ---------------------------------------------------------------------------

def test_below_threshold_returns_none():
    cfg = CorrelationConfig(min_events=3, window_seconds=60)
    correlator = EventCorrelator(cfg)
    assert correlator.add(make_event()) is None
    assert correlator.add(make_event()) is None


def test_at_threshold_returns_incident():
    cfg = CorrelationConfig(min_events=2, window_seconds=60)
    correlator = EventCorrelator(cfg)
    correlator.add(make_event())
    inc = correlator.add(make_event())
    assert isinstance(inc, Incident)
    assert inc.size == 2
    assert inc.key == "error"


def test_bucket_reset_after_incident():
    cfg = CorrelationConfig(min_events=2, window_seconds=60)
    correlator = EventCorrelator(cfg)
    correlator.add(make_event())
    correlator.add(make_event())  # triggers incident, resets
    result = correlator.add(make_event())  # only 1 in bucket now
    assert result is None


def test_group_by_filepath():
    cfg = CorrelationConfig(min_events=2, window_seconds=60, group_by="filepath")
    correlator = EventCorrelator(cfg)
    ev1 = make_event(filepath="/var/log/a.log")
    ev2 = make_event(filepath="/var/log/b.log")
    assert correlator.add(ev1) is None
    assert correlator.add(ev2) is None  # different key
    inc = correlator.add(make_event(filepath="/var/log/a.log"))
    assert inc is not None
    assert inc.key == "/var/log/a.log"


def test_stale_events_evicted():
    cfg = CorrelationConfig(min_events=2, window_seconds=1)
    correlator = EventCorrelator(cfg)

    fake_now = time.time()
    with patch("logdrift.correlation.time.time", return_value=fake_now):
        correlator.add(make_event())

    # Advance time beyond the window
    with patch("logdrift.correlation.time.time", return_value=fake_now + 2):
        result = correlator.add(make_event())  # stale event evicted; only 1 remains
    assert result is None


def test_add_many_returns_incidents():
    cfg = CorrelationConfig(min_events=2, window_seconds=60)
    correlator = EventCorrelator(cfg)
    events = [make_event() for _ in range(4)]
    incidents = correlator.add_many(events)
    assert len(incidents) == 2
    for inc in incidents:
        assert isinstance(inc, Incident)
