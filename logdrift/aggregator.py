"""Log aggregator: polls watched files and surfaces anomaly events.

Extended with optional BaselineStore support so that already-known
(pattern, file) pairs can be suppressed from the output.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional

from logdrift.baseline import BaselineStore
from logdrift.patterns import PatternRegistry
from logdrift.watcher import LogFileWatcher


@dataclass
class AnomalyEvent:
    source_file: str
    line: str
    pattern_name: str
    timestamp: float = field(default_factory=time.time)

    def __str__(self) -> str:
        ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(self.timestamp))
        return f"[{ts}] {self.source_file} | {self.pattern_name} | {self.line.rstrip()}"


class LogAggregator:
    """Aggregate log lines from multiple files and emit AnomalyEvents."""

    def __init__(
        self,
        registry: Optional[PatternRegistry] = None,
        baseline: Optional[BaselineStore] = None,
        suppress_known: bool = False,
    ) -> None:
        self._registry = registry or PatternRegistry()
        self._watchers: List[LogFileWatcher] = []
        self._baseline = baseline
        self._suppress_known = suppress_known and baseline is not None

    def add_file(self, path: str) -> None:
        self._watchers.append(LogFileWatcher(path))

    def poll_once(self) -> List[AnomalyEvent]:
        """Read new lines from all watched files and return anomaly events."""
        events: List[AnomalyEvent] = []
        for watcher in self._watchers:
            for line in watcher.read_new_lines():
                matched = self._registry.match(line)
                if matched is None:
                    continue
                if self._suppress_known and self._baseline is not None:
                    if self._baseline.is_known(matched.name, watcher.path):
                        self._baseline.record(matched.name, watcher.path)
                        continue
                if self._baseline is not None:
                    self._baseline.record(matched.name, watcher.path)
                events.append(
                    AnomalyEvent(
                        source_file=watcher.path,
                        line=line,
                        pattern_name=matched.name,
                    )
                )
        return events

    def poll_loop(self, interval: float = 1.0) -> None:  # pragma: no cover
        """Block forever, printing events as they arrive."""
        while True:
            for event in self.poll_once():
                print(event)
            time.sleep(interval)
