"""Command-line interface for logdrift."""

from __future__ import annotations

import argparse
import sys
import time

from logdrift.aggregator import LogAggregator
from logdrift.patterns import PatternRegistry
from logdrift.reporter import Reporter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="logdrift",
        description="Watch log files and surface anomalies using pattern matching.",
    )
    parser.add_argument(
        "files", nargs="+", metavar="FILE", help="Log file(s) to watch."
    )
    parser.add_argument(
        "--interval", type=float, default=2.0, metavar="SECS",
        help="Poll interval in seconds (default: 2.0).",
    )
    parser.add_argument(
        "--format", dest="fmt", choices=("text", "json"), default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Poll once and exit instead of running continuously.",
    )
    return parser


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    registry = PatternRegistry()
    aggregator = LogAggregator(registry)
    reporter = Reporter(fmt=args.fmt)

    for path in args.files:
        try:
            aggregator.add_file(path)
        except FileNotFoundError:
            print(f"[logdrift] Warning: file not found: {path}", file=sys.stderr)

    try:
        while True:
            events = aggregator.poll_once()
            if events:
                reporter.report(events)
            if args.once:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run())
