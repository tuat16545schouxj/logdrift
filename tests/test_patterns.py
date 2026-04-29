"""Tests for logdrift.patterns module."""

import pytest

from logdrift.patterns import DEFAULT_PATTERNS, Pattern, PatternRegistry


def test_default_patterns_exist():
    assert len(DEFAULT_PATTERNS) > 0


def test_pattern_match_case_insensitive():
    p = Pattern(name="error", regex=r"\berror\b", severity="medium")
    assert p.match("An ERROR occurred") is not None
    assert p.match("everything is fine") is None


def test_pattern_no_false_positive():
    p = Pattern(name="warning", regex=r"\bwarn\b", severity="low")
    assert p.match("no issues here") is None


def test_registry_default_patterns():
    registry = PatternRegistry()
    assert len(registry.patterns) == len(DEFAULT_PATTERNS)


def test_registry_match_error_line():
    registry = PatternRegistry()
    matches = registry.match_line("2024-01-01 ERROR: disk full")
    names = [p.name for p in matches]
    assert "error" in names


def test_registry_match_critical_line():
    registry = PatternRegistry()
    matches = registry.match_line("FATAL: kernel panic")
    names = [p.name for p in matches]
    assert "critical" in names


def test_registry_match_exception_line():
    registry = PatternRegistry()
    matches = registry.match_line("Traceback (most recent call last):")
    names = [p.name for p in matches]
    assert "exception" in names


def test_registry_no_match_clean_line():
    registry = PatternRegistry()
    matches = registry.match_line("INFO: server started successfully on port 8080")
    assert matches == []


def test_registry_add_custom_pattern():
    registry = PatternRegistry()
    custom = Pattern(name="auth_fail", regex=r"authentication failed", severity="high")
    registry.add_pattern(custom)
    matches = registry.match_line("Authentication failed for user admin")
    names = [p.name for p in matches]
    assert "auth_fail" in names


def test_registry_multiple_matches():
    registry = PatternRegistry()
    matches = registry.match_line("CRITICAL ERROR: out of memory")
    names = [p.name for p in matches]
    assert "error" in names
    assert "critical" in names
    assert "oom" in names


def test_registry_empty_patterns():
    registry = PatternRegistry(patterns=[])
    assert registry.match_line("ERROR: something") == []
