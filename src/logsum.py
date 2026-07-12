"""Summarise events.csv logs into a grouped summary.csv.

See spec.md. Python standard library only.
"""
from __future__ import annotations

import argparse
import csv
import sys
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


def summarise(rows):
    """Group rows by (service, level, normalised message) and sort deterministically."""
    groups = {}
    for row in rows:
        service = normalise_service(row.get("service"))
        level = normalise_level(row.get("level"))
        message = normalise_message(row.get("message"))
        key = (service, level, message)

        raw_ts = (row.get("timestamp") or "").strip()
        dt = parse_timestamp(raw_ts)

        group = groups.get(key)
        if group is None:
            group = {
                "count": 0,
                "first_dt": None, "first_str": "",
                "last_dt": None, "last_str": "",
            }
            groups[key] = group
        group["count"] += 1

        # Malformed timestamps are counted but excluded from first/last_seen (spec Q5).
        if dt is not None:
            if group["first_dt"] is None or dt < group["first_dt"]:
                group["first_dt"], group["first_str"] = dt, raw_ts
            if group["last_dt"] is None or dt > group["last_dt"]:
                group["last_dt"], group["last_str"] = dt, raw_ts

    records = [
        {
            "service": service,
            "level": level,
            "message": message,
            "count": g["count"],
            "first_seen": g["first_str"],
            "last_seen": g["last_str"],
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

    try:
        write_summary(out_path, records)
    except OSError as exc:
        print(f"logsum: cannot write output: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
