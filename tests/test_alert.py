"""Tests for logdrift.alert channel abstractions."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from logdrift.aggregator import AnomalyEvent
from logdrift.alert import AlertDispatcher, WebhookChannel, EmailChannel


def make_event(filepath="app.log", pattern_name="error", line="ERROR: boom"):
    e = AnomalyEvent(filepath=filepath, pattern_name=pattern_name, line=line)
    return e


# ---------------------------------------------------------------------------
# WebhookChannel
# ---------------------------------------------------------------------------

class TestWebhookChannel:
    def test_send_empty_events_does_nothing(self):
        ch = WebhookChannel(url="http://example.com/hook")
        with patch("urllib.request.urlopen") as mock_open:
            ch.send([])
            mock_open.assert_not_called()

    def test_send_posts_json(self):
        ch = WebhookChannel(url="http://example.com/hook", timeout=5)
        event = make_event()
        captured = {}

        def fake_urlopen(req, timeout):
            captured["url"] = req.full_url
            captured["method"] = req.method
            captured["body"] = json.loads(req.data)
            captured["timeout"] = timeout
            return MagicMock().__enter__.return_value

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            ch.send([event])

        assert captured["url"] == "http://example.com/hook"
        assert captured["method"] == "POST"
        assert captured["timeout"] == 5
        anomalies = captured["body"]["anomalies"]
        assert len(anomalies) == 1
        assert anomalies[0]["file"] == "app.log"
        assert anomalies[0]["pattern"] == "error"


# ---------------------------------------------------------------------------
# EmailChannel
# ---------------------------------------------------------------------------

class TestEmailChannel:
    def _make_channel(self):
        return EmailChannel(
            smtp_host="localhost",
            smtp_port=25,
            sender="logdrift@example.com",
            recipients=["ops@example.com"],
        )

    def test_send_empty_events_does_nothing(self):
        ch = self._make_channel()
        with patch("smtplib.SMTP") as mock_smtp:
            ch.send([])
            mock_smtp.assert_not_called()

    def test_send_constructs_email(self):
        ch = self._make_channel()
        event = make_event()
        mock_smtp_instance = MagicMock()
        mock_smtp_instance.__enter__ = MagicMock(return_value=mock_smtp_instance)
        mock_smtp_instance.__exit__ = MagicMock(return_value=False)

        with patch("smtplib.SMTP", return_value=mock_smtp_instance):
            ch.send([event])

        mock_smtp_instance.send_message.assert_called_once()
        msg = mock_smtp_instance.send_message.call_args[0][0]
        assert msg["From"] == "logdrift@example.com"
        assert "ops@example.com" in msg["To"]
        assert "ERROR: boom" in msg.get_content()


# ---------------------------------------------------------------------------
# AlertDispatcher
# ---------------------------------------------------------------------------

class TestAlertDispatcher:
    def test_dispatch_calls_all_channels(self):
        ch1 = MagicMock()
        ch2 = MagicMock()
        dispatcher = AlertDispatcher(channels=[ch1, ch2])
        events = [make_event()]
        dispatcher.dispatch(events)
        ch1.send.assert_called_once_with(events)
        ch2.send.assert_called_once_with(events)

    def test_add_channel(self):
        dispatcher = AlertDispatcher()
        ch = MagicMock()
        dispatcher.add_channel(ch)
        assert ch in dispatcher.channels
