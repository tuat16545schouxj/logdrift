"""Event retention policy: age-based expiry and max-count trimming."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List

from logdrift.aggregator import AnomalyEvent


@dataclass
class RetentionConfig:
    """Configuration for the retention policy."""

    max_age_seconds: float = 3600.0  # 1 hour default
    max_events: int = 1000


@dataclass
class RetentionStore:
    """Holds recent events and enforces retention limits."""

    config: RetentionConfig = field(default_factory=RetentionConfig)
    _events: List[AnomalyEvent] = field(default_factory=list, repr=False)

    def add(self, event: AnomalyEvent) -> None:
        """Add an event and immediately apply retention rules."""
        self._events.append(event)
        self._apply()

    def add_many(self, events: List[AnomalyEvent]) -> None:
        """Add multiple events and apply retention rules once."""
        self._events.extend(events)
        self._apply()

    def all(self) -> List[AnomalyEvent]:
        """Return a snapshot of currently retained events."""
        return list(self._events)

    def expire(self) -> int:
        """Remove stale events; return the number removed."""
        before = len(self._events)
        self._apply()
        return before - len(self._events)

    def clear(self) -> None:
        """Remove all events."""
        self._events.clear()

    # ------------------------------------------------------------------
    def _apply(self) -> None:
        cutoff = time.time() - self.config.max_age_seconds
        self._events = [
            e for e in self._events if e.timestamp >= cutoff
        ]
        if len(self._events) > self.config.max_events:
            # Keep the most recent max_events entries
            self._events = self._events[-self.config.max_events :]

    def __len__(self) -> int:
        return len(self._events)
