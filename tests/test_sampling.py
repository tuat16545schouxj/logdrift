"""Tests for logdrift.sampling — EventSampler."""

from __future__ import annotations

import datetime
from typing import List

import pytest

from logdrift.aggregator import AnomalyEvent
from logdrift.sampling import EventSampler, SamplingConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_event(
    line: str = "ERROR something",
    filepath: str = "/var/log/app.log",
    pattern_name: str = "error",
) -> AnomalyEvent:
    return AnomalyEvent(
        filepath=filepath,
        line=line,
        pattern_name=pattern_name,
        timestamp=datetime.datetime(2024, 1, 1, 12, 0, 0),
    )


def make_events(n: int, **kwargs) -> List[AnomalyEvent]:
    return [make_event(line=f"ERROR line {i}", **kwargs) for i in range(n)]


# ---------------------------------------------------------------------------
# SamplingConfig defaults
# ---------------------------------------------------------------------------

def test_default_config_rate_is_one():
    config = SamplingConfig()
    assert config.rate == 1
    assert config.deterministic is False


# ---------------------------------------------------------------------------
# rate=1 — keep everything
# ---------------------------------------------------------------------------

def test_rate_one_keeps_all_events():
    sampler = EventSampler(SamplingConfig(rate=1))
    events = make_events(20)
    assert sampler.filter(events) == events


# ---------------------------------------------------------------------------
# Counter-based sampling
# ---------------------------------------------------------------------------

def test_rate_n_keeps_roughly_one_in_n():
    sampler = EventSampler(SamplingConfig(rate=5))
    events = make_events(50)
    kept = sampler.filter(events)
    # Exactly 10 should be kept (indices 0, 5, 10, …)
    assert len(kept) == 10


def test_first_event_always_kept_for_new_key():
    sampler = EventSampler(SamplingConfig(rate=10))
    event = make_event()
    assert sampler.should_keep(event) is True


def test_second_event_suppressed_when_rate_gt_one():
    sampler = EventSampler(SamplingConfig(rate=10))
    event = make_event()
    sampler.should_keep(event)  # first — kept
    assert sampler.should_keep(event) is False  # second — suppressed


def test_different_keys_are_independent():
    sampler = EventSampler(SamplingConfig(rate=3))
    e1 = make_event(filepath="/a.log")
    e2 = make_event(filepath="/b.log")
    # Both are first occurrences for their respective keys
    assert sampler.should_keep(e1) is True
    assert sampler.should_keep(e2) is True


def test_reset_clears_counters():
    sampler = EventSampler(SamplingConfig(rate=5))
    events = make_events(5)
    sampler.filter(events)  # advances counters
    sampler.reset()
    # After reset the first event should be kept again
    assert sampler.should_keep(make_event()) is True


# ---------------------------------------------------------------------------
# Deterministic (hash-based) sampling
# ---------------------------------------------------------------------------

def test_deterministic_sampling_is_stable():
    config = SamplingConfig(rate=4, deterministic=True)
    sampler = EventSampler(config)
    event = make_event(line="stable line")
    results = {sampler.should_keep(event) for _ in range(10)}
    # Deterministic — same event always produces the same decision
    assert len(results) == 1


def test_deterministic_different_lines_vary():
    config = SamplingConfig(rate=2, deterministic=True)
    sampler = EventSampler(config)
    decisions = [sampler.should_keep(make_event(line=f"line {i}")) for i in range(20)]
    # With rate=2 we expect roughly half to be kept (not all True or all False)
    assert True in decisions
    assert False in decisions
