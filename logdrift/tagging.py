"""Event tagging — attach static or dynamic tags to AnomalyEvents based on rules."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from logdrift.aggregator import AnomalyEvent


@dataclass
class TagRule:
    """A rule that adds a tag when a pattern matches the event's log line."""

    tag: str
    pattern: str
    filepath_pattern: Optional[str] = None

    _compiled: re.Pattern = field(init=False, repr=False)
    _compiled_path: Optional[re.Pattern] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._compiled = re.compile(self.pattern, re.IGNORECASE)
        self._compiled_path = (
            re.compile(self.filepath_pattern, re.IGNORECASE)
            if self.filepath_pattern
            else None
        )

    def matches(self, event: AnomalyEvent) -> bool:
        """Return True if this rule applies to *event*."""
        if self._compiled_path and not self._compiled_path.search(event.filepath):
            return False
        return bool(self._compiled.search(event.line))


class EventTagger:
    """Applies a list of TagRules to events and returns enriched tag sets."""

    def __init__(self, rules: Optional[List[TagRule]] = None) -> None:
        self._rules: List[TagRule] = rules or []

    def add_rule(self, rule: TagRule) -> None:
        self._rules.append(rule)

    def tags_for(self, event: AnomalyEvent) -> List[str]:
        """Return all tags whose rules match *event* (deduplicated, sorted)."""
        matched = {rule.tag for rule in self._rules if rule.matches(event)}
        return sorted(matched)

    def tag_event(self, event: AnomalyEvent) -> Dict[str, object]:
        """Return a dict with the event plus a 'tags' key."""
        return {"event": event, "tags": self.tags_for(event)}


def tagger_from_config(config: List[Dict[str, str]]) -> EventTagger:
    """Build an EventTagger from a list of rule dicts.

    Each dict should have at minimum 'tag' and 'pattern' keys.
    An optional 'filepath_pattern' key scopes the rule to matching paths.
    """
    tagger = EventTagger()
    for entry in config:
        rule = TagRule(
            tag=entry["tag"],
            pattern=entry["pattern"],
            filepath_pattern=entry.get("filepath_pattern"),
        )
        tagger.add_rule(rule)
    return tagger
