# Current Task

## Task ID
TASK-011-FIX2

## Title
Synchronize T11 account documentation after redirect/logout fix

## Goal
Bring the agent documentation into agreement with the completed T11 customer
accounts implementation and T11-FIX redirect/logout hardening, without changing
application code.

## Scope
Documentation-only correction. The account implementation already passes the
reviewed behavior checks:
- external login `next` URLs are blocked;
- safe relative `next` URLs are honored;
- authenticated navbar includes a POST logout form;
- account pages use normal storefront base context;
- 211 tests pass.

## Files Expected to Change
- `docs/agent/HANDOFF.md`
- `docs/agent/TEST_STATUS.md`
- `docs/agent/TASK_BOARD.md`
- `docs/agent/CURRENT_TASK.md`
- `.agent/CONTINUITY.md`

## Required Behavior
1. Update `docs/agent/HANDOFF.md` so it no longer says only T0-T10 are
   complete.
2. Add T11/T11-FIX to the completed-task summary in `HANDOFF.md`.
3. Update `HANDOFF.md` verification status from 193 tests to 211 tests.
4. Remove `Customer accounts and authentication` from `HANDOFF.md` optional
   future work because T11 implemented it.
5. Update `docs/agent/TEST_STATUS.md` current state from T0-T10 / 193 tests to
   T0-T11 / 211 tests.
6. Add a T11/T11-FIX verification section to `TEST_STATUS.md` listing the
   account, storefront, full test, check, and migration dry-run commands.
7. Ensure `docs/agent/TASK_BOARD.md` marks T11 done and does not list an
   outstanding T11 fix task.
8. Update `.agent/CONTINUITY.md` with a concise outcome entry for this
   documentation sync.

## Non-Goals
- Do not modify `store/`, `templates/`, `femdes_site/`, migrations, settings,
  requirements, static assets, or tests.
- Do not add the next feature task yet.
- Do not change account behavior.
- Do not add category/tag management in this task.

## Acceptance Criteria
- `rg -n "T0 through T10|193 tests|Customer accounts and authentication" docs/agent/HANDOFF.md docs/agent/TEST_STATUS.md` returns no stale matches.
- `docs/agent/HANDOFF.md` lists T11 customer accounts as complete.
- `docs/agent/TEST_STATUS.md` reports 211 tests and includes T11/T11-FIX
  verification.
- `docs/agent/TASK_BOARD.md` marks T11 done.
- Only documentation/continuity files are modified.

## Validation Commands
```bash
rg -n "T0 through T10|193 tests|Customer accounts and authentication" docs/agent/HANDOFF.md docs/agent/TEST_STATUS.md
conda run -n femdes python manage.py test store.tests.test_accounts store.tests.test_storefront -v 2
conda run -n femdes python manage.py test -v 1
conda run -n femdes python manage.py check
conda run -n femdes python manage.py makemigrations --check --dry-run
```
