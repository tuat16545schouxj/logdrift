"""Tests for logdrift.enrichment."""

import pytest

from logdrift.enrichment import EnrichmentRule, Enricher, default_enricher


# ---------------------------------------------------------------------------
# EnrichmentRule
# ---------------------------------------------------------------------------

def test_compile_requires_named_group():
    with pytest.raises(ValueError, match="named group"):
        EnrichmentRule.compile("bad", r"\d+")


def test_extract_returns_none_on_no_match():
    rule = EnrichmentRule.compile("ip", r"(?P<ip>\b(?:\d{1,3}\.){3}\d{1,3}\b)")
    assert rule.extract("no ip here") is None


def test_extract_returns_matched_fields():
    rule = EnrichmentRule.compile("ip", r"(?P<ip>\b(?:\d{1,3}\.){3}\d{1,3}\b)")
    result = rule.extract("client 192.168.1.1 connected")
    assert result == {"ip": "192.168.1.1"}


def test_extract_multiple_groups():
    rule = EnrichmentRule.compile(
        "kv", r"user=(?P<user>\w+)\s+action=(?P<action>\w+)"
    )
    result = rule.extract("user=alice action=login")
    assert result == {"user": "alice", "action": "login"}


# ---------------------------------------------------------------------------
# Enricher
# ---------------------------------------------------------------------------

def test_enrich_empty_rules_returns_empty_dict():
    enricher = Enricher()
    assert enricher.enrich("any log line") == {}


def test_enrich_applies_all_matching_rules():
    enricher = Enricher()
    enricher.add_rule(EnrichmentRule.compile("ip", r"(?P<ip>\b(?:\d{1,3}\.){3}\d{1,3}\b)"))
    enricher.add_rule(EnrichmentRule.compile("level", r"\b(?P<log_level>ERROR|INFO)\b"))
    result = enricher.enrich("ERROR from 10.0.0.1")
    assert result["ip"] == "10.0.0.1"
    assert result["log_level"] == "ERROR"


def test_enrich_later_rule_overrides_earlier():
    enricher = Enricher()
    enricher.add_rule(EnrichmentRule.compile("r1", r"(?P<tag>foo)"))
    enricher.add_rule(EnrichmentRule.compile("r2", r"(?P<tag>bar)"))
    result = enricher.enrich("foo bar")
    assert result["tag"] == "bar"


def test_enrich_non_matching_rule_skipped():
    enricher = Enricher()
    enricher.add_rule(EnrichmentRule.compile("ip", r"(?P<ip>\b(?:\d{1,3}\.){3}\d{1,3}\b)"))
    result = enricher.enrich("no ip address present")
    assert result == {}


# ---------------------------------------------------------------------------
# default_enricher
# ---------------------------------------------------------------------------

def test_default_enricher_extracts_ip():
    e = default_enricher()
    assert e.enrich("request from 172.16.0.5")["ip"] == "172.16.0.5"


def test_default_enricher_extracts_log_level():
    e = default_enricher()
    assert e.enrich("2024-01-01 ERROR something failed")["log_level"] == "ERROR"


def test_default_enricher_extracts_http_status():
    e = default_enricher()
    assert e.enrich("HTTP/1.1 404 Not Found")["http_status"] == "404"


def test_default_enricher_extracts_request_id():
    e = default_enricher()
    assert e.enrich("request_id=abc-123 processing")["request_id"] == "abc-123"


def test_default_enricher_no_match_returns_empty():
    e = default_enricher()
    result = e.enrich("just a plain log line with nothing special")
    assert result == {}
