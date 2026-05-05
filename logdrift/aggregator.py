"""Log aggregator that ties together file watching and pattern matching."""

import time
import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from logdrift.watcher import LogFileWatcher
from logdrift.patterns import PatternRegistry

logger = logging.getLogger(__name__)


@dataclass
class AnomalyEvent:
    """Represents a detected anomaly in a log file."""

    filepath: str
    line: str
    pattern_name: str
    timestamp: float = field(default_factory=time.time)

    def __str__(self) -> str:
        return (
            f"[{self.pattern_name}] {self.filepath}: {self.line.rstrip()}"
        )


class LogAggregator:
    """Watches multiple log files and surfaces anomalies via pattern matching."""

    def __init__(
        self,
        paths: List[str],
        registry: Optional[PatternRegistry] = None,
        on_anomaly: Optional[Callable[[AnomalyEvent], None]] = None,
        poll_interval: float = 1.0,
    ) -> None:
        self._registry = registry or PatternRegistry()
        self._on_anomaly = on_anomaly or self._default_handler
        self._poll_interval = poll_interval
        self._watchers: Dict[str, LogFileWatcher] = {
            path: LogFileWatcher(path) for path in paths
        }
        self._running = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_file(self, path: str) -> None:
        """Start watching an additional log file."""
        if path not in self._watchers:
            self._watchers[path] = LogFileWatcher(path)
            logger.debug("Added watcher for %s", path)

    def remove_file(self, path: str) -> None:
        """Stop watching a log file."""
        self._watchers.pop(path, None)
        logger.debug("Removed watcher for %s", path)

    def poll_once(self) -> List[AnomalyEvent]:
        """Read new lines from all watched files and return detected anomalies."""
        events: List[AnomalyEvent] = []
        for path, watcher in list(self._watchers.items()):
            try:
                for line in watcher.read_new_lines():
                    matched = self._registry.match(line)
                    if matched:
                        event = AnomalyEvent(
                            filepath=path,
                            line=line,
                            pattern_name=matched,
                        )
                        self._on_anomaly(event)
                        events.append(event)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Error reading %s: %s", path, exc)
        return events

    def run(self) -> None:
        """Block and continuously poll until stopped."""
        self._running = True
        logger.info("LogAggregator started, watching %d file(s)", len(self._watchers))
        try:
            while self._running:
                self.poll_once()
                time.sleep(self._poll_interval)
        except KeyboardInterrupt:
            pass
        finally:
            self._running = False
            logger.info("LogAggregator stopped")

    def stop(self) -> None:
        """Signal the run loop to exit."""
        self._running = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _default_handler(event: AnomalyEvent) -> None:
        print(str(event))
