# CI notes

## Workflow
`.github/workflows/ci.yml` — GitHub Actions, Python 3.11, triggers on
`push` and `pull_request`. Steps: install `ruff`+`pytest`, run
`ruff check .`, then `pytest -v`. 21 lines; no secrets, no Docker.

## Run result
- **Run:** https://github.com/smetaninatv/ai-incidents-analysis-demo/actions/runs/29196963300
- **Branch:** `ci/add-github-actions`
- **Commit:** `67e82ed`
- **Conclusion:** ✅ success (job `test`), 14:48:32Z → 14:48:40Z

Per-step outcomes:

| # | Step                 | Result  | Duration |
|---|----------------------|---------|----------|
| 1 | Set up job           | success | ~0s |
| 2 | actions/checkout@v4  | success | ~1s |
| 3 | Set up Python 3.11   | success | ~0s |
| 4 | Install tooling      | success | ~3s |
| 5 | Lint (`ruff check .`)| success | ~0s |
| 6 | Test (`pytest -v`)   | success | ~1s |

## Was it green because tests actually ran? (step 3 check)
Yes — green reflects a real test run, not a no-op:

1. **Exit-code proof.** `pytest` returns exit code **5** when it collects
   **zero** tests, which fails the step. The Test step is green, so
   `pytest` exited 0 → at least one test was collected and all passed.
2. **The Test step exists and executed** as its own step (step 6, ~1s),
   distinct from Lint — it wasn't skipped or short-circuited.
3. **Local parity.** The identical commands (`ruff check .`, `pytest -v`)
   collect and pass **19 tests** locally on the same commit.
4. Raw job logs (which would print the literal `19 passed` line) require
   authentication and returned HTTP 403 anonymously, so that line could
   not be captured here; the exit-code contract above is the proof.

The single CI annotation is an unrelated infrastructure **warning**
("Node.js 20 is deprecated … forced to run on Node.js 24" for
`actions/checkout@v4` / `actions/setup-python@v5`) — it does not affect
the build and needs no code/test/workflow fix.

## Pre-flight fix before pushing
Running the exact CI commands locally first caught one real problem:
`ruff check .` failed with `F401 'pytest' imported but unused` in
`tests/test_logsum.py` (the suite uses the auto-injected `tmp_path`
fixture and never referenced `pytest`). Removed the unused import, so the
Lint step was green on the first CI run. Classification: **test bug**
(a lint defect in the test file), not a code or workflow bug.

## PR
Branch pushed to `origin`. `gh` CLI is not installed and no API token was
available in this environment, so the PR was not created programmatically.
Open it with one click here:

https://github.com/smetaninatv/ai-incidents-analysis-demo/pull/new/ci/add-github-actions
