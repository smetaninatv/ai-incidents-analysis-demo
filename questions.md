# Repo Q&A

_Answers derived only from the files cited. Line numbers refer to the
files as read on 2026-07-12._

Files read for this document:
- `spec.md`
- `src/logsum.py`
- `.github/workflows/ci.yml`
- `README.md`
- `CLAUDE.md` (project instructions, provided in context)
- Directory listing via glob for `README*`, `Makefile`, `pyproject.toml`,
  `pytest.ini`, `tox.ini`, `setup.cfg`, `conftest.py`, `requirements*.txt`

---

## Q1. Where is the grouping rule?

**Plain answer.** Events are grouped by a three-part key —
`(service, level, message)` — after each part is normalised. Two rows
land in the same group only if all three normalised values match. The
rule is stated in the spec and implemented in `summarise()`.

**Citations.**
- Spec definition of the key: `spec.md:23-24` ("Exact group key …
  `(service, level, normalised_message)`. Two events collapse into one
  group iff all three match after normalisation").
- Implementation — the key is built here:
  `src/logsum.py:75-79` (tuple of `normalise_service`, `normalise_level`,
  `normalise_message` on the row).
- Grouping happens by inserting into a dict keyed on that tuple:
  `src/logsum.py:73` (the `groups` dict) and `src/logsum.py:81`
  (`groups.setdefault(key, _Group()).add(...)`).
- Normalisation applied before grouping is defined in `spec.md:26-31`
  and implemented in `src/logsum.py:17-30` (`normalise_message`,
  `normalise_level`, `normalise_service`).
- Result ordering (count desc, then service, level, message asc):
  `src/logsum.py:94-95`, matching `spec.md:19`.

---

## Q2. How is missing level handled?

**Plain answer.** A missing or blank `level` is not dropped. It is
replaced with the sentinel string `UNKNOWN`, and the row is grouped and
counted under that value like any other level.

**Citations.**
- Spec rule: `spec.md:36-37` ("A missing/blank `level` is grouped under
  the sentinel `UNKNOWN`. The row is retained and counted; never
  dropped").
- Implementation: `src/logsum.py:22-25` — `normalise_level` computes
  `cleaned = (level or "").strip().upper()` and `return cleaned or
  "UNKNOWN"`, so an empty/whitespace-only/missing level becomes
  `"UNKNOWN"` (the `level or ""` guard also covers a `None` value).
- The row is still counted because the normalised level is part of the
  group key (`src/logsum.py:77`) and every grouped row increments the
  count (`src/logsum.py:61`, `self.count += 1`).

---

## Q3. How do I run tests and CI locally?

**Plain answer.** CI runs two commands on Python 3.11: `ruff check .`
(lint) and `pytest -v` (tests). To reproduce it locally, use Python 3.11,
install the two tools, then run the same two commands from the repo root:

```
python -m pip install --upgrade pip ruff pytest
ruff check .
pytest -v
```

The test file makes the `src` package importable on its own (it puts the
repo root on `PYTHONPATH` for the subprocesses it launches), so running
`pytest` from the repo root is sufficient — no install/packaging step is
needed.

**Citations.**
- The CI workflow and its exact steps: `.github/workflows/ci.yml`.
  - Triggers on push and pull request: `.github/workflows/ci.yml:3-5`.
  - Python version 3.11: `.github/workflows/ci.yml:12-15`.
  - Tooling install: `.github/workflows/ci.yml:17`
    (`python -m pip install --upgrade pip ruff pytest`).
  - Lint command: `.github/workflows/ci.yml:19` (`ruff check .`).
  - Test command: `.github/workflows/ci.yml:21` (`pytest -v`).
- Preferred tools (ruff, pytest) are also stated in project instructions:
  `CLAUDE.md:11-14`.
- The tests are runnable without packaging because the suite sets its own
  import path: `tests/test_logsum.py:25` computes `PROJECT_ROOT`, and the
  `run_cli` helper (`tests/test_logsum.py:34`) passes it as `PYTHONPATH`
  when invoking the CLI as a subprocess (`tests/test_logsum.py:40`).

---

## Things I could not verify

- **No pinned dependencies.** There is no `requirements.txt`,
  `pyproject.toml`, `setup.cfg`, `pytest.ini`, `tox.ini`, `Makefile`, or
  `conftest.py` in the repo (glob search returned only `README.md` and a
  cache file, `.pytest_cache/README.md`). So the *exact* ruff/pytest
  versions used locally are not declared anywhere in the repo — CI simply
  installs the latest (`.github/workflows/ci.yml:17`).
- **No documented run instructions.** `README.md:1-2` contains only a
  one-line project description and says nothing about tests or CI; the
  local-run steps above are reconstructed from `.github/workflows/ci.yml`,
  not from written docs.
- **Python-version parity not checked from files.** CI targets Python
  3.11 (`.github/workflows/ci.yml:12-15`). Whether the suite passes on
  3.11 specifically cannot be confirmed from the repo contents alone; I
  can only cite the CI configuration, not a CI run result.
