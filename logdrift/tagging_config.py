"""Load EventTagger configuration from a TOML file or dict."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List

from logdrift.tagging import EventTagger, tagger_from_config

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


def tagger_from_dict(data: Dict[str, Any]) -> EventTagger:
    """Build an EventTagger from a parsed config dict.

    Expected shape::

        [tagging]
        [[tagging.rules]]
        tag = "auth"
        pattern = "authentication failed"
        filepath_pattern = "auth.log"   # optional

    """
    rules_data: List[Dict[str, str]] = (
        data.get("tagging", {}).get("rules", [])
    )
    return tagger_from_config(rules_data)


def tagger_from_toml(path: str | Path) -> EventTagger:
    """Load an EventTagger from a TOML config file."""
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    return tagger_from_dict(data)
