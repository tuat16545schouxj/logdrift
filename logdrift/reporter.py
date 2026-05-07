"""Reporter module for formatting and outputting anomaly summaries."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from typing import IO, List

from logdrift.aggregator import AnomalyEvent


class Reporter:
    """Formats and writes anomaly reports to an output stream."""

    FORMATS = ("text", "json")

    def __init__(self, fmt: str = "text", stream: IO[str] = sys.stdout) -> None:
        if fmt not in self.FORMATS:
            raise ValueError(f"Unknown format {fmt!r}. Choose from {self.FORMATS}.")
        self.fmt = fmt
        self.stream = stream

    def report(self, events: List[AnomalyEvent]) -> None:
        """Write a report for the given list of anomaly events."""
        if self.fmt == "json":
            self._write_json(events)
        else:
            self._write_text(events)

    def _write_text(self, events: List[AnomalyEvent]) -> None:
        if not events:
            self.stream.write("[logdrift] No anomalies detected.\n")
            return
        self.stream.write(f"[logdrift] {len(events)} anomaly(ies) detected:\n")
        for ev in events:
            ts = ev.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            self.stream.write(
                f"  [{ts}] {ev.source_file} | pattern={ev.pattern_name!r} | {ev.line}\n"
            )

    def _write_json(self, events: List[AnomalyEvent]) -> None:
        payload = [
            {
                "timestamp": ev.timestamp.isoformat(),
                "source_file": ev.source_file,
                "pattern_name": ev.pattern_name,
                "line": ev.line,
            }
            for ev in events
        ]
        json.dump(payload, self.stream, indent=2)
        self.stream.write("\n")
