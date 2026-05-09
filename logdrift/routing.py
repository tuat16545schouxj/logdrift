"""Event routing: dispatch anomaly events to different channels based on rules."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from logdrift.aggregator import AnomalyEvent


@dataclass
class RoutingRule:
    """A single routing rule that matches events and assigns a destination tag."""

    destination: str
    filepath_pattern: Optional[str] = None
    pattern_name: Optional[str] = None
    line_regex: Optional[str] = None

    _line_re: Optional[re.Pattern] = field(default=None, init=False, repr=False)

    def compile(self) -> "RoutingRule":
        if self.line_regex:
            self._line_re = re.compile(self.line_regex, re.IGNORECASE)
        return self

    def matches(self, event: AnomalyEvent) -> bool:
        if self.filepath_pattern:
            if not re.search(self.filepath_pattern, event.filepath, re.IGNORECASE):
                return False
        if self.pattern_name:
            if event.pattern_name != self.pattern_name:
                return False
        if self._line_re:
            if not self._line_re.search(event.line):
                return False
        return True


class EventRouter:
    """Routes events to destination tags based on an ordered list of rules."""

    def __init__(
        self,
        rules: Optional[List[RoutingRule]] = None,
        default_destination: str = "default",
    ) -> None:
        self._rules: List[RoutingRule] = [r.compile() for r in (rules or [])]
        self.default_destination = default_destination

    def add_rule(self, rule: RoutingRule) -> None:
        self._rules.append(rule.compile())

    def route(self, event: AnomalyEvent) -> str:
        """Return the destination tag for *event* (first match wins)."""
        for rule in self._rules:
            if rule.matches(event):
                return rule.destination
        return self.default_destination

    def route_many(self, events: List[AnomalyEvent]) -> dict[str, List[AnomalyEvent]]:
        """Partition *events* into a dict keyed by destination tag."""
        buckets: dict[str, List[AnomalyEvent]] = {}
        for event in events:
            dest = self.route(event)
            buckets.setdefault(dest, []).append(event)
        return buckets
