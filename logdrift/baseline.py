"""Baseline persistence for anomaly suppression.

Stores known-good patterns so that recurring expected anomalies
(e.g. scheduled job errors) are not re-surfaced on every run.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class BaselineEntry:
    pattern_name: str
    source_file: str
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    occurrence_count: int = 1

    def touch(self) -> None:
        """Update last_seen and increment counter."""
        self.last_seen = time.time()
        self.occurrence_count += 1


class BaselineStore:
    """Persist and query baseline entries backed by a JSON file."""

    def __init__(self, path: str | os.PathLike = ".logdrift_baseline.json") -> None:
        self._path = Path(path)
        self._entries: Dict[str, BaselineEntry] = {}
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_known(self, pattern_name: str, source_file: str) -> bool:
        """Return True if this (pattern, file) pair is already baselined."""
        return self._make_key(pattern_name, source_file) in self._entries

    def record(self, pattern_name: str, source_file: str) -> BaselineEntry:
        """Record an occurrence; create entry if new, otherwise touch it."""
        key = self._make_key(pattern_name, source_file)
        if key in self._entries:
            self._entries[key].touch()
        else:
            self._entries[key] = BaselineEntry(
                pattern_name=pattern_name,
                source_file=source_file,
            )
        self._save()
        return self._entries[key]

    def all_entries(self) -> List[BaselineEntry]:
        return list(self._entries.values())

    def clear(self) -> None:
        self._entries.clear()
        self._save()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_key(pattern_name: str, source_file: str) -> str:
        return f"{pattern_name}::{source_file}"

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text())
            for key, data in raw.items():
                self._entries[key] = BaselineEntry(**data)
        except (json.JSONDecodeError, TypeError, KeyError):
            # Corrupt file — start fresh
            self._entries = {}

    def _save(self) -> None:
        self._path.write_text(
            json.dumps(
                {k: asdict(v) for k, v in self._entries.items()},
                indent=2,
            )
        )
