# ai-incidents-analysis-demo

A tiny command-line tool that reads a CSV of log events and writes a
grouped summary CSV — one row per event group. Python standard library
only; no third-party runtime dependencies.

See [`spec.md`](spec.md) for the full behavioural specification.

## Requirements

- Python 3.11+ (CI runs on 3.11).
- Runtime: standard library only.
- Dev/test: [`ruff`](https://docs.astral.sh/ruff/) (lint) and
  [`pytest`](https://pytest.org) (tests).

## Usage

```
python -m src.logsum <input.csv> [output.csv] [-o OUTPUT] [--min-count N]
```

- `input` (required) — path to the events CSV.
- `output` (optional positional) or `-o` / `--output` — output path
  (default: `summary.csv` in the current directory). The `-o` flag wins
  if both are given.
- `--min-count N` — only write groups whose `count >= N` (default: unset,
  i.e. all groups).
- `-h` / `--help` — usage.

Example:

```
python -m src.logsum data/sample_events.csv -o summary.csv
python -m src.logsum data/sample_events.csv --min-count 2
```

### Input

UTF-8 CSV with a header and these columns (all required):

| column      | meaning                                   |
|-------------|-------------------------------------------|
| `timestamp` | ISO-8601 string (e.g. `2026-07-12T09:31:00Z`) |
| `level`     | severity (e.g. `INFO`, `WARN`, `ERROR`)   |
| `service`   | emitting service name                     |
| `message`   | free-text event message                   |

### Output

UTF-8 CSV with a header and one row per group:
`service, level, message, count, first_seen, last_seen`.

Rows are sorted by `count` descending, then `service`, `level`, `message`
ascending (deterministic).

## Behaviour highlights

- **Grouping.** Events are grouped by `(service, level, message)` after
  normalisation (service trimmed, case-sensitive; level trimmed and
  upper-cased; message trimmed with internal whitespace collapsed).
- **Missing level.** A blank/missing `level` is grouped under the
  sentinel `UNKNOWN` — the row is retained and counted, never dropped.
- **Malformed timestamps.** A row with an unparseable `timestamp` is
  still counted, but excluded from `first_seen`/`last_seen`. If every row
  in a group is unparseable, those fields are written empty.
- **first_seen / last_seen.** Chosen by comparing timestamps as UTC
  instants, but the original timestamp string is echoed verbatim.
- **Empty input.** A header-only (or zero-row) input produces a
  header-only `summary.csv` and exits `0`.

### Exit codes

| code | meaning |
|------|---------|
| `0`  | success (including empty input) |
| `1`  | I/O error, or malformed CSV structure (e.g. missing required columns) |
| `2`  | usage error (missing/unknown args, or a non-integer `--min-count`) |

## Development

Layout: code in `src/`, tests in `tests/`, sample data in `data/`.

Run the lint and test suite locally (the same commands CI runs):

```
python -m pip install --upgrade pip ruff pytest
ruff check .
pytest -v
```

Tests invoke the CLI end-to-end and set their own import path, so
`pytest` works from the repo root without any install/packaging step.

## Continuous integration

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs `ruff check .`
and `pytest -v` on Python 3.11 for every push and pull request.
