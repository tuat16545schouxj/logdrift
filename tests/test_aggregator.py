"""Tests for logdrift.aggregator."""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from logdrift.aggregator import AnomalyEvent, LogAggregator
from logdrift.patterns import PatternRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_log(tmp_path: Path) -> Path:
    log = tmp_path / "app.log"
    log.write_text("")
    return log


@pytest.fixture()
def registry() -> PatternRegistry:
    return PatternRegistry()


# ---------------------------------------------------------------------------
# AnomalyEvent
# ---------------------------------------------------------------------------


def test_anomaly_event_str() -> None:
    event = AnomalyEvent(filepath="/var/log/app.log", line="ERROR boom\n", pattern_name="error")
    assert "error" in str(event)
    assert "/var/log/app.log" in str(event)
    assert "ERROR boom" in str(event)


def test_anomaly_event_timestamp_set_automatically() -> None:
    before = time.time()
    event = AnomalyEvent(filepath="f", line="l", pattern_name="p")
    after = time.time()
    assert before <= event.timestamp <= after


# ---------------------------------------------------------------------------
# LogAggregator.poll_once
# ---------------------------------------------------------------------------


def test_poll_once_no_anomaly(tmp_log: Path, registry: PatternRegistry) -> None:
    tmp_log.write_text("everything is fine\n")
    agg = LogAggregator(paths=[str(tmp_log)], registry=registry)
    events = agg.poll_once()
    assert events == []


def test_poll_once_detects_error_line(tmp_log: Path, registry: PatternRegistry) -> None:
    tmp_log.write_text("ERROR: disk full\n")
    agg = LogAggregator(paths=[str(tmp_log)], registry=registry)
    events = agg.poll_once()
    assert len(events) == 1
    assert events[0].filepath == str(tmp_log)
    assert "ERROR" in events[0].line


def test_poll_once_calls_on_anomaly_callback(tmp_log: Path, registry: PatternRegistry) -> None:
    tmp_log.write_text("CRITICAL: out of memory\n")
    handler = MagicMock()
    agg = LogAggregator(paths=[str(tmp_log)], registry=registry, on_anomaly=handler)
    agg.poll_once()
    handler.assert_called_once()
    event_arg = handler.call_args[0][0]
    assert isinstance(event_arg, AnomalyEvent)


def test_poll_once_incremental(tmp_log: Path, registry: PatternRegistry) -> None:
    agg = LogAggregator(paths=[str(tmp_log)], registry=registry)
    agg.poll_once()  # consume empty file
    tmp_log.write_text("ERROR: something broke\n")
    events = agg.poll_once()
    assert len(events) == 1


# ---------------------------------------------------------------------------
# add_file / remove_file
# ---------------------------------------------------------------------------


def test_add_file(tmp_log: Path, registry: PatternRegistry) -> None:
    agg = LogAggregator(paths=[], registry=registry)
    assert str(tmp_log) not in agg._watchers
    agg.add_file(str(tmp_log))
    assert str(tmp_log) in agg._watchers


def test_remove_file(tmp_log: Path, registry: PatternRegistry) -> None:
    agg = LogAggregator(paths=[str(tmp_log)], registry=registry)
    agg.remove_file(str(tmp_log))
    assert str(tmp_log) not in agg._watchers


def test_remove_nonexistent_file_is_safe(registry: PatternRegistry) -> None:
    agg = LogAggregator(paths=[], registry=registry)
    agg.remove_file("/does/not/exist.log")  # should not raise


# ---------------------------------------------------------------------------
# stop
# ---------------------------------------------------------------------------


def test_stop_sets_running_false(registry: PatternRegistry) -> None:
    agg = LogAggregator(paths=[], registry=registry)
    agg._running = True
    agg.stop()
    assert not agg._running
