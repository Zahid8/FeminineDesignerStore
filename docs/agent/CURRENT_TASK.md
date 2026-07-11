# Current Task

## Task ID
TASK-024-FIX — Complete staff dashboard metrics, access coverage, admin links, and docs sync

## Context

Commit `15f1ea0` added a staff dashboard, staff order list/update, staff customer list, and `store/tests/test_staff_views.py`. The focused/full suites pass, but the implementation does not yet satisfy every TASK-024 acceptance criterion.

Do not rewrite the entire staff feature. Keep the existing routes/templates and make narrow corrections.

## Blocking Findings To Fix

1. Dashboard payment metrics are incomplete.
   - `store/views.py::staff_dashboard` calculates `pending_count`, but `templates/store/staff_dashboard.html` never renders it.
   - The task required paid and pending/non-paid payment counts.
   - Add a visible dashboard card/metric for pending or non-paid payments.
   - Prefer `non_paid_count = Order.objects.exclude(payment_status="paid").count()` if the label says non-paid, or use only `payment_status="pending"` if the label says pending. Make the label and query agree.

2. Dashboard customer count is ambiguous and likely wrong.
   - Current code uses `User.objects.filter(is_active=True).count()`, which counts staff/admin accounts as customers.
   - Change the count to active non-staff users or customer profiles, and make the label/test match the chosen behavior.

3. Staff access coverage is incomplete.
   - `StaffDashboardAccessTests` checks dashboard, order list, and customer list, but not `staff_order_update`.
   - Add access tests for anonymous and non-staff users hitting `staff_order_update` with a real order number.

4. Staff customer list lacks admin change links.
   - TASK-024 required customer/profile rows to link to Django admin change pages where appropriate.
   - Add user admin links, and profile admin links when a profile exists.
   - Keep the page read-only; do not add destructive actions.

5. Tests are too superficial.
   - `test_dashboard_has_counts` asserts `">1<"` twice, which can pass from the same number or unrelated markup.
   - Replace with exact label/value assertions that prove customer count, active product count, total order count, paid count, and pending/non-paid count are each rendered.
   - Use fixtures with distinct values: for example 2 customers, 1 staff user, 1 inactive product, multiple orders with paid/pending/failed statuses.
   - Add a test that inactive products are not counted.
   - Add a test that staff users are not counted as customers if the implementation uses active non-staff users.

6. Documentation carryover is still stale.
   - `docs/agent/TEST_STATUS.md` still contains stale current-state text (`T23-FIX3 active`, `277 tests`).
   - `docs/agent/HANDOFF.md` still contains stale `277 tests` verification text.
   - Sync both files with actual T24-FIX verification results.

## Acceptance Criteria

- Staff dashboard displays and tests exact counts for customers, active products, total orders, paid payments, and pending/non-paid payments.
- Staff users are not counted as customers unless the label explicitly says users; tests lock this behavior.
- Staff-only access is tested for dashboard, order list, order update, and customer list.
- Order status update still accepts only valid `Order.STATUS_CHOICES` values and does not change payment status.
- Staff customer list includes Django admin change links for users and available profiles.
- No destructive customer/product/order actions are added.
- Existing account order tracking and invoice tests still pass.
- Docs contain no stale current-state matches for:
  ```bash
  rg -n "277 tests|T23-FIX3 .*active|T23-FIX4 .*active|T18-FIX2 open|T0 through T20|T0 through T21" docs/agent/HANDOFF.md docs/agent/TEST_STATUS.md
  ```
- Focused tests, full tests, `check`, migration dry-run, `pip check`, and diff whitespace checks pass.

## DeepSeek Self-Validation Loop

Before claiming completion, DeepSeek must run this loop and include the results in handoff notes:

1. Fail-first audit:
   - Confirm dashboard tests fail if the pending/non-paid metric card is removed.
   - Confirm dashboard tests fail if staff users are included in customer count.
   - Confirm access tests fail if `staff_order_update` is accessible to a non-staff user.
   - Confirm customer-list tests fail if admin links are removed.
   - Confirm stale docs search returns no current-state matches:
     ```bash
     rg -n "277 tests|T23-FIX3 .*active|T23-FIX4 .*active|T18-FIX2 open|T0 through T20|T0 through T21" docs/agent/HANDOFF.md docs/agent/TEST_STATUS.md
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
   Confirm changes are limited to staff dashboard/customer-list implementation, staff tests, and required docs.
