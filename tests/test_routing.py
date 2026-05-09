"""Tests for logdrift.routing."""

from __future__ import annotations

import datetime
import pytest

from logdrift.aggregator import AnomalyEvent
from logdrift.routing import EventRouter, RoutingRule


def make_event(
    filepath: str = "/var/log/app.log",
    pattern_name: str = "error",
    line: str = "ERROR something went wrong",
) -> AnomalyEvent:
    return AnomalyEvent(
        filepath=filepath,
        pattern_name=pattern_name,
        line=line,
        timestamp=datetime.datetime.now(),
    )


def test_default_destination_returned_when_no_rules():
    router = EventRouter(default_destination="fallback")
    event = make_event()
    assert router.route(event) == "fallback"


def test_filepath_pattern_match():
    rule = RoutingRule(destination="auth-team", filepath_pattern="auth")
    router = EventRouter(rules=[rule])
    event = make_event(filepath="/var/log/auth.log")
    assert router.route(event) == "auth-team"


def test_filepath_pattern_no_match_falls_through():
    rule = RoutingRule(destination="auth-team", filepath_pattern="auth")
    router = EventRouter(rules=[rule], default_destination="default")
    event = make_event(filepath="/var/log/app.log")
    assert router.route(event) == "default"


def test_pattern_name_match():
    rule = RoutingRule(destination="critical", pattern_name="critical")
    router = EventRouter(rules=[rule])
    event = make_event(pattern_name="critical")
    assert router.route(event) == "critical"


def test_line_regex_match():
    rule = RoutingRule(destination="security", line_regex=r"failed login")
    router = EventRouter(rules=[rule])
    event = make_event(line="WARN: Failed Login attempt from 1.2.3.4")
    assert router.route(event) == "security"


def test_line_regex_no_match():
    rule = RoutingRule(destination="security", line_regex=r"failed login")
    router = EventRouter(rules=[rule], default_destination="ops")
    event = make_event(line="INFO: user logged in")
    assert router.route(event) == "ops"


def test_first_matching_rule_wins():
    rules = [
        RoutingRule(destination="first", filepath_pattern="app"),
        RoutingRule(destination="second", filepath_pattern="app"),
    ]
    router = EventRouter(rules=rules)
    event = make_event(filepath="/var/log/app.log")
    assert router.route(event) == "first"


def test_route_many_partitions_events():
    rules = [
        RoutingRule(destination="auth", filepath_pattern="auth"),
    ]
    router = EventRouter(rules=rules, default_destination="default")
    events = [
        make_event(filepath="/var/log/auth.log"),
        make_event(filepath="/var/log/app.log"),
        make_event(filepath="/var/log/auth.log"),
    ]
    buckets = router.route_many(events)
    assert len(buckets["auth"]) == 2
    assert len(buckets["default"]) == 1


def test_add_rule_dynamically():
    router = EventRouter(default_destination="default")
    router.add_rule(RoutingRule(destination="dynamic", pattern_name="warning"))
    event = make_event(pattern_name="warning")
    assert router.route(event) == "dynamic"


def test_route_many_empty_list_returns_empty_dict():
    """Routing an empty event list should return an empty dict without errors."""
    router = EventRouter(default_destination="default")
    buckets = router.route_many([])
    assert buckets == {}
