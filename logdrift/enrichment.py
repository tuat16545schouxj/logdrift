"""Log line enrichment: attach structured metadata to anomaly events."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class EnrichmentRule:
    """A named regex rule that extracts key/value fields from a log line."""

    name: str
    pattern: re.Pattern
    fields: List[str]  # named groups to extract

    @classmethod
    def compile(cls, name: str, regex: str) -> "EnrichmentRule":
        compiled = re.compile(regex)
        groups = list(compiled.groupindex.keys())
        if not groups:
            raise ValueError(
                f"EnrichmentRule '{name}' regex must contain at least one named group."
            )
        return cls(name=name, pattern=compiled, fields=groups)

    def extract(self, line: str) -> Optional[Dict[str, str]]:
        """Return matched named groups or None if the line doesn't match."""
        m = self.pattern.search(line)
        if m is None:
            return None
        return {k: v for k, v in m.groupdict().items() if v is not None}


@dataclass
class Enricher:
    """Applies a collection of EnrichmentRules to produce metadata dicts."""

    rules: List[EnrichmentRule] = field(default_factory=list)

    def add_rule(self, rule: EnrichmentRule) -> None:
        self.rules.append(rule)

    def enrich(self, line: str) -> Dict[str, str]:
        """Run all rules; later rules override earlier ones on key conflicts."""
        metadata: Dict[str, str] = {}
        for rule in self.rules:
            result = rule.extract(line)
            if result:
                metadata.update(result)
        return metadata


def default_enricher() -> Enricher:
    """Return an Enricher pre-loaded with common log metadata rules."""
    enricher = Enricher()
    enricher.add_rule(
        EnrichmentRule.compile(
            "ip_address",
            r"(?P<ip>\b(?:\d{1,3}\.){3}\d{1,3}\b)",
        )
    )
    enricher.add_rule(
        EnrichmentRule.compile(
            "http_status",
            r"\bHTTP[/ ]\S*\s+(?P<http_status>\d{3})\b",
        )
    )
    enricher.add_rule(
        EnrichmentRule.compile(
            "log_level",
            r"\b(?P<log_level>DEBUG|INFO|WARNING|ERROR|CRITICAL)\b",
        )
    )
    enricher.add_rule(
        EnrichmentRule.compile(
            "request_id",
            r"(?:request[_-]?id|rid)[=:\s]+(?P<request_id>[\w-]+)",
        )
    )
    return enricher
