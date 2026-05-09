"""High-level helper: poll aggregator, correlate events, emit incidents."""
from __future__ import annotations

import time
from typing import Callable, List, Optional

from logdrift.aggregator import LogAggregator
from logdrift.correlation import CorrelationConfig, EventCorrelator, Incident


def poll_and_correlate(
    aggregator: LogAggregator,
    correlator: EventCorrelator,
    on_incident: Callable[[Incident], None],
) -> List[Incident]:
    """Poll the aggregator once and feed events into the correlator.

    Calls *on_incident* for every new Incident produced.
    Returns the list of incidents emitted during this poll.
    """
    events = aggregator.poll_once()
    incidents = correlator.add_many(events)
    for inc in incidents:
        on_incident(inc)
    return incidents


def run_correlation_loop(
    aggregator: LogAggregator,
    correlator: EventCorrelator,
    on_incident: Callable[[Incident], None],
    interval: float = 5.0,
    max_iterations: Optional[int] = None,
) -> None:  # pragma: no cover
    """Blocking loop that polls and correlates at *interval* seconds."""
    iterations = 0
    while True:
        poll_and_correlate(aggregator, correlator, on_incident)
        iterations += 1
        if max_iterations is not None and iterations >= max_iterations:
            break
        time.sleep(interval)
