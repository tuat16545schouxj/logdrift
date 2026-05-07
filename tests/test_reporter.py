"""Tests for logdrift.reporter and logdrift.cli."""

from __future__ import annotations

import io
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from logdrift.aggregator import AnomalyEvent
from logdrift.cli import build_parser, run
from logdrift.reporter import Reporter


def make_event(source="app.log", pattern="error", line="ERROR: boom") -> AnomalyEvent:
    ev = AnomalyEvent(source_file=source, pattern_name=pattern, line=line)
    ev.timestamp = datetime(2024, 6, 1, 12, 0, 0)
    return ev


# --- Reporter tests ---

def test_reporter_text_no_events():
    buf = io.StringIO()
    Reporter(fmt="text", stream=buf).report([])
    assert "No anomalies" in buf.getvalue()


def test_reporter_text_with_events():
    buf = io.StringIO()
    Reporter(fmt="text", stream=buf).report([make_event()])
    out = buf.getvalue()
    assert "1 anomaly" in out
    assert "app.log" in out
    assert "ERROR: boom" in out
    assert "2024-06-01" in out


def test_reporter_json_no_events():
    buf = io.StringIO()
    Reporter(fmt="json", stream=buf).report([])
    data = json.loads(buf.getvalue())
    assert data == []


def test_reporter_json_with_events():
    buf = io.StringIO()
    Reporter(fmt="json", stream=buf).report([make_event()])
    data = json.loads(buf.getvalue())
    assert len(data) == 1
    assert data[0]["source_file"] == "app.log"
    assert data[0]["pattern_name"] == "error"
    assert data[0]["line"] == "ERROR: boom"


def test_reporter_invalid_format():
    with pytest.raises(ValueError, match="Unknown format"):
        Reporter(fmt="xml")


# --- CLI tests ---

def test_build_parser_defaults():
    parser = build_parser()
    args = parser.parse_args(["app.log"])
    assert args.files == ["app.log"]
    assert args.interval == 2.0
    assert args.fmt == "text"
    assert args.once is False


def test_run_once_no_anomalies(tmp_path):
    log_file = tmp_path / "test.log"
    log_file.write_text("all good\n")
    buf = io.StringIO()
    with patch("logdrift.reporter.sys.stdout", buf):
        exit_code = run([str(log_file), "--once"])
    assert exit_code == 0


def test_run_once_missing_file(tmp_path, capsys):
    exit_code = run([str(tmp_path / "missing.log"), "--once"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Warning" in captured.err
