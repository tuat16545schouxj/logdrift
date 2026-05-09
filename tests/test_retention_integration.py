"""Tests for logdrift.retention_integration."""

import os
import tempfile
from pathlib import Path

import pytest

from logdrift.aggregator import LogAggregator
from logdrift.patterns import PatternRegistry
from logdrift.retention import RetentionConfig, RetentionStore
from logdrift.retention_integration import poll_with_retention


@pytest.fixture()
def tmp_log(tmp_path: Path):
    p = tmp_path / "app.log"
    p.touch()
    return p


@pytest.fixture()
def registry():
    return PatternRegistry()


@pytest.fixture()
def store():
    return RetentionStore(config=RetentionConfig(max_age_seconds=3600.0, max_events=100))


# ---------------------------------------------------------------------------

def test_poll_no_anomalies_store_stays_empty(tmp_log, registry, store):
    tmp_log.write_text("everything is fine\n")
    agg = LogAggregator(registry=registry)
    agg.add_file(str(tmp_log))
    events = poll_with_retention(agg, store)
    assert events == []
    assert len(store) == 0


def test_poll_anomaly_added_to_store(tmp_log, registry, store):
    tmp_log.write_text("ERROR: disk full\n")
    agg = LogAggregator(registry=registry)
    agg.add_file(str(tmp_log))
    events = poll_with_retention(agg, store)
    assert len(events) == 1
    assert len(store) == 1
    assert store.all()[0].line == "ERROR: disk full"


def test_poll_multiple_anomalies_all_stored(tmp_log, registry, store):
    tmp_log.write_text("ERROR: thing one\nERROR: thing two\n")
    agg = LogAggregator(registry=registry)
    agg.add_file(str(tmp_log))
    events = poll_with_retention(agg, store)
    assert len(events) == 2
    assert len(store) == 2


def test_store_accumulates_across_polls(tmp_log, registry, store):
    agg = LogAggregator(registry=registry)
    agg.add_file(str(tmp_log))

    tmp_log.write_text("ERROR: first\n")
    poll_with_retention(agg, store)

    with tmp_log.open("a") as fh:
        fh.write("ERROR: second\n")
    poll_with_retention(agg, store)

    assert len(store) == 2


def test_store_respects_max_events(tmp_log, registry):
    small_store = RetentionStore(config=RetentionConfig(max_age_seconds=3600.0, max_events=1))
    tmp_log.write_text("ERROR: first\nERROR: second\n")
    agg = LogAggregator(registry=registry)
    agg.add_file(str(tmp_log))
    poll_with_retention(agg, small_store)
    assert len(small_store) == 1
