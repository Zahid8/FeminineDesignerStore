# Current Task

## Task ID
TASK-018-FIX

## Title
Harden Razorpay flow, add missing tests, and sync docs

## Objective
T18 fixed the likely blank-SKU checkout crash at the service layer, but it does not yet satisfy the payment-gateway acceptance criteria.

The Razorpay implementation is almost completely untested, and `razorpay_payment()` creates a new Razorpay order every time the payment page is loaded. That overwrites `Order.gateway_order_id`, which can break retries and makes invalid/mismatched verification redirects unsafe because they redirect back into a view that creates a fresh gateway order. The docs also still describe T17/266 as current and list payment gateway integration as future work.

Do not rewrite checkout wholesale. Make a narrow corrective pass over the existing implementation.

## Required Fixes

1. Strengthen the blank-SKU checkout regression to cover the real browser-facing view path.
   - Use `Client`, add a product with `sku=None` or `sku=""` to the session cart, POST valid checkout data to `reverse("checkout")`, and assert:
     - response is not 500,
     - response redirects to the expected next page,
     - `Order` and `OrderItem` are created,
     - `OrderItem.sku == ""`,
     - the cart is cleared.
   - Keep the service-level test if useful, but it is not enough by itself.

2. Make Razorpay order creation idempotent for a local order.
   - If `order.gateway_order_id` already exists and the order is not paid, `razorpay_payment()` must reuse it instead of creating a new Razorpay order.
   - Avoid overwriting `gateway_order_id` on repeated page loads.
   - If Razorpay SDK order creation fails, do not 500. Show a recoverable error and keep the order pending.

3. Make verification genuinely POST-only and recoverable.
   - Do not let GET requests to the verification URL redirect to order success.
   - On invalid, missing, or mismatched Razorpay data, do not mark the order paid and do not create a new Razorpay order as a side effect of the error path.
   - Handle Razorpay signature exceptions and unexpected Razorpay client errors without returning 500.
   - Only mark paid when the posted `razorpay_order_id` matches the stored local `gateway_order_id` and `verify_payment_signature()` succeeds.

4. Add meaningful Razorpay tests.
   - Manual fallback: with Razorpay disabled, checkout redirects to order success and does not call/import the Razorpay client.
   - Razorpay enabled: checkout creates the local order, redirects to the payment page, and mocked `client.order.create()` receives amount in paise, currency `INR`, receipt `order.order_number`, and safe notes.
   - Repeated GET to the payment page reuses the existing stored `gateway_order_id` and does not call `order.create()` again.
   - Valid verification marks the matching order paid, sets `payment_method="razorpay"`, `payment_reference`, `gateway_payment_id`, and `paid_at`, then redirects to order success.
   - Invalid signature leaves the order unpaid/failed and returns a recoverable response.
   - Mismatched `razorpay_order_id` leaves the order unpaid and does not create a new gateway order.
   - Missing payment id/signature does not produce a 500.
   - Admin tests assert Razorpay gateway IDs are searchable/read-only as currently intended.

5. Sync docs.
   - Update `docs/agent/HANDOFF.md` summary/completed tasks so T18 is current and payment gateway integration is not listed as future work.
   - Update `docs/agent/TEST_STATUS.md` current state and command snippet to the real final test count after this fix.
   - Update `docs/agent/TASK_BOARD.md` only if its status/test count becomes stale.
   - Update `.agent/CONTINUITY.md` with a concise outcome and verification summary.

6. Document payment environment variables.
   - `.env.example` already has Razorpay variables; also document them in `README.md` and/or `deploy.md` if those docs cover deployment environment variables.
   - Do not include real keys.

## Acceptance Criteria

- The reported checkout 500 is covered by a browser-facing checkout POST test.
- Blank-SKU checkout still stores `OrderItem.sku == ""`.
- Razorpay order creation is idempotent for repeated payment page loads.
- Payment is marked paid only after server-side signature verification.
- Invalid/missing/mismatched Razorpay data never marks an order paid and never causes a 500.
- Tests mock Razorpay; no test performs a real network payment API call.
- Manual UPI fallback still works when Razorpay env vars are absent.
- Docs consistently report T18/T18-FIX completion and the final test count.
- Payment gateway is not listed as future work after it is complete.

## Required Verification

Run all commands from the repository root:

```bash
conda run -n femdes python manage.py test store.tests.test_cart store.tests.test_storefront -v 2
conda run -n femdes python manage.py test store.tests.test_admin store.tests.test_models -v 2
conda run -n femdes python manage.py test -v 1
conda run -n femdes python manage.py check
conda run -n femdes python manage.py makemigrations --check --dry-run
conda run -n femdes python -m pip check
rg -n "T0 through T17|266 tests|Payment gateway integration" docs/agent/HANDOFF.md docs/agent/TEST_STATUS.md
git diff --check HEAD^..HEAD
```

The `rg` command must return no matches after docs are synced.

## Notes

- Prefer patching the existing `razorpay_payment()` / `razorpay_verify()` flow instead of replacing the checkout architecture.
- It is acceptable to defer webhook support if clearly documented as future work; do not add an unverified webhook endpoint.
- Do not expose Razorpay secret keys in templates, logs, tests, or docs.
- Owner review policy: documentation-only drift should be carried into the next substantive task, not split into a standalone fix task. This task remains active because the current blockers include payment-flow behavior and missing tests, not docs only.
