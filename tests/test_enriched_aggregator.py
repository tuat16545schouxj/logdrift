"""Tests for logdrift.enriched_aggregator."""

import pytest

from logdrift.enriched_aggregator import EnrichedAnomalyEvent, EnrichedLogAggregator
from logdrift.enrichment import Enricher, EnrichmentRule
from logdrift.patterns import PatternRegistry


@pytest.fixture()
def tmp_log(tmp_path):
    p = tmp_path / "app.log"
    p.write_text("")
    return p


@pytest.fixture()
def registry():
    r = PatternRegistry()
    return r


@pytest.fixture()
def simple_enricher():
    e = Enricher()
    e.add_rule(EnrichmentRule.compile("ip", r"(?P<ip>\b(?:\d{1,3}\.){3}\d{1,3}\b)"))
    e.add_rule(EnrichmentRule.compile("level", r"\b(?P<log_level>ERROR|CRITICAL)\b"))
    return e


# ---------------------------------------------------------------------------
# EnrichedAnomalyEvent
# ---------------------------------------------------------------------------

def test_enriched_event_has_metadata_field():
    ev = EnrichedAnomalyEvent(
        filepath="/var/log/app.log",
        line="ERROR from 1.2.3.4",
        pattern_name="error",
        metadata={"ip": "1.2.3.4", "log_level": "ERROR"},
    )
    assert ev.metadata["ip"] == "1.2.3.4"
    assert ev.metadata["log_level"] == "ERROR"


def test_enriched_event_metadata_defaults_to_empty():
    ev = EnrichedAnomalyEvent(
        filepath="/var/log/app.log",
        line="plain line",
        pattern_name="error",
    )
    assert ev.metadata == {}


# ---------------------------------------------------------------------------
# EnrichedLogAggregator — no anomalies
# ---------------------------------------------------------------------------

def test_poll_once_no_anomaly_returns_empty(tmp_log, registry, simple_enricher):
    agg = EnrichedLogAggregator(registry=registry, enricher=simple_enricher)
    agg.add_file(str(tmp_log))
    tmp_log.write_text("everything is fine\n")
    events = agg.poll_once()
    assert events == []


# ---------------------------------------------------------------------------
# EnrichedLogAggregator — with anomalies
# ---------------------------------------------------------------------------

def test_poll_once_enriches_anomaly(tmp_log, simple_enricher):
    reg = PatternRegistry()
    agg = EnrichedLogAggregator(registry=reg, enricher=simple_enricher)
    agg.add_file(str(tmp_log))
    tmp_log.write_text("CRITICAL failure at 10.0.0.1\n")
    events = agg.poll_once()
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, EnrichedAnomalyEvent)
    assert ev.metadata.get("ip") == "10.0.0.1"
    assert ev.metadata.get("log_level") == "CRITICAL"


def test_poll_once_no_metadata_when_no_match(tmp_log):
    reg = PatternRegistry()
    enricher = Enricher()
    enricher.add_rule(EnrichmentRule.compile("ip", r"(?P<ip>\b(?:\d{1,3}\.){3}\d{1,3}\b)"))
    agg = EnrichedLogAggregator(registry=reg, enricher=enricher)
    agg.add_file(str(tmp_log))
    tmp_log.write_text("ERROR no ip in this line\n")
    events = agg.poll_once()
    assert len(events) == 1
    assert events[0].metadata == {}


def test_default_enricher_used_when_none_provided(tmp_log):
    reg = PatternRegistry()
    agg = EnrichedLogAggregator(registry=reg, enricher=None)
    agg.add_file(str(tmp_log))
    tmp_log.write_text("ERROR request from 192.168.0.1\n")
    events = agg.poll_once()
    assert len(events) == 1
    assert events[0].metadata.get("ip") == "192.168.0.1"
