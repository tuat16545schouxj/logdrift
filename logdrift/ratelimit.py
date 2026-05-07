"""Rate limiting for anomaly events using a sliding window counter."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict

from logdrift.aggregator import AnomalyEvent


@dataclass
class RateLimitConfig:
    """Configuration for the sliding-window rate limiter."""
    window_seconds: float = 60.0
    max_events: int = 10


@dataclass
class _WindowState:
    timestamps: Deque[float] = field(default_factory=deque)


class SlidingWindowRateLimiter:
    """Allows at most *max_events* per *window_seconds* for each (filepath, pattern) pair."""

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self._config = config or RateLimitConfig()
        self._windows: Dict[str, _WindowState] = {}

    def _key(self, event: AnomalyEvent) -> str:
        return f"{event.filepath}::{event.pattern_name}"

    def _evict_old(self, state: _WindowState, now: float) -> None:
        cutoff = now - self._config.window_seconds
        while state.timestamps and state.timestamps[0] < cutoff:
            state.timestamps.popleft()

    def is_allowed(self, event: AnomalyEvent) -> bool:
        """Return True if the event is within the allowed rate; record it if so."""
        key = self._key(event)
        now = time.time()
        state = self._windows.setdefault(key, _WindowState())
        self._evict_old(state, now)
        if len(state.timestamps) >= self._config.max_events:
            return False
        state.timestamps.append(now)
        return True

    def current_count(self, event: AnomalyEvent) -> int:
        """Return how many events are recorded in the current window for this key."""
        key = self._key(event)
        state = self._windows.get(key)
        if state is None:
            return 0
        self._evict_old(state, time.time())
        return len(state.timestamps)

    def reset(self, event: AnomalyEvent) -> None:
        """Clear the window state for a given event key."""
        key = self._key(event)
        self._windows.pop(key, None)
