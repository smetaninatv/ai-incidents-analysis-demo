# Test notes — `tests/test_logsum.py`

Tests were written from `spec.md` only; `src/logsum.py` was not read.
The CLI is exercised end-to-end via `python -m src.logsum` so each
assertion tracks a spec rule rather than an implementation detail.

## Result of `pytest -v`
**19 passed, 0 failed.** Every spec-derived test passed against the
current implementation, so there was no red test to isolate.

Because steps 4–5 call for classifying one case as *implementation bug*,
*test bug*, or *spec ambiguity*, the entry below documents the one point
that genuinely required a decision while writing the suite — a **spec
ambiguity** surfaced by a targeted probe.

## Decision record — spec ambiguity: empty (no-header) input

**The question.** Q6 defines "empty input" as *"only a header (or zero
data rows)"* → header-only output, exit `0`. Q7 says *"malformed CSV
structure (e.g. missing required columns)"* → exit `1`. A file with **no
header at all** (0 bytes) is covered by *both* readings: it has zero data
rows (Q6 → exit 0) but also no required columns (Q7 → exit 1). The spec
does not resolve the overlap.

**Isolation method.** Minimal reproduction with a single-variable input —
a 0-byte fixture — invoked directly, observing exit code and output:

```
printf "" > zero_bytes.csv
PYTHONPATH=. python -m src.logsum zero_bytes.csv -o out.csv
# exit=0
# out.csv -> "service,level,message,count,first_seen,last_seen"
```

The empty file is the smallest input that separates the two rules: it
strips away every other variable (data rows, column names, parse errors)
so the only thing under test is "no header present."

**Observed behaviour.** Exit `0`, header-only `summary.csv`. The
implementation classifies a headerless/empty file as *empty input* (Q6),
not as *missing required columns* (Q7).

**Decision: spec ambiguity — not an implementation or test bug.**
- Not an *implementation* bug: exit 0 is a defensible, user-friendly
  reading of Q6 and matches the header-only-file case that Q6 explicitly
  blesses.
- Not a *test* bug: no assertion in the suite depends on this case, so
  nothing is falsely red or green.
- It is a genuine gap in `spec.md`: the two rules overlap for a
  headerless file and the document picks no winner.

**Consequence for the suite.** I deliberately did **not** add an
assertion pinning exit 0 vs exit 1 for a headerless file, to avoid
over-specifying beyond what `spec.md` mandates. `spec.md` is signed off,
so tightening it is gated (see CLAUDE.md "Escalation gates"). Suggested
resolution for a future `spec.md` revision: state explicitly that an
*empty file with no header* is treated as empty input (exit 0), OR that
absence of the required header is a structural error (exit 1). Until then
this behaviour is documented here rather than asserted.

## Fixtures
- `tests/fixtures/basic_events.csv` — grouping + normalisation +
  cross-offset UTC ordering with verbatim echo.
- `tests/fixtures/empty_events.csv` — header-only input (Q6).
- `tests/fixtures/missing_message_column.csv` — missing required column
  (Q7 → exit 1).

All fixture data is synthetic (CLAUDE.md constraint).
