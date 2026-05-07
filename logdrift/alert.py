"""Alert channel abstractions for logdrift anomaly notifications."""

from __future__ import annotations

import json
import smtplib
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import List

from logdrift.aggregator import AnomalyEvent


class AlertChannel(ABC):
    """Base class for alert delivery channels."""

    @abstractmethod
    def send(self, events: List[AnomalyEvent]) -> None:
        """Send a batch of anomaly events through this channel."""


@dataclass
class WebhookChannel(AlertChannel):
    """Delivers alerts via HTTP POST to a webhook URL (e.g. Slack, Teams)."""

    url: str
    timeout: int = 10

    def send(self, events: List[AnomalyEvent]) -> None:
        if not events:
            return
        payload = json.dumps(
            {
                "anomalies": [
                    {
                        "file": e.filepath,
                        "pattern": e.pattern_name,
                        "line": e.line,
                        "timestamp": e.timestamp.isoformat(),
                    }
                    for e in events
                ]
            }
        ).encode()
        req = urllib.request.Request(
            self.url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout):
            pass


@dataclass
class EmailChannel(AlertChannel):
    """Delivers alerts via SMTP email."""

    smtp_host: str
    smtp_port: int
    sender: str
    recipients: List[str]
    subject: str = "logdrift anomaly alert"
    timeout: int = 10

    def send(self, events: List[AnomalyEvent]) -> None:
        if not events:
            return
        body_lines = [f"logdrift detected {len(events)} anomaly(ies):\n"]
        for e in events:
            body_lines.append(
                f"  [{e.timestamp.isoformat()}] {e.filepath} | {e.pattern_name}: {e.line}"
            )
        msg = EmailMessage()
        msg["Subject"] = self.subject
        msg["From"] = self.sender
        msg["To"] = ", ".join(self.recipients)
        msg.set_content("\n".join(body_lines))
        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=self.timeout) as smtp:
            smtp.send_message(msg)


@dataclass
class AlertDispatcher:
    """Dispatches anomaly events to one or more alert channels."""

    channels: List[AlertChannel] = field(default_factory=list)

    def add_channel(self, channel: AlertChannel) -> None:
        self.channels.append(channel)

    def dispatch(self, events: List[AnomalyEvent]) -> None:
        for channel in self.channels:
            channel.send(events)
