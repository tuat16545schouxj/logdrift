"""Integration helpers: poll aggregator, throttle, alert, and summarise."""

from __future__ import annotations

import time
import logging
from typing import Optional

from logdrift.aggregator import LogAggregator
from logdrift.throttle import AnomalyThrottle
from logdrift.baseline import BaselineStore
from logdrift.alert import AlertDispatcher
from logdrift.summary import SummaryBuilder

logger = logging.getLogger(__name__)


def poll_and_alert(
    aggregator: LogAggregator,
    dispatcher: AlertDispatcher,
    throttle: Optional[AnomalyThrottle] = None,
    summary_builder: Optional[SummaryBuilder] = None,
) -> int:
    """Poll the aggregator once, filter through throttle, fire alerts.

    Returns the number of events dispatched.
    """
    events = aggregator.poll_once()

    if throttle is not None:
        events = throttle.filter(events)

    if summary_builder is not None:
        for ev in events:
            summary_builder.add(ev)

    if events:
        dispatcher.send(events)
        logger.debug("Dispatched %d anomaly event(s).", len(events))

    return len(events)


def run_loop(
    aggregator: LogAggregator,
    dispatcher: AlertDispatcher,
    throttle: Optional[AnomalyThrottle] = None,
    poll_interval: float = 5.0,
    summary_interval: float = 300.0,
    summary_builder: Optional[SummaryBuilder] = None,
) -> None:  # pragma: no cover
    """Run the poll-alert loop indefinitely.

    Logs a periodic summary when *summary_builder* is provided.
    """
    last_summary = time.monotonic()

    logger.info(
        "logdrift loop started (poll=%.1fs, summary=%.1fs)",
        poll_interval,
        summary_interval,
    )

    while True:
        try:
            poll_and_alert(aggregator, dispatcher, throttle, summary_builder)
        except Exception:  # noqa: BLE001
            logger.exception("Error during poll cycle.")

        now = time.monotonic()
        if summary_builder is not None and (now - last_summary) >= summary_interval:
            report = summary_builder.build()
            logger.info("\n%s", report)
            last_summary = now

        time.sleep(poll_interval)
