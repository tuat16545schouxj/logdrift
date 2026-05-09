"""Integration helpers: pipe aggregator output through a RetentionStore."""

from __future__ import annotations

import time
from typing import List

from logdrift.aggregator import AnomalyEvent, LogAggregator
from logdrift.retention import RetentionConfig, RetentionStore


def poll_with_retention(
    aggregator: LogAggregator,
    store: RetentionStore,
) -> List[AnomalyEvent]:
    """Poll the aggregator, persist new events in *store*, and return them."""
    new_events = aggregator.poll_once()
    store.add_many(new_events)
    return new_events


def run_retention_loop(
    aggregator: LogAggregator,
    store: RetentionStore,
    interval: float = 5.0,
    expire_interval: float = 60.0,
) -> None:  # pragma: no cover
    """Continuously poll and prune the retention store.

    Args:
        aggregator: The log aggregator to poll.
        store: The retention store to populate.
        interval: Seconds between poll cycles.
        expire_interval: Seconds between explicit expiry sweeps.
    """
    last_expire = time.time()
    while True:
        poll_with_retention(aggregator, store)
        now = time.time()
        if now - last_expire >= expire_interval:
            removed = store.expire()
            if removed:
                print(f"[retention] expired {removed} stale event(s)")
            last_expire = now
        time.sleep(interval)
