# spec.md — events summariser CLI

## 1. Purpose
A tiny command-line tool that reads a CSV of log events and writes a grouped summary CSV, one row per event group. Python standard library only.

## 2. Input
`events.csv`, UTF-8, with header. Columns:
- `timestamp` — ISO-8601 string (e.g. `2026-07-12T09:31:00Z`)
- `level` — severity (e.g. `INFO`, `WARN`, `ERROR`)
- `service` — emitting service name
- `message` — free-text event message

## 3. Output
`summary.csv`, UTF-8, with header. One row per group. Columns:
`service, level, message, count, first_seen, last_seen`
- `message` = the normalised message (the group representative)
- `count` = number of events in the group
- `first_seen` / `last_seen` = min / max valid timestamp in the group
- Rows sorted by `count` descending, then `service, level, message` ascending (deterministic output).

## 4. Spec questions & answers

**Q1 — Exact group key.**
`(service, level, normalised_message)`. Two events collapse into one group iff all three match after normalisation.

**Q2 — Normalisation rules.**
Applied before grouping:
- `service`: strip surrounding whitespace; compare case-sensitively (kept as-is).
- `level`: strip whitespace; upper-case.
- `message`: strip whitespace; collapse internal runs of whitespace to a single space. (No number/UUID templating in v1 — see out of scope.)
- `timestamp`: strip whitespace; parse as ISO-8601.

**Q3 — Count only, or first_seen / last_seen too.**
Include all three: `count`, `first_seen`, `last_seen`.

**Q4 — Missing level behaviour.**
A missing/blank `level` is grouped under the sentinel `UNKNOWN`. The row is retained and counted; never dropped.

**Q5 — Malformed timestamp behaviour.**
A row whose `timestamp` cannot be parsed is still counted in its group, but is excluded from `first_seen`/`last_seen` computation. If every row in a group has an unparseable timestamp, `first_seen`/`last_seen` are written empty.

**Q6 — Empty input behaviour.**
Input with only a header (or zero data rows) produces a `summary.csv` containing just the header row, and the tool exits `0`.

**Q7 — CLI flags and exit codes.**
Invocation: `summarise <input.csv> [--output <path>]`
- positional `input` — path to `events.csv` (required)
- `--output` / `-o` — output path (default: `summary.csv` in the current directory)
- `--help` / `-h` — usage
Exit codes:
- `0` — success (including empty input)
- `2` — usage error (missing/unknown args) — argparse default
- `1` — I/O error (input not found/unreadable, output not writable) or malformed CSV structure (e.g. missing required columns)

**Q8 — Explicit out-of-scope items (v1).**
- Message templating / clustering of numbers, IDs, UUIDs, timestamps inside messages.
- Timezone normalisation beyond ISO-8601 parsing; no cross-timezone reconciliation.
- Streaming / very-large-file optimisation (loads input into memory).
- Multiple input files, globbing, or directory input.
- Output formats other than CSV (no JSON, no console tables).
- Filtering by level/service/time range.
- Config files or environment-variable configuration.

## 5. Non-functional constraints
- Python standard library only (`csv`, `argparse`, `datetime`). No third-party deps.
- `ruff` clean; covered by `pytest` tests under `tests/`.
- Synthetic data only for any fixtures.

## Signed off
Tatiana Smetanina — 2026-07-12

## Implementation notes
- **Decision — timestamps compared in UTC, but echoed verbatim.** `first_seen`/`last_seen` are chosen by parsing each timestamp to a timezone-aware UTC `datetime` for correct min/max comparison across offsets, yet the *original* input string is written back to the output (e.g. `2026-07-12T09:31:00Z` stays as `Z`, not rewritten to `+00:00`). This keeps output faithful to the source while comparisons stay correct. Naive timestamps are assumed UTC.
- **Extension beyond Q7 — output may also be a second positional argument** (`logsum <input> <output>`), in addition to the spec's `--output/-o` flag, to support `python -m src.logsum data/sample_events.csv data/summary.csv`. The `-o` flag wins if both are supplied.
