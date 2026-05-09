"""Tests for logdrift.routing_config."""

from __future__ import annotations

import datetime
import pytest

from logdrift.aggregator import AnomalyEvent
from logdrift.routing_config import router_from_config


def make_event(
    filepath: str = "/var/log/app.log",
    pattern_name: str = "error",
    line: str = "ERROR boom",
) -> AnomalyEvent:
    return AnomalyEvent(
        filepath=filepath,
        pattern_name=pattern_name,
        line=line,
        timestamp=datetime.datetime.now(),
    )


def test_empty_config_uses_default_destination():
    router = router_from_config({})
    assert router.route(make_event()) == "default"


def test_custom_default_destination():
    router = router_from_config({"default_destination": "ops"})
    assert router.route(make_event()) == "ops"


def test_rule_created_from_config():
    config = {
        "rules": [
            {"destination": "security", "filepath_pattern": "auth"}
        ]
    }
    router = router_from_config(config)
    event = make_event(filepath="/var/log/auth.log")
    assert router.route(event) == "security"


def test_multiple_rules_order_preserved():
    config = {
        "default_destination": "default",
        "rules": [
            {"destination": "first", "pattern_name": "error"},
            {"destination": "second", "pattern_name": "error"},
        ],
    }
    router = router_from_config(config)
    assert router.route(make_event(pattern_name="error")) == "first"


def test_missing_destination_raises():
    config = {"rules": [{"filepath_pattern": "auth"}]}
    with pytest.raises(ValueError, match="destination"):
        router_from_config(config)


def test_full_rule_all_fields():
    config = {
        "rules": [
            {
                "destination": "db-team",
                "filepath_pattern": "mysql",
                "pattern_name": "error",
                "line_regex": "deadlock",
            }
        ]
    }
    router = router_from_config(config, default_destination="default")
    matching = make_event(
        filepath="/var/log/mysql.log",
        pattern_name="error",
        line="ERROR: deadlock detected",
    )
    non_matching = make_event(
        filepath="/var/log/mysql.log",
        pattern_name="error",
        line="ERROR: table not found",
    )
    assert router.route(matching) == "db-team"
    assert router.route(non_matching) == "default"
