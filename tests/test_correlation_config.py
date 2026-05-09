"""Tests for logdrift.correlation_config."""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from logdrift.correlation_config import correlator_config_from_dict


def test_defaults_when_section_missing():
    cfg = correlator_config_from_dict({})
    assert cfg.window_seconds == 60.0
    assert cfg.min_events == 2
    assert cfg.group_by == "pattern_name"


def test_custom_values():
    cfg = correlator_config_from_dict(
        {"correlation": {"window_seconds": 30, "min_events": 5, "group_by": "filepath"}}
    )
    assert cfg.window_seconds == 30.0
    assert cfg.min_events == 5
    assert cfg.group_by == "filepath"


def test_invalid_group_by_raises():
    with pytest.raises(ValueError, match="group_by"):
        correlator_config_from_dict({"correlation": {"group_by": "invalid"}})


def test_window_seconds_coerced_to_float():
    cfg = correlator_config_from_dict({"correlation": {"window_seconds": "120"}})
    assert isinstance(cfg.window_seconds, float)
    assert cfg.window_seconds == 120.0


def test_min_events_coerced_to_int():
    cfg = correlator_config_from_dict({"correlation": {"min_events": "3"}})
    assert isinstance(cfg.min_events, int)
    assert cfg.min_events == 3
