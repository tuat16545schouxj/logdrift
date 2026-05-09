"""Tests for logdrift.tagging."""

from __future__ import annotations

import datetime
import pytest

from logdrift.aggregator import AnomalyEvent
from logdrift.tagging import TagRule, EventTagger, tagger_from_config


def make_event(line: str = "ERROR something failed", filepath: str = "/var/log/app.log") -> AnomalyEvent:
    return AnomalyEvent(
        filepath=filepath,
        line=line,
        pattern_name="error",
        timestamp=datetime.datetime(2024, 1, 1, 12, 0, 0),
    )


# --- TagRule ---

def test_tag_rule_matches_line():
    rule = TagRule(tag="critical", pattern=r"critical")
    event = make_event(line="CRITICAL disk full")
    assert rule.matches(event)


def test_tag_rule_no_match():
    rule = TagRule(tag="critical", pattern=r"critical")
    event = make_event(line="INFO everything is fine")
    assert not rule.matches(event)


def test_tag_rule_filepath_scoped_match():
    rule = TagRule(tag="nginx", pattern=r"error", filepath_pattern=r"nginx")
    event = make_event(line="error 404", filepath="/var/log/nginx/access.log")
    assert rule.matches(event)


def test_tag_rule_filepath_scoped_no_match():
    rule = TagRule(tag="nginx", pattern=r"error", filepath_pattern=r"nginx")
    event = make_event(line="error 404", filepath="/var/log/app.log")
    assert not rule.matches(event)


def test_tag_rule_case_insensitive():
    rule = TagRule(tag="oom", pattern=r"out of memory")
    event = make_event(line="Out Of Memory killer invoked")
    assert rule.matches(event)


# --- EventTagger ---

def test_tagger_no_rules_returns_empty_tags():
    tagger = EventTagger()
    assert tagger.tags_for(make_event()) == []


def test_tagger_single_matching_rule():
    tagger = EventTagger([TagRule(tag="error", pattern=r"error")])
    assert tagger.tags_for(make_event(line="ERROR boom")) == ["error"]


def test_tagger_multiple_rules_all_match():
    tagger = EventTagger([
        TagRule(tag="error", pattern=r"error"),
        TagRule(tag="critical", pattern=r"critical"),
    ])
    tags = tagger.tags_for(make_event(line="CRITICAL ERROR meltdown"))
    assert tags == ["critical", "error"]


def test_tagger_deduplicates_tags():
    tagger = EventTagger([
        TagRule(tag="error", pattern=r"error"),
        TagRule(tag="error", pattern=r"fail"),
    ])
    tags = tagger.tags_for(make_event(line="error fail"))
    assert tags == ["error"]


def test_tagger_tag_event_returns_dict_with_tags():
    tagger = EventTagger([TagRule(tag="db", pattern=r"database")])
    event = make_event(line="database connection lost")
    result = tagger.tag_event(event)
    assert result["tags"] == ["db"]
    assert result["event"] is event


# --- tagger_from_config ---

def test_tagger_from_config_empty():
    tagger = tagger_from_config([])
    assert tagger.tags_for(make_event()) == []


def test_tagger_from_config_creates_rules():
    config = [
        {"tag": "auth", "pattern": r"authentication failed"},
        {"tag": "disk", "pattern": r"no space left", "filepath_pattern": r"syslog"},
    ]
    tagger = tagger_from_config(config)
    assert tagger.tags_for(make_event(line="authentication failed for user root")) == ["auth"]


def test_tagger_from_config_filepath_pattern_respected():
    config = [{"tag": "disk", "pattern": r"no space left", "filepath_pattern": r"syslog"}]
    tagger = tagger_from_config(config)
    event_match = make_event(line="no space left on device", filepath="/var/log/syslog")
    event_no_match = make_event(line="no space left on device", filepath="/var/log/app.log")
    assert tagger.tags_for(event_match) == ["disk"]
    assert tagger.tags_for(event_no_match) == []
