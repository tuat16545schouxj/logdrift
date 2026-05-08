"""Aggregator variant that attaches enrichment metadata to AnomalyEvents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from logdrift.aggregator import AnomalyEvent, LogAggregator
from logdrift.enrichment import Enricher, default_enricher
from logdrift.patterns import PatternRegistry


@dataclass
class EnrichedAnomalyEvent(AnomalyEvent):
    """An AnomalyEvent extended with structured metadata extracted from the line."""

    metadata: Dict[str, str] = field(default_factory=dict)

    def __str__(self) -> str:  # pragma: no cover
        base = super().__str__()
        if self.metadata:
            meta_str = " ".join(f"{k}={v}" for k, v in sorted(self.metadata.items()))
            return f"{base} [{meta_str}]"
        return base


class EnrichedLogAggregator(LogAggregator):
    """LogAggregator that enriches each anomaly with metadata via an Enricher."""

    def __init__(
        self,
        registry: Optional[PatternRegistry] = None,
        enricher: Optional[Enricher] = None,
    ) -> None:
        super().__init__(registry=registry)
        self._enricher: Enricher = enricher if enricher is not None else default_enricher()

    def poll_once(self) -> List[EnrichedAnomalyEvent]:
        """Poll all watched files and return enriched anomaly events."""
        raw_events: List[AnomalyEvent] = super().poll_once()
        enriched: List[EnrichedAnomalyEvent] = []
        for ev in raw_events:
            metadata = self._enricher.enrich(ev.line)
            enriched.append(
                EnrichedAnomalyEvent(
                    filepath=ev.filepath,
                    line=ev.line,
                    pattern_name=ev.pattern_name,
                    timestamp=ev.timestamp,
                    metadata=metadata,
                )
            )
        return enriched
