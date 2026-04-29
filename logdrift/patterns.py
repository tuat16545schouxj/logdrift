"""Pattern matching module for logdrift.

Defines built-in anomaly patterns and a registry for matching log lines.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Pattern:
    """A named regex pattern with an associated severity level."""

    name: str
    regex: str
    severity: str  # "low", "medium", "high", "critical"
    description: str = ""
    _compiled: Optional[re.Pattern] = field(default=None, init=False, repr=False)

    def compile(self) -> None:
        self._compiled = re.compile(self.regex, re.IGNORECASE)

    def match(self, line: str) -> Optional[re.Match]:
        if self._compiled is None:
            self.compile()
        return self._compiled.search(line)


DEFAULT_PATTERNS: List[Pattern] = [
    Pattern(
        name="error",
        regex=r"\b(error|err)\b",
        severity="medium",
        description="Generic error keyword",
    ),
    Pattern(
        name="critical",
        regex=r"\b(critical|crit|fatal)\b",
        severity="critical",
        description="Critical or fatal condition",
    ),
    Pattern(
        name="warning",
        regex=r"\b(warning|warn)\b",
        severity="low",
        description="Warning condition",
    ),
    Pattern(
        name="exception",
        regex=r"(exception|traceback|panic)",
        severity="high",
        description="Exception or traceback detected",
    ),
    Pattern(
        name="oom",
        regex=r"out of memory|oom.?kill",
        severity="critical",
        description="Out-of-memory event",
    ),
    Pattern(
        name="timeout",
        regex=r"timed? ?out|connection timeout",
        severity="medium",
        description="Timeout event",
    ),
]


class PatternRegistry:
    """Registry that holds patterns and matches them against log lines."""

    def __init__(self, patterns: Optional[List[Pattern]] = None) -> None:
        self._patterns: List[Pattern] = patterns if patterns is not None else list(DEFAULT_PATTERNS)
        for p in self._patterns:
            p.compile()

    def add_pattern(self, pattern: Pattern) -> None:
        pattern.compile()
        self._patterns.append(pattern)

    def match_line(self, line: str) -> List[Pattern]:
        """Return all patterns that match the given log line."""
        return [p for p in self._patterns if p.match(line)]

    @property
    def patterns(self) -> List[Pattern]:
        return list(self._patterns)
