"""Tests for logdrift.suppression_config."""
from __future__ import annotations

import time

import pytest

from logdrift.suppression_config import suppressor_from_config


def test_empty_config_returns_suppressor_with_no_rules():
    suppressor = suppressor_from_config({})
    assert suppressor.rules == []


def test_single_rule_created():
    config = {
        "rules": [
            {"name": "ignore-health", "line_pattern": "healthcheck"}
        ]
    }
    suppressor = suppressor_from_config(config)
    assert len(suppressor.rules) == 1
    assert suppressor.rules[0].name == "ignore-health"


def test_rule_with_filepath_pattern():
    config = {
        "rules": [
            {"name": "access-only", "filepath_pattern": r"access\.log"}
        ]
    }
    suppressor = suppressor_from_config(config)
    rule = suppressor.rules[0]
    assert rule.filepath_pattern == r"access\.log"


def test_rule_with_pattern_name():
    config = {
        "rules": [
            {"name": "no-warn", "pattern_name": "warning"}
        ]
    }
    suppressor = suppressor_from_config(config)
    assert suppressor.rules[0].pattern_name == "warning"


def test_ttl_seconds_sets_expires_at():
    before = time.time()
    config = {
        "rules": [
            {"name": "temp", "line_pattern": "debug", "ttl_seconds": 60}
        ]
    }
    suppressor = suppressor_from_config(config)
    after = time.time()
    rule = suppressor.rules[0]
    assert rule.expires_at is not None
    assert before + 60 <= rule.expires_at <= after + 60


def test_no_ttl_means_rule_never_expires():
    config = {
        "rules": [
            {"name": "permanent", "line_pattern": "error"}
        ]
    }
    suppressor = suppressor_from_config(config)
    assert suppressor.rules[0].expires_at is None


def test_multiple_rules_all_created():
    config = {
        "rules": [
            {"name": "r1", "line_pattern": "foo"},
            {"name": "r2", "line_pattern": "bar"},
            {"name": "r3", "pattern_name": "debug"},
        ]
    }
    suppressor = suppressor_from_config(config)
    assert len(suppressor.rules) == 3
    names = [r.name for r in suppressor.rules]
    assert names == ["r1", "r2", "r3"]
