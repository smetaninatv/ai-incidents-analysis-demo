# CLAUDE.md

## Project context
Tiny CLI that summarises synthetic `events.csv` logs.

## Conventions
- Code lives in `src/`
- Tests live in `tests/`
- Data lives in `data/`

## Utilities to prefer
- Python standard library (avoid third-party deps)
- `ruff` for linting/formatting
- `pytest` for tests

## Escalation gates
Stop and ask before:
- Adding any dependency beyond the standard library.
- Using non-synthetic data — synthetic data only.
- Overwriting `spec.md` after sign-off.
