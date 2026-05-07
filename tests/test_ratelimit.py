"""Tests for logdrift.ratelimit."""

from __future__ import annotations

import time
from datetime import datetime
from unittest.mock import patch

import pytest

from logdrift.aggregator import AnomalyEvent
from logdrift.ratelimit import RateLimitConfig, SlidingWindowRateLimiter


def make_event(filepath: str = "/var/log/app.log", pattern: str = "error") -> AnomalyEvent:
    return AnomalyEvent(
        filepath=filepath,
        line="ERROR something went wrong",
        pattern_name=pattern,
        timestamp=datetime.utcnow(),
    )


def test_first_event_is_allowed():
    limiter = SlidingWindowRateLimiter(RateLimitConfig(max_events=3, window_seconds=60))
    event = make_event()
    assert limiter.is_allowed(event) is True


def test_within_limit_all_allowed():
    limiter = SlidingWindowRateLimiter(RateLimitConfig(max_events=3, window_seconds=60))
    event = make_event()
    results = [limiter.is_allowed(event) for _ in range(3)]
    assert all(results)


def test_exceeding_limit_blocked():
    limiter = SlidingWindowRateLimiter(RateLimitConfig(max_events=3, window_seconds=60))
    event = make_event()
    for _ in range(3):
        limiter.is_allowed(event)
    assert limiter.is_allowed(event) is False


def test_different_keys_independent():
    limiter = SlidingWindowRateLimiter(RateLimitConfig(max_events=1, window_seconds=60))
    e1 = make_event(pattern="error")
    e2 = make_event(pattern="warning")
    assert limiter.is_allowed(e1) is True
    assert limiter.is_allowed(e2) is True
    assert limiter.is_allowed(e1) is False
    assert limiter.is_allowed(e2) is False


def test_window_expiry_allows_new_events():
    config = RateLimitConfig(max_events=2, window_seconds=1.0)
    limiter = SlidingWindowRateLimiter(config)
    event = make_event()
    limiter.is_allowed(event)
    limiter.is_allowed(event)
    assert limiter.is_allowed(event) is False

    # Advance time beyond the window
    future = time.time() + 2.0
    with patch("logdrift.ratelimit.time.time", return_value=future):
        assert limiter.is_allowed(event) is True


def test_current_count_reflects_window():
    limiter = SlidingWindowRateLimiter(RateLimitConfig(max_events=5, window_seconds=60))
    event = make_event()
    assert limiter.current_count(event) == 0
    limiter.is_allowed(event)
    limiter.is_allowed(event)
    assert limiter.current_count(event) == 2


def test_reset_clears_state():
    limiter = SlidingWindowRateLimiter(RateLimitConfig(max_events=1, window_seconds=60))
    event = make_event()
    limiter.is_allowed(event)
    assert limiter.is_allowed(event) is False
    limiter.reset(event)
    assert limiter.is_allowed(event) is True


def test_current_count_unknown_key_is_zero():
    limiter = SlidingWindowRateLimiter()
    event = make_event()
    assert limiter.current_count(event) == 0
