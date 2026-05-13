"""Integration helpers: combine EventSuppressor with the polling pipeline."""
from __future__ import annotations

import time
from typing import List, Optional

from logdrift.aggregator import AnomalyEvent, LogAggregator
from logdrift.suppression import EventSuppressor


def poll_with_suppression(
    aggregator: LogAggregator,
    suppressor: EventSuppressor,
    prune: bool = True,
) -> List[AnomalyEvent]:
    """Poll the aggregator once and filter events through the suppressor.

    Args:
        aggregator: The log aggregator to poll.
        suppressor: Active suppression rules.
        prune: If True, expired rules are pruned before filtering.

    Returns:
        Unsuppressed anomaly events.
    """
    if prune:
        suppressor.prune_expired()

    events = aggregator.poll_once()
    return suppressor.filter(events)


def run_suppression_loop(
    aggregator: LogAggregator,
    suppressor: EventSuppressor,
    interval: float = 5.0,
    max_iterations: Optional[int] = None,
) -> None:
    """Continuously poll and print unsuppressed events.

    Args:
        aggregator: The log aggregator.
        suppressor: Active suppression rules.
        interval: Seconds between polls.
        max_iterations: Stop after N iterations (None = run forever).
    """
    iteration = 0
    while max_iterations is None or iteration < max_iterations:
        events = poll_with_suppression(aggregator, suppressor)
        for event in events:
            print(event)
        time.sleep(interval)
        iteration += 1
