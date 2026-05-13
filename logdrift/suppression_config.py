"""Load suppression rules from a dict or TOML file."""
from __future__ import annotations

import time
from typing import Any, Dict, List

from logdrift.suppression import EventSuppressor, SuppressionRule


def _parse_ttl(ttl: Any) -> float | None:
    """Convert a TTL value in seconds to an absolute expiry timestamp."""
    if ttl is None:
        return None
    return time.time() + float(ttl)


def suppressor_from_config(config: Dict[str, Any]) -> EventSuppressor:
    """Build an EventSuppressor from a plain dict.

    Expected structure::

        {
            "rules": [
                {
                    "name": "ignore-healthcheck",
                    "line_pattern": "healthcheck",
                    "filepath_pattern": None,
                    "pattern_name": None,
                    "ttl_seconds": 3600
                }
            ]
        }
    """
    rules: List[SuppressionRule] = []
    for entry in config.get("rules", []):
        expires_at = _parse_ttl(entry.get("ttl_seconds"))
        rule = SuppressionRule(
            name=entry["name"],
            line_pattern=entry.get("line_pattern"),
            filepath_pattern=entry.get("filepath_pattern"),
            pattern_name=entry.get("pattern_name"),
            expires_at=expires_at,
        )
        rules.append(rule)
    return EventSuppressor(rules=rules)


def suppressor_from_toml(path: str) -> EventSuppressor:
    """Load suppression config from a TOML file."""
    try:
        import tomllib  # type: ignore
    except ImportError:  # Python < 3.11
        import tomli as tomllib  # type: ignore

    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    return suppressor_from_config(data.get("suppression", {}))
