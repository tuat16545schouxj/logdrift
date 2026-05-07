"""Integration tests for LogAggregator + BaselineStore suppression."""

from pathlib import Path

import pytest

from logdrift.aggregator import LogAggregator
from logdrift.baseline import BaselineStore
from logdrift.patterns import PatternRegistry


@pytest.fixture
def tmp_log(tmp_path: Path):
    p = tmp_path / "app.log"
    p.write_text("")
    return p


@pytest.fixture
def registry() -> PatternRegistry:
    return PatternRegistry()


@pytest.fixture
def baseline(tmp_path: Path) -> BaselineStore:
    return BaselineStore(path=tmp_path / "baseline.json")


# ---------------------------------------------------------------------------
# Baseline recording
# ---------------------------------------------------------------------------

def test_anomaly_recorded_in_baseline(tmp_log, registry, baseline):
    agg = LogAggregator(registry=registry, baseline=baseline, suppress_known=False)
    agg.add_file(str(tmp_log))
    tmp_log.write_text("ERROR: disk full\n")
    agg.poll_once()
    assert baseline.is_known("error", str(tmp_log))


def test_non_anomaly_not_recorded(tmp_log, registry, baseline):
    agg = LogAggregator(registry=registry, baseline=baseline, suppress_known=False)
    agg.add_file(str(tmp_log))
    tmp_log.write_text("INFO: all good\n")
    agg.poll_once()
    assert baseline.all_entries() == []


# ---------------------------------------------------------------------------
# Suppression
# ---------------------------------------------------------------------------

def test_known_anomaly_suppressed(tmp_log, registry, baseline):
    # Pre-seed the baseline
    baseline.record("error", str(tmp_log))

    agg = LogAggregator(registry=registry, baseline=baseline, suppress_known=True)
    agg.add_file(str(tmp_log))
    tmp_log.write_text("ERROR: disk full\n")
    events = agg.poll_once()
    assert events == []


def test_unknown_anomaly_not_suppressed(tmp_log, registry, baseline):
    agg = LogAggregator(registry=registry, baseline=baseline, suppress_known=True)
    agg.add_file(str(tmp_log))
    tmp_log.write_text("CRITICAL: out of memory\n")
    events = agg.poll_once()
    # 'critical' pattern should fire and not be suppressed (first time)
    assert len(events) >= 1


def test_suppress_false_does_not_suppress(tmp_log, registry, baseline):
    baseline.record("error", str(tmp_log))

    agg = LogAggregator(registry=registry, baseline=baseline, suppress_known=False)
    agg.add_file(str(tmp_log))
    tmp_log.write_text("ERROR: disk full\n")
    events = agg.poll_once()
    assert len(events) == 1


def test_suppressed_entry_occurrence_incremented(tmp_log, registry, baseline):
    baseline.record("error", str(tmp_log))
    first_count = baseline.all_entries()[0].occurrence_count

    agg = LogAggregator(registry=registry, baseline=baseline, suppress_known=True)
    agg.add_file(str(tmp_log))
    tmp_log.write_text("ERROR: disk full\n")
    agg.poll_once()

    updated = baseline.all_entries()[0]
    assert updated.occurrence_count == first_count + 1
