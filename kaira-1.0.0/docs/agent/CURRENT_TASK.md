# Current Task

## Task ID
TASK-011-FIX4

## Title
Fix the remaining stale test-count line in TEST_STATUS

## Goal
Make the required stale-documentation search pass by editing the one remaining
stale line in `docs/agent/TEST_STATUS.md`.

## Scope
Documentation only. This is not a code task.

## Files Expected to Change
- `docs/agent/TEST_STATUS.md`
- `docs/agent/CURRENT_TASK.md`
- `.agent/CONTINUITY.md`

## Required Behavior
1. Edit `docs/agent/TEST_STATUS.md` line in the T10/T10-FIX verification block
   that currently says:

```bash
conda run -n femdes python manage.py test                                  # 193 tests, OK
```

2. Reword that historical T10 line so it preserves the meaning without
   containing the exact text `193 tests`.
3. Do not remove the current-state `211 tests` text.
4. Do not edit application code, tests, migrations, templates, README,
   settings, static assets, or requirements.
5. Do not write the next feature task in this fix.

## Non-Goals
- Do not change account behavior.
- Do not change category/tag behavior.
- Do not add product images or measurement specs.
- Do not run migrations or alter the database.

## Acceptance Criteria
- This command exits with no matches:

```bash
rg -n "T0 through T10|193 tests|Customer accounts and authentication" docs/agent/HANDOFF.md docs/agent/TEST_STATUS.md
```

- `docs/agent/TEST_STATUS.md` still reports `211 tests` in the current state.
- Only `docs/agent/TEST_STATUS.md`, `docs/agent/CURRENT_TASK.md`, and
  `.agent/CONTINUITY.md` are modified.

## Validation Commands
```bash
rg -n "T0 through T10|193 tests|Customer accounts and authentication" docs/agent/HANDOFF.md docs/agent/TEST_STATUS.md
conda run -n femdes python manage.py test -v 1
conda run -n femdes python manage.py check
conda run -n femdes python manage.py makemigrations --check --dry-run
```
