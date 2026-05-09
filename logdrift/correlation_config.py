"""Load CorrelationConfig from a dict or TOML file."""
from __future__ import annotations

from typing import Any, Dict

from logdrift.correlation import CorrelationConfig


def correlator_config_from_dict(data: Dict[str, Any]) -> CorrelationConfig:
    """Build a CorrelationConfig from a plain dict (e.g. parsed TOML section)."""
    section = data.get("correlation", {})
    window = float(section.get("window_seconds", 60.0))
    min_events = int(section.get("min_events", 2))
    group_by = str(section.get("group_by", "pattern_name"))
    if group_by not in ("pattern_name", "filepath"):
        raise ValueError(
            f"correlation.group_by must be 'pattern_name' or 'filepath', got {group_by!r}"
        )
    return CorrelationConfig(
        window_seconds=window,
        min_events=min_events,
        group_by=group_by,
    )


def correlator_config_from_toml(path: str) -> CorrelationConfig:
    """Load CorrelationConfig from a TOML file."""
    try:
        import tomllib  # Python 3.11+
    except ImportError:  # pragma: no cover
        import tomli as tomllib  # type: ignore

    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    return correlator_config_from_dict(data)
