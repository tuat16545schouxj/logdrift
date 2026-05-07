"""Tests for logdrift.dedup — AnomalyDeduplicator."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from logdrift.aggregator import AnomalyEvent
from logdrift.dedup import AnomalyDeduplicator, DedupConfig, _event_fingerprint


def make_event(filepath="app.log", pattern_name="error", line="ERROR something bad") -> AnomalyEvent:
    return AnomalyEvent(filepath=filepath, pattern_name=pattern_name, line=line)


# ---------------------------------------------------------------------------
# fingerprint
# ---------------------------------------------------------------------------

def test_fingerprint_same_event_is_stable():
    e = make_event()
    assert _event_fingerprint(e) == _event_fingerprint(e)


def test_fingerprint_differs_by_line():
    e1 = make_event(line="ERROR foo")
    e2 = make_event(line="ERROR bar")
    assert _event_fingerprint(e1) != _event_fingerprint(e2)


def test_fingerprint_differs_by_filepath():
    e1 = make_event(filepath="a.log")
    e2 = make_event(filepath="b.log")
    assert _event_fingerprint(e1) != _event_fingerprint(e2)


# ---------------------------------------------------------------------------
# filter — basic deduplication
# ---------------------------------------------------------------------------

def test_first_occurrence_passes_through():
    dedup = AnomalyDeduplicator()
    events = [make_event()]
    result = dedup.filter(events)
    assert len(result) == 1


def test_duplicate_within_window_suppressed():
    dedup = AnomalyDeduplicator(DedupConfig(window_seconds=60))
    e = make_event()
    dedup.filter([e])          # first — admitted
    result = dedup.filter([e]) # second — suppressed
    assert result == []


def test_duplicate_after_window_re_admitted():
    dedup = AnomalyDeduplicator(DedupConfig(window_seconds=1))
    e = make_event()
    dedup.filter([e])

    # Advance time beyond the window
    with patch("logdrift.dedup.time.time", return_value=time.time() + 5):
        result = dedup.filter([e])
    assert len(result) == 1


def test_different_events_both_pass():
    dedup = AnomalyDeduplicator()
    e1 = make_event(line="ERROR alpha")
    e2 = make_event(line="ERROR beta")
    result = dedup.filter([e1, e2])
    assert len(result) == 2


# ---------------------------------------------------------------------------
# duplicate_count
# ---------------------------------------------------------------------------

def test_duplicate_count_increments():
    dedup = AnomalyDeduplicator()
    e = make_event()
    dedup.filter([e])
    dedup.filter([e])
    dedup.filter([e])
    assert dedup.duplicate_count(e) == 3


def test_duplicate_count_unknown_event_is_zero():
    dedup = AnomalyDeduplicator()
    assert dedup.duplicate_count(make_event()) == 0


# ---------------------------------------------------------------------------
# cache size cap
# ---------------------------------------------------------------------------

def test_cache_respects_max_size():
    dedup = AnomalyDeduplicator(DedupConfig(max_cache_size=3))
    for i in range(10):
        dedup.filter([make_event(line=f"ERROR line {i}")])
    assert len(dedup._cache) <= 3


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------

def test_reset_clears_cache():
    dedup = AnomalyDeduplicator()
    e = make_event()
    dedup.filter([e])
    dedup.reset()
    result = dedup.filter([e])
    assert len(result) == 1
