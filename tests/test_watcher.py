"""Tests for logdrift.watcher module."""

import os
import tempfile
import threading
import time

import pytest

from logdrift.watcher import LogFileWatcher, MultiLogWatcher


@pytest.fixture()
def tmp_log(tmp_path):
    log_file = tmp_path / "test.log"
    log_file.write_text("")
    return str(log_file)


def test_read_new_lines_empty(tmp_log):
    watcher = LogFileWatcher(tmp_log)
    assert watcher.read_new_lines() == []


def test_read_new_lines_initial_content(tmp_log):
    with open(tmp_log, "w") as f:
        f.write("line one\nline two\n")
    watcher = LogFileWatcher(tmp_log)
    lines = watcher.read_new_lines()
    assert lines == ["line one", "line two"]


def test_read_new_lines_incremental(tmp_log):
    watcher = LogFileWatcher(tmp_log)
    with open(tmp_log, "a") as f:
        f.write("first\n")
    assert watcher.read_new_lines() == ["first"]
    with open(tmp_log, "a") as f:
        f.write("second\n")
    assert watcher.read_new_lines() == ["second"]


def test_read_new_lines_missing_file():
    watcher = LogFileWatcher("/nonexistent/path/file.log")
    assert watcher.read_new_lines() == []


def test_multi_watcher_poll_once(tmp_path):
    log_a = tmp_path / "a.log"
    log_b = tmp_path / "b.log"
    log_a.write_text("alpha\n")
    log_b.write_text("beta\n")

    watcher = MultiLogWatcher([str(log_a), str(log_b)])
    results = list(watcher.poll_once())
    paths = [r[0] for r in results]
    lines = [r[1] for r in results]
    assert str(log_a) in paths
    assert str(log_b) in paths
    assert "alpha" in lines
    assert "beta" in lines


def test_multi_watcher_add_remove(tmp_path):
    log_a = tmp_path / "a.log"
    log_a.write_text("")
    watcher = MultiLogWatcher([])
    watcher.add_file(str(log_a))
    assert str(log_a) in watcher._watchers
    watcher.remove_file(str(log_a))
    assert str(log_a) not in watcher._watchers


def test_multi_watcher_watch_callback(tmp_path):
    log_file = tmp_path / "live.log"
    log_file.write_text("")
    collected = []
    stop = threading.Event()

    watcher = MultiLogWatcher([str(log_file)], poll_interval=0.05)

    def run():
        watcher.watch(lambda fp, line: collected.append(line), stop_event=stop)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    time.sleep(0.1)
    with open(str(log_file), "a") as f:
        f.write("hello watcher\n")
    time.sleep(0.2)
    stop.set()
    t.join(timeout=1)
    assert "hello watcher" in collected
