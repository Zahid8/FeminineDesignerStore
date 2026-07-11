# Current Task

## Task ID
TASK-021-FIX3 — Finish site-wide IndiChic pass and repair regressions

## Review Outcome

`TASK-021-FIX2` is not accepted.

Mechanical tests mostly pass, but the implementation does not satisfy the acceptance criteria. It only adds product-list pill filters/CSS utilities and shallow substring tests, while the required cart, checkout, Razorpay payment, order success, account pages, search popup, cart offcanvas, and footer design pass is still missing.

There are also concrete regressions:

- `index.html` was changed even though this legacy static file was out of scope, and its TemplatesJungle/ThemeWagon attribution was removed.
- `index.html` now has trailing whitespace, so `git diff --check 1200cc3..HEAD` fails.
- `templates/store/home.html` has invalid duplicate `class` attributes on promo stat elements, so `text-warm` is ignored.
- `templates/store/partials/navbar.html` still hides the brand on mobile via `d-none d-lg-block`; the CSS override cannot make it visible.
- `docs/agent/HANDOFF.md` and `docs/agent/TEST_STATUS.md` still claim the current state is T0-T20/277 tests.

## Required Fixes

### 1. Revert unrelated legacy static edit

- Restore the removed footer attribution block in root `index.html`.
- Remove the trailing whitespace in `index.html`.
- Do not edit root `index.html` further for this Django storefront UI task.

### 2. Fix current template regressions

- In `templates/store/home.html`, merge duplicate class attributes such as:
  - `class="promo-stat fs-4 fw-bold" class="text-warm"`
  into one valid class list.
- In `templates/store/partials/navbar.html`, keep the brand/logo visible on mobile. Do not rely on CSS to override Bootstrap `d-none`.
- If `.hero-float-widget` remains in CSS, render actual hero floating widgets or remove the unused hook.

### 3. Complete the missing site-wide IndiChic coverage

Apply the light IndiChic design shell to the remaining customer-facing Django templates:

- `templates/store/product_detail.html`
- `templates/store/cart.html`
- `templates/store/checkout.html`
- `templates/store/razorpay_payment.html`
- `templates/store/order_success.html`
- `templates/store/account_login.html`
- `templates/store/account_register.html`
- `templates/store/account_profile.html`
- `templates/store/account_orders.html`
- `templates/store/partials/search_popup.html`
- `templates/store/partials/cart_offcanvas.html`
- `templates/store/partials/footer.html`

Use the existing utility classes where appropriate (`page-shell`, `page-shell-wide`, `indichic-card`, `bg-soft`, `text-warm`, `filter-pill`) but do not add superficial unused classes. Preserve all URLs, forms, CSRF, cart/session behavior, checkout/order behavior, Razorpay behavior, account auth behavior, and footer attribution.

### 4. Strengthen tests

Add meaningful tests that prove structure plus behavior, not only class-name substrings:

- mobile and desktop navbar brand/search/cart/account/logout behavior;
- product detail ready-made specs, optional note, gallery, add-to-cart, buy-now/customization behavior with the new shell;
- cart update/remove/checkout behavior with the new shell;
- checkout form rendering and POST behavior with the new shell;
- Razorpay hidden fields/script context/form action with the new shell;
- order success order number/payment instructions with the new shell;
- account login/register/profile/orders auth behavior with the new shell;
- search popup and cart offcanvas remain functional;
- footer attribution remains present.

Use DOM relationship checks with the existing `HTMLParser` helper or an equivalent focused parser where practical.

### 5. Sync docs and verification

Update `docs/agent/HANDOFF.md` and `docs/agent/TEST_STATUS.md` with the actual T21-FIX3 state and current test count.

Run and record:

```bash
conda run -n femdes python manage.py test store.tests.test_storefront store.tests.test_cart store.tests.test_razorpay store.tests.test_accounts -v 2
conda run -n femdes python manage.py test -v 1
conda run -n femdes python manage.py check
conda run -n femdes python manage.py makemigrations --check --dry-run
conda run -n femdes python manage.py collectstatic --noinput
conda run -n femdes python -m pip check
git diff --check
git diff --numstat HEAD~1..HEAD -- static/store/style.css
```

Also document a browser/screenshot pass for `/`, `/products/`, one product detail page, `/cart/`, `/checkout/` with cart items, Razorpay payment page with test settings, order success, and account login/register/profile/orders.

## Acceptance Criteria

- Root `index.html` attribution is restored and `git diff --check` passes.
- The public Django storefront has a coherent light IndiChic design across product detail, cart, checkout, Razorpay, order success, account pages, search popup, cart offcanvas, and footer, not only home/product list.
- Existing business behavior still works.
- Tests meaningfully cover the new structure and preserved behavior.
- Handoff/test-status docs reflect the real current state.
- CSS diff remains scoped and no runtime asset/code is copied from `web_temp/indichic` or `reference.png`.
