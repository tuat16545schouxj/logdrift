"""Integration helpers: wire AlertDispatcher into the poll loop."""

from __future__ import annotations

from typing import List, Optional

from logdrift.aggregator import AnomalyEvent, LogAggregator
from logdrift.alert import AlertDispatcher


def poll_and_alert(
    aggregator: LogAggregator,
    dispatcher: AlertDispatcher,
    min_events: int = 1,
) -> List[AnomalyEvent]:
    """Run one poll cycle and dispatch any anomalies that exceed *min_events*.

    Parameters
    ----------
    aggregator:
        A configured :class:`~logdrift.aggregator.LogAggregator`.
    dispatcher:
        An :class:`~logdrift.alert.AlertDispatcher` with one or more channels.
    min_events:
        Only dispatch when at least this many events are found in a single
        poll cycle.  Defaults to ``1`` (dispatch on every anomaly).

    Returns
    -------
    list
        The anomaly events found during this cycle (may be empty).
    """
    events: List[AnomalyEvent] = aggregator.poll_once()
    if len(events) >= min_events:
        dispatcher.dispatch(events)
    return events


def run_loop(
    aggregator: LogAggregator,
    dispatcher: AlertDispatcher,
    interval: float = 5.0,
    min_events: int = 1,
    iterations: Optional[int] = None,
) -> None:
    """Continuously poll and alert in a blocking loop.

    Parameters
    ----------
    aggregator:
        A configured :class:`~logdrift.aggregator.LogAggregator`.
    dispatcher:
        Alert dispatcher to use for delivery.
    interval:
        Seconds to sleep between poll cycles.
    min_events:
        Minimum anomaly count per cycle to trigger an alert.
    iterations:
        If set, stop after this many cycles (useful for testing).
    """
    import time

    count = 0
    while True:
        poll_and_alert(aggregator, dispatcher, min_events=min_events)
        count += 1
        if iterations is not None and count >= iterations:
            break
        time.sleep(interval)
