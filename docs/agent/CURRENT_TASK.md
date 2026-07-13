# Current Task

## Task ID
TASK-025-FIX2 — Prove status-filter ownership with same-status foreign order

## Context

Commit `b881701` strengthened most TASK-025-FIX gaps:

- Search by another user's order number now returns the no-match empty state.
- Invalid status now asserts the other user's order detail link is absent.
- The no-orders empty state is tested.
- HANDOFF and TEST_STATUS now report T0 through T25 complete with 325 tests.

One test-proof gap remains. `OrderSearchFilterTests.test_status_filter_shows_only_matching` filters `?status=shipped`, but the only other user's order in the fixture is `pending`. That means the test would still pass if `account_orders` accidentally filtered all users' shipped orders, because there is no same-status foreign order to leak.

Do not rewrite the feature. The view is already scoped correctly. This task is a narrow test-strength and docs-closeout fix.

## Required Fixes

1. Strengthen status-filter ownership proof.
   - Add a second foreign order in `OrderSearchFilterTests.setUp`, for example:
     ```python
     self.other_shipped_order = Order.objects.create(
         customer_name="D",
         customer_email="d@t.com",
         shipping_address="D",
         customer_user=self.other,
         status="shipped",
     )
     ```
   - In `test_status_filter_shows_only_matching`, assert the current user's shipped order renders and the foreign shipped order does not render.
   - For this status-filter test, assert the foreign shipped `order_number` itself is absent, not only customer email.
   - Also assert the foreign shipped order detail URL is absent.

2. Preserve the other T25-FIX coverage.
   - Keep the search-by-foreign-order test.
   - Keep the invalid-status scoping test.
   - Keep both empty-state tests.
   - Keep existing account order view behavior unchanged unless the strengthened test reveals a real bug.

3. Close docs after verification.
   - Keep `docs/agent/HANDOFF.md` and `docs/agent/TEST_STATUS.md` on the actual full test count.
   - If this fix is approved, write the next implementation-ready task into `docs/agent/CURRENT_TASK.md`.

## Acceptance Criteria

- Status-filter tests fail if `account_orders` starts from all orders instead of `request.user` orders and another user has the same filtered status.
- Search-by-order-number tests fail if another user's order becomes visible.
- Invalid-status tests fail if another user's order becomes visible.
- Both empty states remain covered.
- Existing account order filtering/search behavior remains intact.
- Existing order detail/tracking access control remains intact.
- No broad feature rewrite, new model, or new route is added unless required by a discovered bug.
- Focused tests, full tests, `check`, migration dry-run, `pip check`, stale-doc search, and diff whitespace checks pass.

## DeepSeek Self-Validation Loop

Before claiming completion, DeepSeek must run this loop and include the results in handoff notes:

1. Fail-first audit:
   - Temporarily change `account_orders` to start from `Order.objects.all()` and confirm `test_status_filter_shows_only_matching` fails because the foreign same-status order leaks.
   - Confirm search-by-foreign-order and invalid-status ownership tests still fail if user scoping is removed.
   - Confirm stale docs search returns no current-state matches:
     ```bash
     rg -n "319 tests|324 tests|T0 through T24|T24-FIX3|Next: T25|T25 .*active|318 tests|T22 is the next|T23-FIX3 .*active|T23-FIX4 .*active|T24-FIX .*active|T24-FIX2 .*complete" docs/agent/HANDOFF.md docs/agent/TEST_STATUS.md
     ```

2. Focused verification:
   ```bash
   conda run -n femdes python manage.py test store.tests.test_accounts store.tests.test_invoices store.tests.test_staff_views -v 2
   ```

3. Full verification:
   ```bash
   conda run -n femdes python manage.py test -v 1
   conda run -n femdes python manage.py check
   conda run -n femdes python manage.py makemigrations --check --dry-run
   conda run -n femdes python -m pip check
   git diff --check HEAD~1..HEAD
   git diff --check
   ```

4. Diff scope audit:
   ```bash
   git diff --name-status HEAD~1..HEAD
   git diff --name-status
   ```
   Confirm changes are limited to account-order tests and required docs unless a real ownership bug is discovered.
