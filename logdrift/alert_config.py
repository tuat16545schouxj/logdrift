"""Load alert channel configuration from a TOML or dict source."""

from __future__ import annotations

from typing import Any, Dict, List

from logdrift.alert import AlertChannel, AlertDispatcher, EmailChannel, WebhookChannel


def _build_channel(cfg: Dict[str, Any]) -> AlertChannel:
    kind = cfg.get("type", "").lower()
    if kind == "webhook":
        return WebhookChannel(
            url=cfg["url"],
            timeout=int(cfg.get("timeout", 10)),
        )
    if kind == "email":
        recipients = cfg["recipients"]
        if isinstance(recipients, str):
            recipients = [r.strip() for r in recipients.split(",")]
        return EmailChannel(
            smtp_host=cfg["smtp_host"],
            smtp_port=int(cfg.get("smtp_port", 25)),
            sender=cfg["sender"],
            recipients=recipients,
            subject=cfg.get("subject", "logdrift anomaly alert"),
            timeout=int(cfg.get("timeout", 10)),
        )
    raise ValueError(f"Unknown alert channel type: {kind!r}")


def dispatcher_from_config(config: Dict[str, Any]) -> AlertDispatcher:
    """Build an AlertDispatcher from a configuration mapping.

    Expected structure::

        {
            "alerts": [
                {"type": "webhook", "url": "https://..."},
                {"type": "email", "smtp_host": "...", ...},
            ]
        }
    """
    dispatcher = AlertDispatcher()
    for channel_cfg in config.get("alerts", []):
        dispatcher.add_channel(_build_channel(channel_cfg))
    return dispatcher


def dispatcher_from_toml(path: str) -> AlertDispatcher:
    """Load alert configuration from a TOML file."""
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]

    with open(path, "rb") as fh:
        config = tomllib.load(fh)
    return dispatcher_from_config(config)
