# Current Task

## Task ID
TASK-025-FIX2 — Finish account-order status-filter ownership proof

## Context

Commit `b881701` fixed most T25 ownership-test gaps, but one acceptance criterion remains unproven:

- `OrderSearchFilterTests.test_status_filter_shows_only_matching` filters `?status=shipped`.
- The fixture has a current-user shipped order and a foreign pending order.
- It does **not** have a foreign shipped order.
- Therefore the test would still pass if `account_orders` accidentally started from `Order.objects.all()` and leaked another user's shipped order.

Commit `8b1c3a6` then added unrelated T26 contact/feedback code instead of finishing this active T25-FIX2 task. Do not expand T26 in this task. Do not revert the T26 files unless the owner explicitly asks. Finish the active T25-FIX2 test proof first.

Current verification after `8b1c3a6` runs 329 tests, while HANDOFF/TEST_STATUS still say 325 tests. Treat that as documentation carryover inside this fix.

## Required Fix

1. Add same-status foreign-order coverage.
   - In `store/tests/test_accounts.py::OrderSearchFilterTests.setUp`, add a second foreign order with `status="shipped"`, for example:
     ```python
     self.other_shipped_order = Order.objects.create(
         customer_name="D",
         customer_email="d@t.com",
         shipping_address="D",
         customer_user=self.other,
         status="shipped",
     )
     ```
   - In `test_status_filter_shows_only_matching`, keep asserting the current user's shipped order renders.
   - Also assert the foreign shipped `order_number` does not render.
   - Also assert the foreign shipped order detail URL does not render.

2. Preserve existing coverage.
   - Keep the search-by-foreign-order test.
   - Keep the invalid-status scoping test.
   - Keep both empty-state tests.
   - Keep existing account order view behavior unchanged unless the strengthened test reveals a real bug.

3. Keep docs consistent.
   - Update `docs/agent/HANDOFF.md` and `docs/agent/TEST_STATUS.md` to the actual full test count after verification.
   - If this fix is approved, write the next implementation-ready task into `docs/agent/CURRENT_TASK.md`.

## Acceptance Criteria

- Status-filter tests fail if `account_orders` starts from all orders instead of `request.user` orders and another user has the same filtered status.
- Search-by-order-number tests fail if another user's order becomes visible.
- Invalid-status tests fail if another user's order becomes visible.
- Both empty states remain covered.
- Existing account order filtering/search behavior remains intact.
- Existing order detail/tracking access control remains intact.
- No broad feature rewrite, new model, or new route is added for this task.
- Focused tests, full tests, `check`, migration dry-run, `pip check`, stale-doc search, and diff whitespace checks pass.

## DeepSeek Self-Validation Loop

Before claiming completion, DeepSeek must run this loop and include the results in handoff notes:

1. Fail-first audit:
   - Temporarily change `account_orders` to start from `Order.objects.all()` and confirm `test_status_filter_shows_only_matching` fails because the foreign same-status order leaks.
   - Confirm search-by-foreign-order and invalid-status ownership tests still fail if user scoping is removed.
   - Confirm stale docs search returns no current-state matches:
     ```bash
     rg -n "319 tests|324 tests|325 tests|T0 through T24|T24-FIX3|Next: T25|T25 .*active|318 tests|T22 is the next|T23-FIX3 .*active|T23-FIX4 .*active|T24-FIX .*active|T24-FIX2 .*complete" docs/agent/HANDOFF.md docs/agent/TEST_STATUS.md
     ```

2. Focused verification:
   ```bash
   conda run -n femdes python manage.py test store.tests.test_accounts store.tests.test_invoices store.tests.test_staff_views store.tests.test_feedback -v 2
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
