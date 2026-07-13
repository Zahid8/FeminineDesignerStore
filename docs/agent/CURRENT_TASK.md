# Current Task

## Task ID
TASK-025-FIX3 — Close final status-filter proof and doc-sync gaps

## Context

Commit `ea7364c` correctly removed the unrelated T27 `store.js` work and added a same-status foreign shipped order to `OrderSearchFilterTests`.

One test-proof detail from the prior acceptance criteria is still missing:

- `test_status_filter_shows_only_matching` now asserts the foreign shipped order detail URL is absent.
- It does **not** directly assert `self.other_shipped.order_number` is absent from the response body.

That direct order-number assertion was explicitly required so the test fails even if a future template renders a leaked foreign order number without linking it.

Documentation also remains stale:

- `docs/agent/HANDOFF.md` summary still says `325 tests`.
- `docs/agent/TEST_STATUS.md` current state and command block still say `325 tests`.

This is a narrow test/docs cleanup only. Do not reintroduce T27 JavaScript. Do not expand T26/T27. Do not change account-order view behavior unless the strengthened test reveals a real bug.

## Required Fix

1. Strengthen the status-filter assertion.
   - In `store/tests/test_accounts.py::OrderSearchFilterTests.test_status_filter_shows_only_matching`, add:
     ```python
     self.assertNotContains(response, self.other_shipped.order_number)
     ```
   - Keep the existing assertions for:
     - current user's shipped order present,
     - current user's pending order absent,
     - foreign pending detail URL absent,
     - foreign shipped detail URL absent.

2. Sync current-state docs.
   - Update `docs/agent/HANDOFF.md` so every current-state test count is `330 tests`.
   - Update `docs/agent/TEST_STATUS.md` so every current-state test count is `330 tests`.
   - Remove stale `325 tests` / `329 tests` matches from current-state docs.

3. If this fix is approved, replace this file with the next implementation-ready task.
   - Carry any remaining documentation-only cleanup into that next task per owner policy.

## Acceptance Criteria

- Status-filter test directly proves the foreign shipped order number is absent.
- Status-filter test still proves the foreign shipped order detail URL is absent.
- Search-by-foreign-order, invalid-status scoping, and both empty-state tests remain covered.
- `static/store/js/store.js` remains absent.
- `templates/base.html` does not include `store/js/store.js`.
- No new model, route, template feature, or JavaScript behavior is added.
- Handoff/test-status current-state docs report the actual `330 tests` count.
- Stale-doc search returns no `325 tests` or `329 tests` current-state matches.

## DeepSeek Self-Validation Loop

Before claiming completion, run and record:

1. Fail-first audit:
   - Temporarily change `store/views.py::account_orders` to start from `Order.objects.all()`.
   - Confirm `test_status_filter_shows_only_matching` fails because `self.other_shipped.order_number` leaks.
   - Restore `Order.objects.filter(customer_user=request.user)`.
   - Confirm:
     ```bash
     test ! -f static/store/js/store.js
     ! rg -n "store/js/store.js" templates store/tests
     ! rg -n "325 tests|329 tests" docs/agent/HANDOFF.md docs/agent/TEST_STATUS.md
     ```

2. Focused verification:
   ```bash
   conda run -n femdes python manage.py test store.tests.test_accounts store.tests.test_invoices store.tests.test_staff_views store.tests.test_feedback store.tests.test_storefront -v 2
   ```

3. Full verification:
   ```bash
   conda run -n femdes python manage.py test -v 1
   conda run -n femdes python manage.py check
   conda run -n femdes python manage.py makemigrations --check --dry-run
   conda run -n femdes python -m pip check
   conda run -n femdes python manage.py collectstatic --noinput
   git diff --check HEAD~1..HEAD
   git diff --check
   ```

4. Diff scope audit:
   ```bash
   git diff --name-status HEAD~1..HEAD
   git diff --name-status
   ```
   The new diff should be limited to `store/tests/test_accounts.py`, `docs/agent/HANDOFF.md`, `docs/agent/TEST_STATUS.md`, and required handoff/current-task bookkeeping.
