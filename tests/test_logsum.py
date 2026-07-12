"""Tests for the events summariser CLI, derived solely from spec.md.

The tool is exercised end-to-end through its documented CLI
(`summarise <input.csv> [--output <path>]`, run here as
`python -m src.logsum ...`) so that every assertion tracks a rule
in the spec rather than the implementation.

Spec references (spec.md):
- Section 3        output columns, group-representative message, sorting
- Q1               group key = (service, level, normalised_message)
- Q2               normalisation rules
- Q4               missing/blank level -> UNKNOWN sentinel
- Q5               malformed timestamp handling
- Q6               empty input -> header-only output, exit 0
- Q7               CLI flags and exit codes (0 / 2 / 1)
- Impl. notes      UTC-instant comparison, verbatim timestamp echo
"""

import csv
import io
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"

EXPECTED_HEADER = ["service", "level", "message", "count", "first_seen", "last_seen"]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def run_cli(*args, cwd=None):
    """Invoke the CLI as `python -m src.logsum <args>`.

    Returns the completed process. ``src`` is importable because
    PROJECT_ROOT is placed on PYTHONPATH, independent of ``cwd``.
    """
    env = {**_base_env(), "PYTHONPATH": str(PROJECT_ROOT)}
    return subprocess.run(
        [sys.executable, "-m", "src.logsum", *args],
        cwd=str(cwd or PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )


def _base_env():
    import os

    return dict(os.environ)


def write_csv(path, text):
    path.write_text(text, encoding="utf-8")
    return path


def read_summary(path):
    """Return (header, list-of-data-rows) from an output CSV."""
    with open(path, encoding="utf-8", newline="") as fh:
        rows = list(csv.reader(fh))
    assert rows, "output file is empty (no header row written)"
    return rows[0], rows[1:]


def as_dicts(path):
    text = Path(path).read_text(encoding="utf-8")
    return list(csv.DictReader(io.StringIO(text)))


# --------------------------------------------------------------------------- #
# Grouping (Q1) + output shape (Section 3)
# --------------------------------------------------------------------------- #
def test_output_header_and_group_collapse(tmp_path):
    out = tmp_path / "summary.csv"
    result = run_cli(str(FIXTURES / "basic_events.csv"), "-o", str(out))
    assert result.returncode == 0, result.stderr

    header, data = read_summary(out)
    assert header == EXPECTED_HEADER

    # 5 input rows collapse into 2 groups: auth/INFO (3) + billing/ERROR (2).
    assert len(data) == 2
    counts = {(r[0], r[1]): int(r[3]) for r in data}
    assert counts[("auth", "INFO")] == 3
    assert counts[("billing", "ERROR")] == 2


def test_distinct_keys_are_not_merged(tmp_path):
    # Same message + level but different service must stay separate (Q1).
    inp = write_csv(
        tmp_path / "in.csv",
        "timestamp,level,service,message\n"
        "2026-07-12T00:00:00Z,INFO,alpha,hello\n"
        "2026-07-12T00:00:00Z,INFO,beta,hello\n",
    )
    out = tmp_path / "summary.csv"
    assert run_cli(str(inp), "-o", str(out)).returncode == 0
    rows = as_dicts(out)
    assert {r["service"] for r in rows} == {"alpha", "beta"}
    assert all(r["count"] == "1" for r in rows)


# --------------------------------------------------------------------------- #
# Normalisation (Q2)
# --------------------------------------------------------------------------- #
def test_service_stripped_but_case_sensitive(tmp_path):
    inp = write_csv(
        tmp_path / "in.csv",
        "timestamp,level,service,message\n"
        "2026-07-12T00:00:00Z,INFO,  auth  ,x\n"   # -> "auth"
        "2026-07-12T00:00:01Z,INFO,auth,x\n"       # -> "auth"  (merges)
        "2026-07-12T00:00:02Z,INFO,Auth,x\n",      # -> "Auth"  (distinct)
    )
    out = tmp_path / "summary.csv"
    assert run_cli(str(inp), "-o", str(out)).returncode == 0
    rows = as_dicts(out)
    by_service = {r["service"]: int(r["count"]) for r in rows}
    assert by_service == {"auth": 2, "Auth": 1}


def test_level_stripped_and_uppercased(tmp_path):
    inp = write_csv(
        tmp_path / "in.csv",
        "timestamp,level,service,message\n"
        "2026-07-12T00:00:00Z, error ,svc,boom\n"
        "2026-07-12T00:00:01Z,ERROR,svc,boom\n"
        "2026-07-12T00:00:02Z,Error,svc,boom\n",
    )
    out = tmp_path / "summary.csv"
    assert run_cli(str(inp), "-o", str(out)).returncode == 0
    rows = as_dicts(out)
    assert len(rows) == 1
    assert rows[0]["level"] == "ERROR"
    assert rows[0]["count"] == "3"


def test_message_whitespace_collapsed_and_stripped(tmp_path):
    inp = write_csv(
        tmp_path / "in.csv",
        "timestamp,level,service,message\n"
        "2026-07-12T00:00:00Z,INFO,svc,  connection   timeout \n"
        "2026-07-12T00:00:01Z,INFO,svc,connection timeout\n"
        "2026-07-12T00:00:02Z,INFO,svc,connection\ttimeout\n",
    )
    out = tmp_path / "summary.csv"
    assert run_cli(str(inp), "-o", str(out)).returncode == 0
    rows = as_dicts(out)
    assert len(rows) == 1
    # Group representative is the normalised message.
    assert rows[0]["message"] == "connection timeout"
    assert rows[0]["count"] == "3"


# --------------------------------------------------------------------------- #
# Missing / blank level (Q4)
# --------------------------------------------------------------------------- #
def test_blank_level_grouped_under_unknown_sentinel(tmp_path):
    inp = write_csv(
        tmp_path / "in.csv",
        "timestamp,level,service,message\n"
        "2026-07-12T00:00:00Z,,billing,payment retry\n"
        "2026-07-12T00:00:01Z,   ,billing,payment retry\n",
    )
    out = tmp_path / "summary.csv"
    assert run_cli(str(inp), "-o", str(out)).returncode == 0
    rows = as_dicts(out)
    # Both blank/whitespace-only levels collapse under the UNKNOWN sentinel;
    # rows are retained and counted, never dropped.
    assert len(rows) == 1
    assert rows[0]["level"] == "UNKNOWN"
    assert rows[0]["count"] == "2"


def test_missing_level_does_not_drop_rows(tmp_path):
    inp = write_csv(
        tmp_path / "in.csv",
        "timestamp,level,service,message\n"
        "2026-07-12T00:00:00Z,INFO,svc,a\n"
        "2026-07-12T00:00:01Z,,svc,b\n",
    )
    out = tmp_path / "summary.csv"
    assert run_cli(str(inp), "-o", str(out)).returncode == 0
    rows = as_dicts(out)
    total = sum(int(r["count"]) for r in rows)
    assert total == 2  # no row silently dropped
    assert "UNKNOWN" in {r["level"] for r in rows}


# --------------------------------------------------------------------------- #
# Malformed timestamp (Q5)
# --------------------------------------------------------------------------- #
def test_malformed_timestamp_counted_but_excluded_from_seen(tmp_path):
    inp = write_csv(
        tmp_path / "in.csv",
        "timestamp,level,service,message\n"
        "2026-07-12T09:00:00Z,ERROR,worker,job failed\n"
        "not-a-timestamp,ERROR,worker,job failed\n"
        "2026-07-12T11:00:00Z,ERROR,worker,job failed\n",
    )
    out = tmp_path / "summary.csv"
    assert run_cli(str(inp), "-o", str(out)).returncode == 0
    rows = as_dicts(out)
    assert len(rows) == 1
    r = rows[0]
    assert r["count"] == "3"  # malformed row still counted
    # first/last computed from the two valid timestamps only.
    assert r["first_seen"] == "2026-07-12T09:00:00Z"
    assert r["last_seen"] == "2026-07-12T11:00:00Z"


def test_all_timestamps_malformed_yields_empty_seen(tmp_path):
    inp = write_csv(
        tmp_path / "in.csv",
        "timestamp,level,service,message\n"
        "nope,ERROR,worker,job failed\n"
        "also-bad,ERROR,worker,job failed\n",
    )
    out = tmp_path / "summary.csv"
    assert run_cli(str(inp), "-o", str(out)).returncode == 0
    rows = as_dicts(out)
    assert len(rows) == 1
    assert rows[0]["count"] == "2"
    assert rows[0]["first_seen"] == ""
    assert rows[0]["last_seen"] == ""


# --------------------------------------------------------------------------- #
# Timestamp comparison in UTC, echoed verbatim (implementation notes)
# --------------------------------------------------------------------------- #
def test_first_last_compared_in_utc_but_echoed_verbatim(tmp_path):
    out = tmp_path / "summary.csv"
    assert run_cli(str(FIXTURES / "basic_events.csv"), "-o", str(out)).returncode == 0
    rows = {(r["service"], r["level"]): r for r in as_dicts(out)}

    auth = rows[("auth", "INFO")]
    assert auth["first_seen"] == "2026-07-12T09:30:00Z"
    assert auth["last_seen"] == "2026-07-12T09:32:00Z"

    # billing group: 10:00+02:00 == 08:00Z (earliest instant) vs 09:00Z.
    # Earliest instant wins for first_seen, but the ORIGINAL string is echoed.
    billing = rows[("billing", "ERROR")]
    assert billing["first_seen"] == "2026-07-12T10:00:00+02:00"
    assert billing["last_seen"] == "2026-07-12T09:00:00Z"


# --------------------------------------------------------------------------- #
# Deterministic sorting (Section 3)
# --------------------------------------------------------------------------- #
def test_sorted_by_count_desc_then_keys_asc(tmp_path):
    inp = write_csv(
        tmp_path / "in.csv",
        "timestamp,level,service,message\n"
        # zeta group: count 1
        "2026-07-12T00:00:00Z,INFO,zeta,m\n"
        # alpha group: count 1
        "2026-07-12T00:00:00Z,INFO,alpha,m\n"
        # mid group: count 2
        "2026-07-12T00:00:00Z,INFO,mid,m\n"
        "2026-07-12T00:00:01Z,INFO,mid,m\n"
        # top group: count 3
        "2026-07-12T00:00:00Z,INFO,top,m\n"
        "2026-07-12T00:00:01Z,INFO,top,m\n"
        "2026-07-12T00:00:02Z,INFO,top,m\n",
    )
    out = tmp_path / "summary.csv"
    assert run_cli(str(inp), "-o", str(out)).returncode == 0
    rows = as_dicts(out)
    order = [(r["service"], int(r["count"])) for r in rows]
    # count desc first; ties broken by service (then level, message) asc.
    assert order == [("top", 3), ("mid", 2), ("alpha", 1), ("zeta", 1)]


# --------------------------------------------------------------------------- #
# Empty input (Q6)
# --------------------------------------------------------------------------- #
def test_header_only_input_writes_header_only_and_exits_zero(tmp_path):
    out = tmp_path / "summary.csv"
    result = run_cli(str(FIXTURES / "empty_events.csv"), "-o", str(out))
    assert result.returncode == 0, result.stderr
    header, data = read_summary(out)
    assert header == EXPECTED_HEADER
    assert data == []


# --------------------------------------------------------------------------- #
# CLI invocation & exit codes (Q7)
# --------------------------------------------------------------------------- #
def test_default_output_is_summary_csv_in_cwd(tmp_path):
    # No -o: output defaults to summary.csv in the current directory.
    result = run_cli(str(FIXTURES / "basic_events.csv"), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    default_out = tmp_path / "summary.csv"
    assert default_out.exists()
    header, _ = read_summary(default_out)
    assert header == EXPECTED_HEADER


def test_long_output_flag(tmp_path):
    out = tmp_path / "custom.csv"
    result = run_cli(str(FIXTURES / "basic_events.csv"), "--output", str(out))
    assert result.returncode == 0, result.stderr
    assert out.exists()


def test_help_exits_zero_and_shows_usage(tmp_path):
    result = run_cli("--help")
    assert result.returncode == 0
    assert "usage" in result.stdout.lower()


def test_missing_required_argument_is_usage_error(tmp_path):
    # No positional input -> argparse usage error, exit code 2 (Q7).
    result = run_cli()
    assert result.returncode == 2


def test_unknown_flag_is_usage_error(tmp_path):
    result = run_cli(str(FIXTURES / "basic_events.csv"), "--nonsense")
    assert result.returncode == 2


# --------------------------------------------------------------------------- #
# Bad input -> exit 1 (Q7)
# --------------------------------------------------------------------------- #
def test_nonexistent_input_file_exits_one(tmp_path):
    missing = tmp_path / "does_not_exist.csv"
    out = tmp_path / "summary.csv"
    result = run_cli(str(missing), "-o", str(out))
    assert result.returncode == 1
    assert not out.exists()


def test_missing_required_column_exits_one(tmp_path):
    # Structurally malformed CSV (no 'message' column) -> exit 1 (Q7).
    out = tmp_path / "summary.csv"
    result = run_cli(str(FIXTURES / "missing_message_column.csv"), "-o", str(out))
    assert result.returncode == 1


# --------------------------------------------------------------------------- #
# --min-count N filter (Q9)
# --------------------------------------------------------------------------- #
# basic_events.csv yields two groups: auth/INFO (count 3), billing/ERROR (2).
def test_min_count_excludes_groups_below_threshold(tmp_path):
    out = tmp_path / "summary.csv"
    result = run_cli(str(FIXTURES / "basic_events.csv"), "--min-count", "3",
                     "-o", str(out))
    assert result.returncode == 0, result.stderr
    rows = as_dicts(out)
    assert len(rows) == 1
    assert rows[0]["service"] == "auth"
    assert rows[0]["count"] == "3"


def test_min_count_boundary_is_inclusive(tmp_path):
    # count == N is kept (>=, not >): both groups survive at N=2.
    out = tmp_path / "summary.csv"
    result = run_cli(str(FIXTURES / "basic_events.csv"), "--min-count", "2",
                     "-o", str(out))
    assert result.returncode == 0, result.stderr
    rows = as_dicts(out)
    assert {r["service"] for r in rows} == {"auth", "billing"}


def test_min_count_filtering_everything_yields_header_only(tmp_path):
    out = tmp_path / "summary.csv"
    result = run_cli(str(FIXTURES / "basic_events.csv"), "--min-count", "4",
                     "-o", str(out))
    assert result.returncode == 0, result.stderr
    header, data = read_summary(out)
    assert header == EXPECTED_HEADER
    assert data == []


def test_default_behaviour_unchanged_without_flag(tmp_path):
    # Explicit guard: output with no --min-count must match the pre-feature
    # result (both groups present, unchanged ordering).
    out = tmp_path / "summary.csv"
    result = run_cli(str(FIXTURES / "basic_events.csv"), "-o", str(out))
    assert result.returncode == 0, result.stderr
    rows = as_dicts(out)
    assert [(r["service"], r["count"]) for r in rows] == [
        ("auth", "3"),
        ("billing", "2"),
    ]


def test_non_integer_min_count_is_usage_error(tmp_path):
    out = tmp_path / "summary.csv"
    result = run_cli(str(FIXTURES / "basic_events.csv"), "--min-count",
                     "notanumber", "-o", str(out))
    assert result.returncode == 2
