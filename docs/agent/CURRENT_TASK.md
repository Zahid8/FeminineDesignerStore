# Current Task

## Task ID
TASK-025-FIX — Strengthen account order search/filter tests and sync docs

## Context

Commit `c8f785f` implemented customer account order status filtering, order-number search, and empty states. The core view is correctly scoped through:

```python
Order.objects.filter(customer_user=request.user)
```

However, the new tests are not strong enough to prove the security-sensitive ownership behavior:

- `test_filter_never_shows_others_orders` asserts the other customer's email is absent, but `account_orders.html` does not render customer emails. If another user's matching order were rendered, this test could still pass.
- There is no test where the search term matches another user's order number and must return no result.
- `test_invalid_status_does_not_crash` only checks HTTP 200; it does not prove invalid status filters still keep results user-scoped.
- The no-orders empty state is implemented but not tested.
- Docs are stale: `HANDOFF.md` and `TEST_STATUS.md` still contain old `319 tests` / T24 current-state lines even though T25 claims 324 tests.

Do not rewrite the feature. Keep the existing account order route and view behavior unless stronger tests reveal a real bug.

## Required Fixes

1. Strengthen ownership tests.
   - Store the other user's order as `self.other_order`.
   - In status-filter tests, assert `self.other_order.order_number` is absent, not just the other user's email.
   - Add a search test that searches by `self.other_order.order_number` and asserts:
     - the response is 200,
     - `self.other_order.order_number` is not rendered,
     - the no-match empty state is rendered.

2. Strengthen invalid status coverage.
   - For `?status=bogus`, assert the page renders only the current user's orders and does not render `self.other_order.order_number`.
   - Keep invalid status non-crashing behavior.

3. Test both empty states.
   - Keep the existing no-match empty-state test.
   - Add a separate authenticated user with no orders and assert the `No orders yet` empty state appears.

4. Sync docs.
   - Update `docs/agent/HANDOFF.md` verification status to the actual full test count.
   - Update `docs/agent/TEST_STATUS.md` current state to T0 through T25 complete and the actual full test count.
   - If this fix is approved, write the next implementation-ready task into `docs/agent/CURRENT_TASK.md`.

## Acceptance Criteria

- Tests fail if `account_orders` accidentally searches or filters all orders instead of only `request.user` orders.
- Tests fail if a different user's order number is rendered during status filtering, order-number searching, or invalid status handling.
- Tests cover both empty states: no account orders and filtered/searched no matches.
- Existing account order filtering/search behavior remains intact.
- Existing order detail/tracking access control remains intact.
- No broad feature rewrite, new model, or new route is added unless required by a discovered bug.
- Focused tests, full tests, `check`, migration dry-run, `pip check`, stale-doc search, and diff whitespace checks pass.

## DeepSeek Self-Validation Loop

Before claiming completion, DeepSeek must run this loop and include the results in handoff notes:

1. Fail-first audit:
   - Temporarily change `account_orders` to start from `Order.objects.all()` and confirm the ownership tests fail.
   - Temporarily remove the no-orders empty-state branch and confirm the no-orders test fails.
   - Temporarily remove the no-match branch and confirm the no-match test fails.
   - Confirm stale docs search returns no current-state matches:
     ```bash
     rg -n "319 tests|T0 through T24|T24-FIX3|Next: T25|T25 .*active|318 tests|T22 is the next|T23-FIX3 .*active|T23-FIX4 .*active|T24-FIX .*active|T24-FIX2 .*complete" docs/agent/HANDOFF.md docs/agent/TEST_STATUS.md
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
