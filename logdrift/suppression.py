"""Suppression rules: silence anomalies matching specific criteria."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import List, Optional

from logdrift.aggregator import AnomalyEvent


@dataclass
class SuppressionRule:
    """A single suppression rule."""
    name: str
    line_pattern: Optional[str] = None
    filepath_pattern: Optional[str] = None
    pattern_name: Optional[str] = None
    expires_at: Optional[float] = None  # Unix timestamp; None = never expires

    _line_re: Optional[re.Pattern] = field(default=None, init=False, repr=False)
    _path_re: Optional[re.Pattern] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.line_pattern:
            self._line_re = re.compile(self.line_pattern, re.IGNORECASE)
        if self.filepath_pattern:
            self._path_re = re.compile(self.filepath_pattern)

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def matches(self, event: AnomalyEvent) -> bool:
        if self.is_expired():
            return False
        if self._line_re and not self._line_re.search(event.line):
            return False
        if self._path_re and not self._path_re.search(event.filepath):
            return False
        if self.pattern_name and event.pattern_name != self.pattern_name:
            return False
        return True


class EventSuppressor:
    """Filters events that match any active suppression rule."""

    def __init__(self, rules: Optional[List[SuppressionRule]] = None) -> None:
        self._rules: List[SuppressionRule] = list(rules or [])

    def add_rule(self, rule: SuppressionRule) -> None:
        self._rules.append(rule)

    def is_suppressed(self, event: AnomalyEvent) -> bool:
        return any(r.matches(event) for r in self._rules)

    def filter(self, events: List[AnomalyEvent]) -> List[AnomalyEvent]:
        """Return only events that are NOT suppressed."""
        return [e for e in events if not self.is_suppressed(e)]

    def prune_expired(self) -> int:
        """Remove expired rules; returns count removed."""
        before = len(self._rules)
        self._rules = [r for r in self._rules if not r.is_expired()]
        return before - len(self._rules)

    @property
    def rules(self) -> List[SuppressionRule]:
        return list(self._rules)
