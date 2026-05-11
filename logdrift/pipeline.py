"""pipeline.py — Composable event processing pipeline for logdrift.

Chains deduplication, rate-limiting, throttling, sampling, tagging,
enrichment, and routing into a single reusable processing unit so that
callers don't have to wire each stage together manually.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional

from logdrift.aggregator import AnomalyEvent
from logdrift.dedup import AnomalyDeduplicator, DedupConfig
from logdrift.enriched_aggregator import EnrichedAnomalyEvent
from logdrift.enrichment import Enricher
from logdrift.ratelimit import RateLimitConfig, SlidingWindowRateLimiter
from logdrift.routing import EventRouter
from logdrift.sampling import EventSampler, SamplingConfig
from logdrift.tagging import EventTagger
from logdrift.throttle import AnomalyThrottle, ThrottleConfig


@dataclass
class PipelineConfig:
    """Aggregated configuration for all pipeline stages.

    Every stage is optional; pass *None* (the default) to skip it.
    """

    dedup: Optional[DedupConfig] = None
    rate_limit: Optional[RateLimitConfig] = None
    throttle: Optional[ThrottleConfig] = None
    sampling: Optional[SamplingConfig] = None
    # Enrichment, tagging, and routing are injected as ready-made objects
    # because they carry compiled regex state that isn't cheaply serialisable.
    enricher: Optional[Enricher] = None
    tagger: Optional[EventTagger] = None
    router: Optional[EventRouter] = None


class EventPipeline:
    """Process a stream of :class:`AnomalyEvent` objects through a series of
    optional stages and yield the events that survive all filters.

    Stages (in order):
      1. Deduplication  – drop exact duplicates within a time window
      2. Rate limiting  – drop events that exceed a per-key rate
      3. Throttling     – suppress bursts beyond a per-key count
      4. Sampling       – probabilistic / deterministic keep-1-in-N
      5. Enrichment     – attach structured metadata from regex captures
      6. Tagging        – attach free-form string tags
      7. Routing        – annotate with a destination label (no dropping)
    """

    def __init__(self, config: PipelineConfig) -> None:
        self._config = config

        self._dedup: Optional[AnomalyDeduplicator] = (
            AnomalyDeduplicator(config.dedup) if config.dedup else None
        )
        self._rate_limiter: Optional[SlidingWindowRateLimiter] = (
            SlidingWindowRateLimiter(config.rate_limit) if config.rate_limit else None
        )
        self._throttle: Optional[AnomalyThrottle] = (
            AnomalyThrottle(config.throttle) if config.throttle else None
        )
        self._sampler: Optional[EventSampler] = (
            EventSampler(config.sampling) if config.sampling else None
        )
        self._enricher: Optional[Enricher] = config.enricher
        self._tagger: Optional[EventTagger] = config.tagger
        self._router: Optional[EventRouter] = config.router

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, events: Iterable[AnomalyEvent]) -> List[AnomalyEvent]:
        """Run *events* through the pipeline and return surviving events.

        Events may be plain :class:`AnomalyEvent` instances or the richer
        :class:`EnrichedAnomalyEvent` subclass — both are handled.
        """
        results: List[AnomalyEvent] = []
        for event in events:
            processed = self._process_one(event)
            if processed is not None:
                results.append(processed)
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _process_one(self, event: AnomalyEvent) -> Optional[AnomalyEvent]:
        """Apply every active stage to a single event.

        Returns the (possibly mutated) event, or *None* if a filter stage
        decided to drop it.
        """
        # --- Filter stages ---
        if self._dedup and not self._dedup.is_new(event):
            return None

        if self._rate_limiter and not self._rate_limiter.allow(event):
            return None

        if self._throttle and not self._throttle.allow(event):
            return None

        if self._sampler and not self._sampler.keep(event):
            return None

        # --- Enrichment / annotation stages ---
        # Wrap in EnrichedAnomalyEvent if enrichment or tagging is active and
        # the event isn't already an enriched instance.
        if self._enricher or self._tagger:
            if not isinstance(event, EnrichedAnomalyEvent):
                event = EnrichedAnomalyEvent(
                    filepath=event.filepath,
                    line=event.line,
                    pattern_name=event.pattern_name,
                    timestamp=event.timestamp,
                    metadata={},
                    tags=[],
                )

        if self._enricher and isinstance(event, EnrichedAnomalyEvent):
            extra = self._enricher.enrich(event.line)
            event.metadata.update(extra)

        if self._tagger and isinstance(event, EnrichedAnomalyEvent):
            new_tags = self._tagger.tag(event)
            for t in new_tags:
                if t not in event.tags:
                    event.tags.append(t)

        # --- Routing (annotation only, never drops) ---
        if self._router:
            event.destination = self._router.route(event)  # type: ignore[attr-defined]

        return event
