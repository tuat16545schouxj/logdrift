"""Tests for logdrift.summary module."""

import time
from unittest.mock import patch

import pytest

from logdrift.aggregator import AnomalyEvent
from logdrift.summary import SummaryBuilder, SummaryReport


def make_event(filepath="app.log", pattern_name="error", line="ERROR something", offset=0):
    ev = AnomalyEvent(
        filepath=filepath,
        line=line,
        pattern_name=pattern_name,
        timestamp=time.time() - offset,
    )
    return ev


# ---------------------------------------------------------------------------
# SummaryReport
# ---------------------------------------------------------------------------

def test_summary_report_str_empty():
    report = SummaryReport(window_seconds=60)
    text = str(report)
    assert "Summary" in text
    assert "0" in text


def test_summary_report_as_dict_keys():
    report = SummaryReport(window_seconds=120, total_events=3)
    d = report.as_dict()
    assert set(d.keys()) == {
        "window_seconds", "generated_at", "total_events",
        "events_by_file", "events_by_pattern", "top_messages",
    }
    assert d["total_events"] == 3


def test_summary_report_str_shows_counts():
    report = SummaryReport(
        window_seconds=60,
        total_events=2,
        events_by_file={"app.log": 2},
        events_by_pattern={"error": 2},
        top_messages=[("ERROR boom", 2)],
    )
    text = str(report)
    assert "app.log" in text
    assert "error" in text
    assert "ERROR boom" in text


# ---------------------------------------------------------------------------
# SummaryBuilder
# ---------------------------------------------------------------------------

def test_builder_empty_build():
    builder = SummaryBuilder(window_seconds=300)
    report = builder.build()
    assert report.total_events == 0
    assert report.events_by_file == {}


def test_builder_counts_events():
    builder = SummaryBuilder(window_seconds=300)
    builder.add(make_event("a.log", "error"))
    builder.add(make_event("a.log", "error"))
    builder.add(make_event("b.log", "warn"))
    report = builder.build()
    assert report.total_events == 3
    assert report.events_by_file["a.log"] == 2
    assert report.events_by_file["b.log"] == 1
    assert report.events_by_pattern["error"] == 2


def test_builder_top_messages_limited():
    builder = SummaryBuilder(window_seconds=300, top_n=2)
    for i in range(5):
        builder.add(make_event(line=f"ERROR msg{i}"))
    report = builder.build()
    assert len(report.top_messages) <= 2


def test_builder_excludes_old_events():
    builder = SummaryBuilder(window_seconds=60)
    builder.add(make_event(offset=120))  # older than window
    builder.add(make_event(offset=10))   # within window
    report = builder.build()
    assert report.total_events == 1


def test_builder_reset_clears_events():
    builder = SummaryBuilder(window_seconds=300)
    builder.add(make_event())
    builder.reset()
    report = builder.build()
    assert report.total_events == 0


def test_builder_retains_recent_after_build():
    builder = SummaryBuilder(window_seconds=300)
    builder.add(make_event())
    builder.build()
    # recent events are kept for the next build window
    report2 = builder.build()
    assert report2.total_events == 1
