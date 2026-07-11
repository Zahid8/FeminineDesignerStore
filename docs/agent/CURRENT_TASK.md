# Current Task

## Task ID
TASK-024-FIX2 — Strengthen staff dashboard stat tests and close task docs

## Context

Commit `1d8176d` fixed the staff dashboard implementation gaps from TASK-024-FIX:

- Dashboard now excludes staff users from `customer_count`.
- Dashboard now renders a visible non-paid payment metric.
- Staff order update is included in anonymous/non-staff access tests.
- Customer list renders admin user links and profile links when a profile exists.
- Stale `277 tests` and T23-FIX active text was removed from `HANDOFF.md`/`TEST_STATUS.md`.

The remaining issue is that `store/tests/test_staff_views.py::StaffDashboardTests.test_dashboard_has_distinct_counts` is still too weak. It checks generic substrings such as `">2<"` and `">1<"` that can be satisfied by other metric cards. For example, if active products incorrectly counted inactive products, the test could still pass because another metric also renders `2`.

Do not rewrite the staff feature. Make a narrow test-proof/doc completion fix.

## Required Fixes

1. Strengthen dashboard stat assertions.
   - Replace generic `assertContains(response, ">2<")` / `">1<"` checks with assertions that bind each label to its specific value.
   - Acceptable approaches:
     - Add stable `data-testid` attributes to each dashboard metric card and assert the exact rendered value near that label, or
     - parse the response HTML with a small stdlib `html.parser.HTMLParser` helper and assert a label-to-value mapping.
   - The test must fail independently if any of these are wrong:
     - customers count includes staff users,
     - inactive products are counted,
     - total order count is wrong,
     - paid payment count is wrong,
     - non-paid payment count is wrong,
     - non-paid metric card is removed.

2. Strengthen customer admin-link coverage.
   - Keep the existing user-admin link assertion.
   - Add an assertion for the profile admin link when a `CustomerProfile` exists:
     `reverse("admin:store_customerprofile_change", args=[profile.pk])`.

3. Close current task docs.
   - Update `docs/agent/CURRENT_TASK.md` to mark TASK-024-FIX2 complete only after verification passes, or write the next task if the review policy requires it.
   - Update `docs/agent/HANDOFF.md` and `docs/agent/TEST_STATUS.md` so they state T24/T24-FIX/T24-FIX2 completion and the actual final test count.
   - Preserve the PDF invoice deferral note.

## Acceptance Criteria

- Dashboard stat tests are label/value-specific, not generic substring checks.
- Tests fail if staff users are counted as customers.
- Tests fail if inactive products are counted.
- Tests fail if the non-paid card is removed or computed incorrectly.
- Customer list tests prove both user and profile admin links render for users with profiles.
- Staff dashboard/order/customer behavior remains unchanged except for test-friendly stable markup if needed.
- Focused tests, full tests, `check`, migration dry-run, `pip check`, stale-doc search, and diff whitespace checks pass.

## DeepSeek Self-Validation Loop

Before claiming completion, DeepSeek must run this loop and include the results in handoff notes:

1. Fail-first audit:
   - Confirm dashboard tests would fail if `customer_count` used `User.objects.filter(is_active=True).count()`.
   - Confirm dashboard tests would fail if `product_count` counted inactive products.
   - Confirm dashboard tests would fail if the non-paid metric card were removed.
   - Confirm customer-list tests would fail if the profile admin link were removed.
   - Confirm stale docs search returns no current-state matches:
     ```bash
     rg -n "277 tests|T23-FIX3 .*active|T23-FIX4 .*active|T24-FIX .*active|T18-FIX2 open|T0 through T20|T0 through T21" docs/agent/HANDOFF.md docs/agent/TEST_STATUS.md
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
   Confirm changes are limited to staff dashboard test-proof markup if needed, staff tests, and required docs.
