"""Build an EventRouter from a plain-dict config or a TOML file."""

from __future__ import annotations

from typing import Any, Dict, List

from logdrift.routing import EventRouter, RoutingRule


def router_from_config(
    config: Dict[str, Any],
    default_destination: str = "default",
) -> EventRouter:
    """Build an :class:`EventRouter` from a config dict.

    Expected shape::

        {
            "default_destination": "ops",
            "rules": [
                {
                    "destination": "security",
                    "filepath_pattern": "auth",
                    "pattern_name": "error",
                    "line_regex": "failed login"
                }
            ]
        }
    """
    default = config.get("default_destination", default_destination)
    rules: List[RoutingRule] = []
    for raw in config.get("rules", []):
        if "destination" not in raw:
            raise ValueError("Each routing rule must have a 'destination' key.")
        rules.append(
            RoutingRule(
                destination=raw["destination"],
                filepath_pattern=raw.get("filepath_pattern"),
                pattern_name=raw.get("pattern_name"),
                line_regex=raw.get("line_regex"),
            )
        )
    return EventRouter(rules=rules, default_destination=default)


def router_from_toml(path: str) -> EventRouter:
    """Load routing config from a TOML file and return an :class:`EventRouter`."""
    try:
        import tomllib  # Python 3.11+
    except ImportError:  # pragma: no cover
        import tomli as tomllib  # type: ignore

    with open(path, "rb") as fh:
        data = tomllib.load(fh)

    return router_from_config(data.get("routing", {}))
