"""Throttle repeated anomaly alerts to avoid notification storms."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from logdrift.aggregator import AnomalyEvent


@dataclass
class ThrottleConfig:
    """Configuration for throttle behaviour."""

    window_seconds: float = 60.0
    max_occurrences: int = 3


@dataclass
class _BucketState:
    count: int = 0
    window_start: float = field(default_factory=time.monotonic)
    suppressed: int = 0


class AnomalyThrottle:
    """Suppress duplicate anomaly events that fire too frequently.

    Events are bucketed by ``(source_file, pattern_name)``.  Within each
    rolling *window_seconds* window at most *max_occurrences* events are
    forwarded; the rest are counted as suppressed.
    """

    def __init__(self, config: Optional[ThrottleConfig] = None) -> None:
        self._config = config or ThrottleConfig()
        self._buckets: Dict[Tuple[str, str], _BucketState] = defaultdict(
            _BucketState
        )

    def _key(self, event: AnomalyEvent) -> Tuple[str, str]:
        return (event.source_file, event.pattern_name)

    def _reset_if_expired(self, state: _BucketState, now: float) -> None:
        if now - state.window_start >= self._config.window_seconds:
            state.count = 0
            state.suppressed = 0
            state.window_start = now

    def should_emit(self, event: AnomalyEvent) -> bool:
        """Return *True* if the event should be forwarded to the reporter."""
        now = time.monotonic()
        key = self._key(event)
        state = self._buckets[key]
        self._reset_if_expired(state, now)
        state.count += 1
        if state.count <= self._config.max_occurrences:
            return True
        state.suppressed += 1
        return False

    def suppressed_count(self, source_file: str, pattern_name: str) -> int:
        """Return the number of suppressed events in the current window."""
        key = (source_file, pattern_name)
        return self._buckets[key].suppressed

    def reset(self) -> None:
        """Clear all throttle state (useful for testing)."""
        self._buckets.clear()
