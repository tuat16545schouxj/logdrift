"""Tests for logdrift.alert_config dispatcher factory."""

from __future__ import annotations

import pytest

from logdrift.alert import EmailChannel, WebhookChannel
from logdrift.alert_config import dispatcher_from_config


def test_empty_config_returns_empty_dispatcher():
    d = dispatcher_from_config({})
    assert d.channels == []


def test_webhook_channel_created():
    config = {
        "alerts": [
            {"type": "webhook", "url": "https://hooks.example.com/abc", "timeout": "5"}
        ]
    }
    d = dispatcher_from_config(config)
    assert len(d.channels) == 1
    ch = d.channels[0]
    assert isinstance(ch, WebhookChannel)
    assert ch.url == "https://hooks.example.com/abc"
    assert ch.timeout == 5


def test_email_channel_created():
    config = {
        "alerts": [
            {
                "type": "email",
                "smtp_host": "mail.example.com",
                "smtp_port": "587",
                "sender": "alert@example.com",
                "recipients": "ops@example.com, dev@example.com",
                "subject": "custom subject",
            }
        ]
    }
    d = dispatcher_from_config(config)
    assert len(d.channels) == 1
    ch = d.channels[0]
    assert isinstance(ch, EmailChannel)
    assert ch.smtp_host == "mail.example.com"
    assert ch.smtp_port == 587
    assert ch.recipients == ["ops@example.com", "dev@example.com"]
    assert ch.subject == "custom subject"


def test_multiple_channels():
    config = {
        "alerts": [
            {"type": "webhook", "url": "https://hooks.example.com/1"},
            {"type": "webhook", "url": "https://hooks.example.com/2"},
        ]
    }
    d = dispatcher_from_config(config)
    assert len(d.channels) == 2


def test_unknown_channel_type_raises():
    config = {"alerts": [{"type": "sms", "number": "+1234567890"}]}
    with pytest.raises(ValueError, match="Unknown alert channel type"):
        dispatcher_from_config(config)


def test_recipients_as_list():
    config = {
        "alerts": [
            {
                "type": "email",
                "smtp_host": "localhost",
                "sender": "a@b.com",
                "recipients": ["x@y.com", "z@w.com"],
            }
        ]
    }
    d = dispatcher_from_config(config)
    ch = d.channels[0]
    assert ch.recipients == ["x@y.com", "z@w.com"]
