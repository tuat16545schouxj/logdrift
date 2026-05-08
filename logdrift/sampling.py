"""Event sampling — reduce noise by probabilistically or periodically sampling anomaly events."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, List

from logdrift.aggregator import AnomalyEvent


@dataclass
class SamplingConfig:
    """Configuration for the event sampler."""

    # Keep only 1-in-N events for a given (filepath, pattern_name) key.
    rate: int = 1  # 1 means keep everything; 10 means keep ~1 in 10
    # If True, use deterministic hashing instead of a counter so that
    # identical log lines are sampled consistently across restarts.
    deterministic: bool = False


@dataclass
class _KeyState:
    counter: int = 0
    last_kept_ts: float = field(default_factory=time.time)


def _event_hash_bucket(event: AnomalyEvent, rate: int) -> bool:
    """Return True if the event should be kept based on its content hash."""
    digest = hashlib.md5(
        f"{event.filepath}:{event.pattern_name}:{event.line}".encode()
    ).hexdigest()
    # Use the last 8 hex chars as an integer and check divisibility.
    bucket = int(digest[-8:], 16)
    return (bucket % rate) == 0


class EventSampler:
    """Filters a stream of AnomalyEvents, retaining a statistical sample.

    Usage::

        config = SamplingConfig(rate=5)
        sampler = EventSampler(config)
        kept = sampler.filter(events)
    """

    def __init__(self, config: SamplingConfig | None = None) -> None:
        self._config = config or SamplingConfig()
        self._state: Dict[str, _KeyState] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def should_keep(self, event: AnomalyEvent) -> bool:
        """Return True if *event* should pass through the sampler."""
        rate = self._config.rate
        if rate <= 1:
            return True

        if self._config.deterministic:
            return _event_hash_bucket(event, rate)

        key = self._key(event)
        state = self._state.setdefault(key, _KeyState())
        state.counter += 1
        keep = (state.counter % rate) == 1  # keep the 1st, (rate+1)th, …
        if keep:
            state.last_kept_ts = time.time()
        return keep

    def filter(self, events: List[AnomalyEvent]) -> List[AnomalyEvent]:
        """Return the subset of *events* that pass the sampling policy."""
        return [e for e in events if self.should_keep(e)]

    def reset(self) -> None:
        """Clear all internal counters (useful between polling cycles in tests)."""
        self._state.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _key(event: AnomalyEvent) -> str:
        return f"{event.filepath}\x00{event.pattern_name}"
