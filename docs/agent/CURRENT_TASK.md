# Current Task

## Task ID
TASK-017-FIX3

## Title
Synchronize final T17 test-count documentation

## Objective
T17-FIX2 successfully strengthened the primary-image storefront tests and the full suite now runs 266 tests. The remaining blocker is documentation drift: `docs/agent/TEST_STATUS.md` still reports 264 tests in the current-state block and command snippet.

Do not change application code or tests unless a verification command fails for an unrelated reason. This is a docs-only corrective task.

## Required Fixes

1. Update `docs/agent/TEST_STATUS.md` current-state prose so it says `266 tests pass`.
2. Update the current `manage.py test` command comment in `docs/agent/TEST_STATUS.md` so it says `PASS (266 tests)`.
3. Confirm `docs/agent/HANDOFF.md` and `docs/agent/CURRENT_TASK.md` do not contradict the 266-test result.
4. Update `.agent/CONTINUITY.md` with a short outcome entry after verification.

## Acceptance Criteria

- `docs/agent/TEST_STATUS.md` current state and command snippet both report 266 tests.
- No stale current-state `264 tests` claim remains in `docs/agent/HANDOFF.md` or `docs/agent/TEST_STATUS.md`.
- No application source, templates, migrations, or tests are changed.
- Full test suite still passes.

## Required Verification

Run all commands from the repository root:

```bash
conda run -n femdes python manage.py test -v 1
conda run -n femdes python manage.py check
conda run -n femdes python manage.py makemigrations --check --dry-run
rg -n "264 tests|260 tests|T0 through T16" docs/agent/HANDOFF.md docs/agent/TEST_STATUS.md
git diff --check HEAD^..HEAD
```

The `rg` command must return no matches.
