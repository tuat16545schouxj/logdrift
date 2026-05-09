"""Tests for logdrift.retention."""

import time
from unittest.mock import patch

import pytest

from logdrift.aggregator import AnomalyEvent
from logdrift.retention import RetentionConfig, RetentionStore


def make_event(line: str = "ERROR boom", ts: float | None = None) -> AnomalyEvent:
    ev = AnomalyEvent(filepath="/var/log/app.log", line=line, pattern_name="error")
    if ts is not None:
        ev.timestamp = ts
    return ev


# ---------------------------------------------------------------------------
# RetentionConfig defaults
# ---------------------------------------------------------------------------

def test_default_config_values():
    cfg = RetentionConfig()
    assert cfg.max_age_seconds == 3600.0
    assert cfg.max_events == 1000


# ---------------------------------------------------------------------------
# add / all / len
# ---------------------------------------------------------------------------

def test_add_single_event():
    store = RetentionStore()
    store.add(make_event())
    assert len(store) == 1


def test_add_many_events():
    store = RetentionStore()
    store.add_many([make_event(f"line {i}") for i in range(5)])
    assert len(store) == 5


def test_all_returns_snapshot():
    store = RetentionStore()
    ev = make_event()
    store.add(ev)
    snapshot = store.all()
    assert ev in snapshot
    # Mutating the snapshot doesn't affect the store
    snapshot.clear()
    assert len(store) == 1


# ---------------------------------------------------------------------------
# Age-based expiry
# ---------------------------------------------------------------------------

def test_old_events_are_expired():
    cfg = RetentionConfig(max_age_seconds=10.0, max_events=1000)
    store = RetentionStore(config=cfg)
    old_ts = time.time() - 20.0
    store.add(make_event(ts=old_ts))
    assert len(store) == 0  # expired immediately on add


def test_recent_events_are_kept():
    cfg = RetentionConfig(max_age_seconds=3600.0, max_events=1000)
    store = RetentionStore(config=cfg)
    store.add(make_event())
    assert len(store) == 1


def test_expire_returns_count_removed():
    cfg = RetentionConfig(max_age_seconds=10.0, max_events=1000)
    store = RetentionStore(config=cfg)
    # Bypass _apply by inserting directly
    store._events.append(make_event(ts=time.time() - 20.0))
    removed = store.expire()
    assert removed == 1
    assert len(store) == 0


# ---------------------------------------------------------------------------
# Max-count trimming
# ---------------------------------------------------------------------------

def test_max_events_trims_oldest():
    cfg = RetentionConfig(max_age_seconds=3600.0, max_events=3)
    store = RetentionStore(config=cfg)
    events = [make_event(f"line {i}") for i in range(5)]
    store.add_many(events)
    assert len(store) == 3
    # The most recent three should be kept
    assert store.all() == events[-3:]


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------

def test_clear_removes_all():
    store = RetentionStore()
    store.add_many([make_event() for _ in range(10)])
    store.clear()
    assert len(store) == 0
