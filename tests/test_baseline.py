"""Tests for logdrift.baseline module."""

import json
import time
from pathlib import Path

import pytest

from logdrift.baseline import BaselineEntry, BaselineStore


@pytest.fixture
def store(tmp_path: Path) -> BaselineStore:
    return BaselineStore(path=tmp_path / "baseline.json")


# ---------------------------------------------------------------------------
# BaselineEntry
# ---------------------------------------------------------------------------

def test_entry_defaults_set_automatically():
    before = time.time()
    entry = BaselineEntry(pattern_name="error", source_file="app.log")
    after = time.time()
    assert before <= entry.first_seen <= after
    assert entry.occurrence_count == 1


def test_entry_touch_updates_fields():
    entry = BaselineEntry(pattern_name="error", source_file="app.log")
    old_last = entry.last_seen
    time.sleep(0.01)
    entry.touch()
    assert entry.last_seen >= old_last
    assert entry.occurrence_count == 2


# ---------------------------------------------------------------------------
# BaselineStore — is_known / record
# ---------------------------------------------------------------------------

def test_new_entry_is_not_known(store: BaselineStore):
    assert not store.is_known("error", "app.log")


def test_record_makes_entry_known(store: BaselineStore):
    store.record("error", "app.log")
    assert store.is_known("error", "app.log")


def test_record_increments_on_repeat(store: BaselineStore):
    store.record("oom", "syslog")
    entry = store.record("oom", "syslog")
    assert entry.occurrence_count == 2


def test_different_files_tracked_separately(store: BaselineStore):
    store.record("error", "a.log")
    assert not store.is_known("error", "b.log")


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def test_entries_persisted_to_disk(tmp_path: Path):
    path = tmp_path / "bl.json"
    s1 = BaselineStore(path=path)
    s1.record("timeout", "worker.log")

    s2 = BaselineStore(path=path)
    assert s2.is_known("timeout", "worker.log")


def test_corrupt_file_starts_fresh(tmp_path: Path):
    path = tmp_path / "bl.json"
    path.write_text("not valid json{{")
    store = BaselineStore(path=path)  # should not raise
    assert store.all_entries() == []


def test_clear_removes_all_entries(store: BaselineStore):
    store.record("error", "app.log")
    store.clear()
    assert store.all_entries() == []
    assert not store.is_known("error", "app.log")


def test_all_entries_returns_list(store: BaselineStore):
    store.record("error", "a.log")
    store.record("warn", "b.log")
    assert len(store.all_entries()) == 2
