"""Summarise events.csv logs into a grouped summary.csv.

See spec.md. Python standard library only.
"""
from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from datetime import datetime, timezone

REQUIRED_COLUMNS = ("timestamp", "level", "service", "message")
OUTPUT_COLUMNS = ("service", "level", "message", "count", "first_seen", "last_seen")


def normalise_message(message: str) -> str:
    """Strip and collapse internal whitespace runs to a single space (spec Q2)."""
    return " ".join((message or "").split())


def normalise_level(level: str) -> str:
    """Strip and upper-case; blank/missing becomes the UNKNOWN sentinel (spec Q2, Q4)."""
    cleaned = (level or "").strip().upper()
    return cleaned or "UNKNOWN"


def normalise_service(service: str) -> str:
    """Strip surrounding whitespace; case preserved (spec Q2)."""
    return (service or "").strip()


def parse_timestamp(raw: str) -> datetime | None:
    """Parse an ISO-8601 timestamp to an aware UTC datetime, or None if invalid (spec Q5)."""
    text = (raw or "").strip()
    if not text:
        return None
    if text[-1] in ("Z", "z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass
class _Group:
    """Running aggregate for one (service, level, message) group."""

    count: int = 0
    first_dt: datetime | None = None
    first_str: str = ""
    last_dt: datetime | None = None
    last_str: str = ""

    def add(self, dt: datetime | None, raw_ts: str) -> None:
        """Count a row; track earliest/latest valid timestamp by UTC instant."""
        self.count += 1
        # Malformed timestamps are counted but excluded from first/last_seen (spec Q5).
        if dt is None:
            return
        if self.first_dt is None or dt < self.first_dt:
            self.first_dt, self.first_str = dt, raw_ts
        if self.last_dt is None or dt > self.last_dt:
            self.last_dt, self.last_str = dt, raw_ts


def summarise(rows):
    """Group rows by (service, level, normalised message) and sort deterministically."""
    groups: dict[tuple[str, str, str], _Group] = {}
    for row in rows:
        key = (
            normalise_service(row.get("service")),
            normalise_level(row.get("level")),
            normalise_message(row.get("message")),
        )
        raw_ts = (row.get("timestamp") or "").strip()
        groups.setdefault(key, _Group()).add(parse_timestamp(raw_ts), raw_ts)

    records = [
        {
            "service": service,
            "level": level,
            "message": message,
            "count": g.count,
            "first_seen": g.first_str,
            "last_seen": g.last_str,
        }
        for (service, level, message), g in groups.items()
    ]
    # Sort: count desc, then service, level, message asc (spec section 3).
    records.sort(key=lambda r: (-r["count"], r["service"], r["level"], r["message"]))
    return records


def read_events(path):
    """Read events from a CSV file. Returns (rows, error_message)."""
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            return [], None  # empty file: zero events (spec Q6)
        missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing:
            return None, f"input is missing required column(s): {', '.join(missing)}"
        return list(reader), None


def write_summary(path, records):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(OUTPUT_COLUMNS)
        for r in records:
            writer.writerow([r[c] for c in OUTPUT_COLUMNS])


def build_parser():
    parser = argparse.ArgumentParser(
        prog="logsum",
        description="Summarise events.csv logs into a grouped summary.csv.",
    )
    parser.add_argument("input", help="path to the input events CSV")
    parser.add_argument("output", nargs="?", default=None,
                        help="output summary CSV path (default: summary.csv)")
    parser.add_argument("-o", "--output", dest="output_flag", default=None,
                        help="output summary CSV path (overrides positional)")
    parser.add_argument("--min-count", dest="min_count", type=int, default=None,
                        metavar="N",
                        help="only output groups whose count is >= N")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    out_path = args.output_flag or args.output or "summary.csv"

    try:
        rows, error = read_events(args.input)
    except OSError as exc:
        print(f"logsum: cannot read input: {exc}", file=sys.stderr)
        return 1
    if error is not None:
        print(f"logsum: {error}", file=sys.stderr)
        return 1

    records = summarise(rows)
    # Opt-in filter: keep only groups at/above the threshold (spec Q9).
    if args.min_count is not None:
        records = [r for r in records if r["count"] >= args.min_count]

    try:
        write_summary(out_path, records)
    except OSError as exc:
        print(f"logsum: cannot write output: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
