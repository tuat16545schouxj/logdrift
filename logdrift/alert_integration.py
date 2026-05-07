"""High-level polling loop: aggregate → deduplicate → throttle → alert."""

from __future__ import annotations

import time
from typing import Optional

from logdrift.aggregator import LogAggregator
from logdrift.alert import AlertDispatcher
from logdrift.baseline import BaselineStore
from logdrift.dedup import AnomalyDeduplicator, DedupConfig
from logdrift.summary import SummaryBuilder
from logdrift.throttle import AnomalyThrottle, ThrottleConfig


def poll_and_alert(
    aggregator: LogAggregator,
    dispatcher: AlertDispatcher,
    throttle: Optional[AnomalyThrottle] = None,
    deduplicator: Optional[AnomalyDeduplicator] = None,
    baseline: Optional[BaselineStore] = None,
    summary_builder: Optional[SummaryBuilder] = None,
) -> int:
    """Run one poll cycle.  Returns the number of alerts dispatched."""
    events = aggregator.poll_once()

    if not events:
        return 0

    # Deduplication (new step, applied before throttle)
    if deduplicator is not None:
        events = deduplicator.filter(events)

    if not events:
        return 0

    # Baseline filtering
    if baseline is not None:
        novel = [e for e in events if not baseline.is_known(e.pattern_name, e.line)]
        for e in novel:
            baseline.record(e.pattern_name, e.line)
        events = novel

    if not events:
        return 0

    # Throttle
    if throttle is not None:
        events = throttle.filter(events)

    if not events:
        return 0

    # Summary tracking
    if summary_builder is not None:
        for e in events:
            summary_builder.add(e)

    dispatcher.send(events)
    return len(events)


def run_loop(
    aggregator: LogAggregator,
    dispatcher: AlertDispatcher,
    interval: float = 5.0,
    throttle_config: Optional[ThrottleConfig] = None,
    dedup_config: Optional[DedupConfig] = None,
    baseline: Optional[BaselineStore] = None,
) -> None:  # pragma: no cover
    """Block forever, polling on *interval* seconds."""
    throttle = AnomalyThrottle(throttle_config) if throttle_config else None
    deduplicator = AnomalyDeduplicator(dedup_config) if dedup_config else AnomalyDeduplicator()
    summary = SummaryBuilder()

    while True:
        poll_and_alert(
            aggregator,
            dispatcher,
            throttle=throttle,
            deduplicator=deduplicator,
            baseline=baseline,
            summary_builder=summary,
        )
        time.sleep(interval)
