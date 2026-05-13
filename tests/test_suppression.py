"""Tests for logdrift.suppression."""
from __future__ import annotations

import time
from datetime import datetime

import pytest

from logdrift.aggregator import AnomalyEvent
from logdrift.suppression import EventSuppressor, SuppressionRule


def make_event(
    line: str = "ERROR something broke",
    filepath: str = "/var/log/app.log",
    pattern_name: str = "error",
) -> AnomalyEvent:
    return AnomalyEvent(
        filepath=filepath,
        line=line,
        pattern_name=pattern_name,
        timestamp=datetime.utcnow(),
    )


# ── SuppressionRule ──────────────────────────────────────────────────────────

def test_rule_matches_line_pattern():
    rule = SuppressionRule(name="r", line_pattern="healthcheck")
    assert rule.matches(make_event(line="GET /healthcheck 200"))
    assert not rule.matches(make_event(line="ERROR something"))


def test_rule_matches_filepath_pattern():
    rule = SuppressionRule(name="r", filepath_pattern=r"access\.log")
    assert rule.matches(make_event(filepath="/var/log/access.log"))
    assert not rule.matches(make_event(filepath="/var/log/error.log"))


def test_rule_matches_pattern_name():
    rule = SuppressionRule(name="r", pattern_name="warning")
    assert rule.matches(make_event(pattern_name="warning"))
    assert not rule.matches(make_event(pattern_name="error"))


def test_rule_all_criteria_must_match():
    rule = SuppressionRule(name="r", line_pattern="health", pattern_name="info")
    assert not rule.matches(make_event(line="healthcheck", pattern_name="error"))
    assert rule.matches(make_event(line="healthcheck", pattern_name="info"))


def test_rule_no_criteria_matches_any_event():
    rule = SuppressionRule(name="catch-all")
    assert rule.matches(make_event())


def test_rule_expired_never_matches():
    rule = SuppressionRule(name="r", expires_at=time.time() - 1)
    assert not rule.matches(make_event())


def test_rule_not_yet_expired_matches():
    rule = SuppressionRule(name="r", expires_at=time.time() + 9999)
    assert rule.matches(make_event())


# ── EventSuppressor ──────────────────────────────────────────────────────────

def test_suppressor_empty_rules_passes_all():
    suppressor = EventSuppressor()
    events = [make_event(), make_event(line="WARN something")]
    assert suppressor.filter(events) == events


def test_suppressor_filters_matched_event():
    rule = SuppressionRule(name="r", line_pattern="healthcheck")
    suppressor = EventSuppressor(rules=[rule])
    events = [make_event(line="GET /healthcheck"), make_event(line="ERROR crash")]
    result = suppressor.filter(events)
    assert len(result) == 1
    assert result[0].line == "ERROR crash"


def test_suppressor_add_rule_dynamically():
    suppressor = EventSuppressor()
    suppressor.add_rule(SuppressionRule(name="r", pattern_name="error"))
    assert suppressor.is_suppressed(make_event(pattern_name="error"))
    assert not suppressor.is_suppressed(make_event(pattern_name="warning"))


def test_suppressor_prune_expired_removes_rules():
    active = SuppressionRule(name="active", expires_at=time.time() + 9999)
    expired = SuppressionRule(name="expired", expires_at=time.time() - 1)
    suppressor = EventSuppressor(rules=[active, expired])
    removed = suppressor.prune_expired()
    assert removed == 1
    assert len(suppressor.rules) == 1
    assert suppressor.rules[0].name == "active"


def test_suppressor_rules_property_returns_copy():
    rule = SuppressionRule(name="r")
    suppressor = EventSuppressor(rules=[rule])
    copy = suppressor.rules
    copy.clear()
    assert len(suppressor.rules) == 1
