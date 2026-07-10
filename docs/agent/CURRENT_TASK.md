# Current Task

## Task ID
TASK-020-FIX2 — Finish the actual T20 redesign implementation and tests

## Review Result To Fix

Commit `e48b5b3` does not satisfy TASK-020-FIX. It removes `reference.png` from tracking and restores a few CSS rules, but it still only changes `templates/store/home.html` plus `static/store/style.css`, adds no tests, leaves inline styles in the home hero, and still fails the required CSS churn gate:

```bash
git diff --numstat 19762f0..HEAD -- static/store/style.css
# current result: 1753 1712 static/store/style.css
```

This is not a docs-only issue.

## Required Fixes

1. Resolve the CSS churn gate.
   - Make `static/store/style.css` reviewable relative to `19762f0`.
   - Prefer restoring the file close to the `19762f0` content and then applying only a small, scoped boutique CSS block.
   - The required command must no longer show whole-file-scale churn:

   ```bash
   git diff --numstat 19762f0..HEAD -- static/store/style.css
   ```

2. Remove remaining inline presentation styles introduced by T20.
   - Move the home hero heading and price colors out of `templates/store/home.html` and into named CSS classes.
   - Do not add new inline styles while fixing this.

3. Apply the blouse boutique visual system to the actual customer flow, not just home.
   - Touch the relevant templates/classes for:
     - `templates/store/product_list.html`
     - `templates/store/product_detail.html`
     - `templates/store/cart.html`
     - `templates/store/checkout.html`
     - `templates/store/razorpay_payment.html`
     - `templates/store/order_success.html`
     - `templates/store/account_login.html`
     - `templates/store/account_register.html`
     - `templates/store/account_profile.html`
     - `templates/store/account_orders.html`
     - shared partials as needed: navbar, search popup, cart offcanvas, footer, product card.
   - Keep existing URLs, form fields, CSRF, cart behavior, checkout/order behavior, Razorpay behavior, auth behavior, admin behavior, models, migrations, and seed data unchanged.
   - Preserve Kaira/Bootstrap/Swiper contracts and TemplatesJungle attribution.

4. Add meaningful structural tests.
   - Modify tests under `store/tests/`; do not rely only on existing 277 tests.
   - Add assertions that would fail if the required visual hooks/sections are removed.
   - Cover at minimum: home hero, product list/search empty state, product card, product detail specs/note area, cart and empty cart, checkout, Razorpay payment page, order success, account login/register/profile/orders, search popup, footer/attribution.
   - Keep tests behavior-aware: prove core forms/links/buttons still render while the new visual hooks are present.

5. Keep `reference.png` untracked.
   - It may remain ignored locally.
   - Do not use it as a runtime image or static asset.
   - Do not copy baby/kids text, imagery, motifs, or exact layout from it.

6. Keep TASK-018-FIX2 status honest.
   - If Razorpay order-create failure is still open, docs must say it is open and must not say all required tasks are done.
   - If you fix it, add focused tests proving a gateway-order-create failure does not clear the cart or strand the user with an unreachable unpaid local order.

## Required Verification

Run and record the results in `docs/agent/TEST_STATUS.md`:

```bash
conda run -n femdes python manage.py test store.tests.test_storefront store.tests.test_cart store.tests.test_razorpay -v 2
conda run -n femdes python manage.py test -v 1
conda run -n femdes python manage.py check
conda run -n femdes python manage.py makemigrations --check --dry-run
conda run -n femdes python manage.py collectstatic --noinput
conda run -n femdes python -m pip check
git diff --check
git diff --numstat 19762f0..HEAD -- static/store/style.css
git diff --name-only e48b5b3..HEAD -- store/tests templates/store static/store/style.css
rg -n "style=\"" templates/store/home.html templates/store/product_list.html templates/store/product_detail.html templates/store/cart.html templates/store/checkout.html templates/store/razorpay_payment.html templates/store/order_success.html templates/store/account_login.html templates/store/account_register.html templates/store/account_profile.html templates/store/account_orders.html
rg -n "No required tasks remain|T0 through T19|T18-FIX2 Razorpay reliability carryover documented" docs/agent/HANDOFF.md docs/agent/TEST_STATUS.md docs/agent/CURRENT_TASK.md
```

Also document a browser/screenshot pass for:

- `/`
- `/products/`
- one product detail page
- `/cart/`
- `/checkout/` with cart items
- Razorpay payment page with test settings
- order success page
- account login/register/profile/orders

## Acceptance Criteria

- CSS churn gate is fixed; `style.css` no longer appears as a whole-file rewrite from `19762f0`.
- T20 visual changes are present across the specified customer-facing templates, not only home.
- New structural tests cover the visual hooks and core behavior for the specified pages.
- No runtime use of `reference.png`; no copied baby/kids reference content.
- Existing behavior and all verification commands pass.
- Docs accurately report whether TASK-018-FIX2 is still open.
