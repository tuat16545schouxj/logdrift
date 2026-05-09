"""Integration layer: route events then dispatch to per-destination alert channels."""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from logdrift.aggregator import AnomalyEvent
from logdrift.alert import AlertDispatcher
from logdrift.enriched_aggregator import EnrichedLogAggregator
from logdrift.routing import EventRouter


def poll_and_route_alert(
    aggregator: EnrichedLogAggregator,
    router: EventRouter,
    dispatchers: Dict[str, AlertDispatcher],
    fallback_dispatcher: Optional[AlertDispatcher] = None,
) -> Dict[str, List[AnomalyEvent]]:
    """Poll the aggregator once, route events, and send to the matching dispatcher.

    Returns the routing buckets so callers can inspect what was dispatched.
    """
    events: List[AnomalyEvent] = aggregator.poll_once()  # type: ignore[assignment]
    if not events:
        return {}

    buckets = router.route_many(events)  # type: ignore[arg-type]
    for destination, dest_events in buckets.items():
        dispatcher = dispatchers.get(destination, fallback_dispatcher)
        if dispatcher is not None:
            dispatcher.send(dest_events)  # type: ignore[arg-type]
    return buckets


def run_routed_loop(
    aggregator: EnrichedLogAggregator,
    router: EventRouter,
    dispatchers: Dict[str, AlertDispatcher],
    fallback_dispatcher: Optional[AlertDispatcher] = None,
    interval: float = 5.0,
    max_iterations: Optional[int] = None,
) -> None:
    """Run a continuous poll-route-alert loop.

    Parameters
    ----------
    aggregator:
        The log aggregator to poll.
    router:
        Routes events to destination tags.
    dispatchers:
        Maps destination tag -> :class:`AlertDispatcher`.
    fallback_dispatcher:
        Used when no dispatcher matches the destination tag.
    interval:
        Seconds to sleep between polls.
    max_iterations:
        Stop after this many iterations (useful for testing).
    """
    iteration = 0
    while True:
        poll_and_route_alert(aggregator, router, dispatchers, fallback_dispatcher)
        iteration += 1
        if max_iterations is not None and iteration >= max_iterations:
            break
        time.sleep(interval)
