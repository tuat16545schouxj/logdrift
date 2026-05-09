"""Event correlation: group related anomaly events into incidents."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional

from logdrift.aggregator import AnomalyEvent


@dataclass
class CorrelationConfig:
    window_seconds: float = 60.0
    min_events: int = 2
    group_by: str = "pattern_name"  # "pattern_name" | "filepath"


@dataclass
class Incident:
    """A group of correlated anomaly events."""
    key: str
    events: List[AnomalyEvent] = field(default_factory=list)
    opened_at: float = field(default_factory=time.time)

    @property
    def size(self) -> int:
        return len(self.events)

    def __str__(self) -> str:  # pragma: no cover
        return (
            f"Incident(key={self.key!r}, events={self.size}, "
            f"opened_at={self.opened_at:.0f})"
        )


class EventCorrelator:
    """Accumulates events and emits Incidents when thresholds are met."""

    def __init__(self, config: Optional[CorrelationConfig] = None) -> None:
        self._config = config or CorrelationConfig()
        # key -> list of (timestamp, event)
        self._buckets: dict[str, list[tuple[float, AnomalyEvent]]] = {}

    def _key(self, event: AnomalyEvent) -> str:
        if self._config.group_by == "filepath":
            return event.filepath
        return event.pattern_name

    def _evict_stale(self, key: str, now: float) -> None:
        cutoff = now - self._config.window_seconds
        self._buckets[key] = [
            (ts, ev) for ts, ev in self._buckets.get(key, []) if ts >= cutoff
        ]

    def add(self, event: AnomalyEvent) -> Optional[Incident]:
        """Add an event; return an Incident if threshold is reached."""
        now = time.time()
        key = self._key(event)
        self._evict_stale(key, now)
        bucket = self._buckets.setdefault(key, [])
        bucket.append((now, event))

        if len(bucket) >= self._config.min_events:
            incident = Incident(
                key=key,
                events=[ev for _, ev in bucket],
                opened_at=bucket[0][0],
            )
            # Reset so we don't keep re-emitting the same incident
            self._buckets[key] = []
            return incident
        return None

    def add_many(self, events: List[AnomalyEvent]) -> List[Incident]:
        incidents: List[Incident] = []
        for ev in events:
            inc = self.add(ev)
            if inc is not None:
                incidents.append(inc)
        return incidents
