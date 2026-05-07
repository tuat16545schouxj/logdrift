"""Deduplication of anomaly events within a rolling time window."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from logdrift.aggregator import AnomalyEvent


@dataclass
class DedupConfig:
    window_seconds: float = 60.0
    max_cache_size: int = 1000


@dataclass
class _CacheEntry:
    first_seen: float
    last_seen: float
    count: int = 1


def _event_fingerprint(event: AnomalyEvent) -> str:
    """Stable hash identifying an event by file, pattern name, and matched line."""
    raw = f"{event.filepath}|{event.pattern_name}|{event.line.strip()}"
    return hashlib.sha1(raw.encode()).hexdigest()


class AnomalyDeduplicator:
    """Suppress duplicate AnomalyEvents seen within a rolling time window."""

    def __init__(self, config: Optional[DedupConfig] = None) -> None:
        self._config = config or DedupConfig()
        self._cache: Dict[str, _CacheEntry] = {}

    def _evict_expired(self, now: float) -> None:
        cutoff = now - self._config.window_seconds
        expired = [k for k, v in self._cache.items() if v.last_seen < cutoff]
        for k in expired:
            del self._cache[k]

    def filter(self, events: List[AnomalyEvent]) -> List[AnomalyEvent]:
        """Return only events that are not duplicates within the current window."""
        now = time.time()
        self._evict_expired(now)

        result: List[AnomalyEvent] = []
        for event in events:
            fp = _event_fingerprint(event)
            if fp in self._cache:
                self._cache[fp].last_seen = now
                self._cache[fp].count += 1
            else:
                if len(self._cache) >= self._config.max_cache_size:
                    # evict oldest entry to stay within size limit
                    oldest = min(self._cache, key=lambda k: self._cache[k].last_seen)
                    del self._cache[oldest]
                self._cache[fp] = _CacheEntry(first_seen=now, last_seen=now)
                result.append(event)
        return result

    def duplicate_count(self, event: AnomalyEvent) -> int:
        """Return how many times this event has been seen (0 if unknown)."""
        fp = _event_fingerprint(event)
        entry = self._cache.get(fp)
        return entry.count if entry else 0

    def reset(self) -> None:
        """Clear the deduplication cache."""
        self._cache.clear()
