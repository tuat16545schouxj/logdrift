"""High-level polling loop that wires together aggregation, dedup, throttle,
rate-limiting, and alert dispatch."""

from __future__ import annotations

import time
import logging
from typing import Optional

from logdrift.aggregator import LogAggregator
from logdrift.dedup import AnomalyDeduplicator, DedupConfig
from logdrift.throttle import AnomalyThrottle, ThrottleConfig
from logdrift.ratelimit import SlidingWindowRateLimiter, RateLimitConfig
from logdrift.alert import AlertDispatcher
from logdrift.summary import SummaryBuilder

logger = logging.getLogger(__name__)


def poll_and_alert(
    aggregator: LogAggregator,
    dispatcher: AlertDispatcher,
    deduplicator: Optional[AnomalyDeduplicator] = None,
    throttle: Optional[AnomalyThrottle] = None,
    rate_limiter: Optional[SlidingWindowRateLimiter] = None,
    summary_builder: Optional[SummaryBuilder] = None,
) -> int:
    """Poll all watched files once, filter events, dispatch alerts.

    Returns the number of events actually dispatched.
    """
    raw_events = aggregator.poll_once()
    filtered = []

    for event in raw_events:
        if deduplicator and not deduplicator.is_new(event):
            logger.debug("dedup suppressed: %s", event)
            continue
        if throttle and not throttle.is_allowed(event):
            logger.debug("throttle suppressed: %s", event)
            continue
        if rate_limiter and not rate_limiter.is_allowed(event):
            logger.debug("rate-limit suppressed: %s", event)
            continue
        filtered.append(event)
        if summary_builder:
            summary_builder.add(event)

    if filtered:
        dispatcher.send(filtered)

    return len(filtered)


def run_loop(
    aggregator: LogAggregator,
    dispatcher: AlertDispatcher,
    interval: float = 5.0,
    dedup_config: Optional[DedupConfig] = None,
    throttle_config: Optional[ThrottleConfig] = None,
    ratelimit_config: Optional[RateLimitConfig] = None,
) -> None:
    """Run the polling loop indefinitely, blocking the calling thread."""
    deduplicator = AnomalyDeduplicator(dedup_config) if dedup_config else None
    throttle = AnomalyThrottle(throttle_config) if throttle_config else None
    rate_limiter = SlidingWindowRateLimiter(ratelimit_config) if ratelimit_config else None
    summary_builder = SummaryBuilder()

    logger.info("logdrift loop started (interval=%.1fs)", interval)
    while True:
        try:
            dispatched = poll_and_alert(
                aggregator, dispatcher, deduplicator, throttle, rate_limiter, summary_builder
            )
            if dispatched:
                logger.info("%d event(s) dispatched", dispatched)
        except Exception:
            logger.exception("error during poll cycle")
        time.sleep(interval)
