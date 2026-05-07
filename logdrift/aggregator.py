"""Log aggregator — polls watched files and surfaces anomaly events.

This module is kept in sync with logdrift/throttle.py: when a
``ThrottleConfig`` is supplied the aggregator will skip events that exceed
the configured rate limit.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from logdrift.patterns import PatternRegistry
from logdrift.watcher import LogFileWatcher


@dataclass
class AnomalyEvent:
    source_file: str
    pattern_name: str
    line: str
    line_number: int
    timestamp: datetime.datetime = field(
        default_factory=datetime.datetime.utcnow
    )

    def __str__(self) -> str:  # pragma: no cover
        ts = self.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
        return (
            f"[{ts}] {self.source_file}:{self.line_number} "
            f"({self.pattern_name}) {self.line.rstrip()}"
        )


class LogAggregator:
    """Aggregate anomaly events from multiple log files.

    Parameters
    ----------
    registry:
        Pattern registry used to classify log lines.
    throttle:
        Optional :class:`~logdrift.throttle.AnomalyThrottle` instance.  When
        provided, events that exceed the throttle limit are silently dropped
        before being handed to *on_anomaly*.
    on_anomaly:
        Callback invoked for every non-throttled :class:`AnomalyEvent`.
    """

    def __init__(
        self,
        registry: PatternRegistry,
        throttle=None,
        on_anomaly: Optional[Callable[[AnomalyEvent], None]] = None,
    ) -> None:
        self._registry = registry
        self._throttle = throttle
        self._on_anomaly = on_anomaly
        self._watchers: List[LogFileWatcher] = []
        self.events: List[AnomalyEvent] = []

    def add_file(self, path: str) -> None:
        """Register a log file for polling."""
        self._watchers.append(LogFileWatcher(path))

    def poll_once(self) -> List[AnomalyEvent]:
        """Read new lines from all watched files and return new events."""
        new_events: List[AnomalyEvent] = []
        for watcher in self._watchers:
            for line_no, line in watcher.read_new_lines():
                matches = self._registry.match(line)
                for pattern_name in matches:
                    event = AnomalyEvent(
                        source_file=watcher.path,
                        pattern_name=pattern_name,
                        line=line,
                        line_number=line_no,
                    )
                    if self._throttle is not None:
                        if not self._throttle.should_emit(event):
                            continue
                    new_events.append(event)
                    self.events.append(event)
                    if self._on_anomaly is not None:
                        self._on_anomaly(event)
        return new_events

    def run(self, interval: float = 1.0) -> None:  # pragma: no cover
        """Poll indefinitely, sleeping *interval* seconds between polls."""
        import time

        while True:
            self.poll_once()
            time.sleep(interval)
