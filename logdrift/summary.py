"""Periodic summary reporting for logdrift anomaly events."""

from __future__ import annotations

import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import List, Dict

from logdrift.aggregator import AnomalyEvent


@dataclass
class SummaryReport:
    """Aggregated summary of anomaly events over a time window."""

    window_seconds: int
    generated_at: float = field(default_factory=time.time)
    total_events: int = 0
    events_by_file: Dict[str, int] = field(default_factory=dict)
    events_by_pattern: Dict[str, int] = field(default_factory=dict)
    top_messages: List[tuple] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "window_seconds": self.window_seconds,
            "generated_at": self.generated_at,
            "total_events": self.total_events,
            "events_by_file": self.events_by_file,
            "events_by_pattern": self.events_by_pattern,
            "top_messages": self.top_messages,
        }

    def __str__(self) -> str:
        lines = [
            f"=== Summary (last {self.window_seconds}s) ===",
            f"Total anomalies : {self.total_events}",
        ]
        if self.events_by_file:
            lines.append("By file:")
            for fname, count in sorted(self.events_by_file.items()):
                lines.append(f"  {fname}: {count}")
        if self.events_by_pattern:
            lines.append("By pattern:")
            for pat, count in sorted(self.events_by_pattern.items()):
                lines.append(f"  {pat}: {count}")
        if self.top_messages:
            lines.append("Top messages:")
            for msg, count in self.top_messages:
                lines.append(f"  [{count}x] {msg}")
        return "\n".join(lines)


class SummaryBuilder:
    """Collects AnomalyEvents and produces SummaryReports on demand."""

    def __init__(self, window_seconds: int = 300, top_n: int = 5) -> None:
        self.window_seconds = window_seconds
        self.top_n = top_n
        self._events: List[AnomalyEvent] = []

    def add(self, event: AnomalyEvent) -> None:
        """Record an event for inclusion in the next summary."""
        self._events.append(event)

    def build(self) -> SummaryReport:
        """Build a summary from collected events and reset the buffer."""
        now = time.time
        cutoff = time.time() - self.window_seconds
        recent = [e for e in self._events if e.timestamp >= cutoff]

        by_file: Counter = Counter()
        by_pattern: Counter = Counter()
        by_message: Counter = Counter()

        for ev in recent:
            by_file[ev.filepath] += 1
            by_pattern[ev.pattern_name] += 1
            by_message[ev.line.strip()] += 1

        report = SummaryReport(
            window_seconds=self.window_seconds,
            total_events=len(recent),
            events_by_file=dict(by_file),
            events_by_pattern=dict(by_pattern),
            top_messages=by_message.most_common(self.top_n),
        )
        self._events = [e for e in self._events if e.timestamp >= cutoff]
        return report

    def reset(self) -> None:
        """Discard all buffered events."""
        self._events = []
