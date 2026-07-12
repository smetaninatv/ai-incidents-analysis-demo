# Provenance note — `--min-count N` feature

_Prepared before any push, per the agreed process. Nothing is committed or
pushed yet._

## Model
- **claude-opus-4-8** (Claude Code / Opus 4.8), single agent, no subagents
  spawned for this task.

## Context loaded
- `CLAUDE.md` (project conventions + escalation gates).
- `spec.md` (full), especially Q7 (CLI/exit codes) and Q6 (empty-output
  shape) — the rules the feature extends.
- `src/logsum.py` (full), read this session before editing.
- Approved plan: `~/.claude/plans/plan-this-task-do-dreamy-storm.md`
  (also echoed back in the approval message).
- Prior in-session work on this branch: the spec-derived pytest suite and
  the `summarise()`/`_Group` refactor (see "Working-tree caveat" below).
- Tooling: `ruff` 0.15.21, `pytest` 9.1.1, Python 3.14.3 (local);
  CI targets Python 3.11.

## Files changed (this task)
| File | Nature of change |
|------|------------------|
| `src/logsum.py` | `build_parser()`: added `--min-count N` (`type=int`, `default=None`). `main()`: filter `records` to `count >= N` only when the flag is set. `summarise()` untouched. |
| `spec.md` | Q7: added the flag + noted non-integer → exit 2. New **Q9** rule. **v1.1 addendum**; original sign-off left intact (amended, not overwritten). |
| `tests/test_logsum.py` | +5 CLI tests: below-threshold excluded, `>=` boundary inclusive, filter-all → header-only exit 0, default-unchanged guard, non-integer → exit 2. |
| `provenance-note.md` | This note (new file). |

No other source, fixture, workflow, or config files were touched by this
task. No new dependencies; no new fixtures.

## Plan deviations
- **None.** Implemented exactly as approved: filter in `main()` (not in
  `summarise()`), spec amended rather than overwritten, no `N<1`
  validation, no short alias/env/config. All items the plan marked
  out-of-scope were left out.

## Untested items / residual risk
- Verified by automated tests: exclusion below N, inclusive `>=`
  boundary, filter-everything (header-only, exit 0), default-unchanged,
  non-integer usage error. Plus a manual smoke test on
  `data/sample_events.csv` (no-flag = all 5 groups; `--min-count 2` keeps
  only the count-3 group).
- **Not explicitly asserted:** `--min-count 0` / negative values (spec Q9
  says these are an accepted no-op — covered by reasoning, not a test);
  interaction of `--min-count` with a second positional `output` arg
  (orthogonal code paths, not combined in a test); very large N beyond the
  max group count (same code path as the "filter-everything" test).
- Full suite: `ruff check .` clean; `pytest` **24 passed** (19 prior + 5
  new). Verified on local Python 3.14, not yet on the CI Python 3.11
  runner (no behavioural reason to differ; stdlib only).

## Working-tree caveat (important for the diff review)
This feature sits on branch **`ci/add-github-actions`** on top of the
earlier, still-uncommitted **`summarise()` refactor**. Because `HEAD`
predates both, `git diff HEAD -- src/logsum.py` shows the refactor **and**
this feature together (~66 changed lines), not the feature alone. The
refactor is documented separately in `refactor-notes.md`. Also untracked
and unrelated to this task: `context-load-check.md` (a pre-existing
harness artifact I did not create or modify).

Recommendation for the push: separate the refactor and the feature into
distinct commits (and consider a dedicated feature branch), so each diff
matches its own note.
