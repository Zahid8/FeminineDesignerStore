# Current Task

## Task ID
TASK-021-FIX2 — Complete missing IndiChic storefront coverage

## Review Outcome

`TASK-021-FIX` is not accepted.

The implementation still only materially changes:

- `templates/store/home.html`
- `templates/store/partials/navbar.html`
- `static/store/style.css`
- one shallow test in `store/tests/test_storefront.py`

It does not apply the light IndiChic design system across product list/detail, cart, checkout, Razorpay payment, order success, account pages, search popup, cart offcanvas, or footer. The tests still only add substring assertions on the home page. `docs/agent/TEST_STATUS.md` and `docs/agent/HANDOFF.md` still report T0-T20 and no T21/T21-FIX verification.

## Goal

Complete the missing parts of the heavy light-version IndiChic adaptation without rewriting unrelated business logic.

Keep the existing T21-FIX home/nav work only if it remains useful, but finish the required site-wide UI system and prove it with meaningful tests.

## Required Fixes

### 1. Apply The Design System Beyond Home/Nav

Update these templates with consistent light IndiChic-inspired shells, cards, forms, pill actions, rounded surfaces, and airy layout:

- `templates/store/product_list.html`
- `templates/store/partials/product_card.html`
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

Do not change models, migrations, URLs, form field names, CSRF behavior, session cart semantics, checkout/order creation, Razorpay verification, account auth behavior, admin behavior, or seed data.

### 2. Fix Current T21-FIX Gaps

- Add at least two actual hero floating widgets/cards in `home.html`; `.hero-float-widget` currently exists only in CSS.
- Keep the mobile brand/logo visible in `navbar.html`; the current navbar hides the brand on small screens.
- Remove duplicated or unnecessary CSS hooks.
- Move new inline `style="color: var(--warm-brown);"` usages into CSS classes unless an existing legacy inline style is unavoidable.
- Preserve or improve the current promo image collage using only existing product/static assets.

### 3. Product List And Product Cards

Implement and test:

- pill category/tag/search/filter controls;
- empty-state styling;
- primary image and fallback image behavior;
- price, active tags, stock/new/out-of-stock cues;
- add-to-cart form/action still working;
- no runtime dependence on `web_temp/indichic` or `reference.png`.

### 4. Detail, Cart, Checkout, Payment, Account Flows

Implement and test:

- product detail visual shell while preserving ready-made specs, optional measurement note, gallery, add-to-cart, buy-now/customization behavior;
- cart visual shell while preserving update/remove/checkout behavior;
- checkout visual shell while preserving contact form POST behavior;
- Razorpay payment visual shell while preserving hidden fields, script context, payment form action, and verification behavior;
- order success visual shell while preserving order number rendering;
- account login/register/profile/orders visual shell while preserving auth redirects, logout POST, safe `next`, and order scoping.

### 5. Tests Must Be Meaningful

Add or strengthen tests under `store/tests/`. Do not rely on a few `assertContains(..., "class-name")` checks.

Tests must cover structure plus behavior for:

- navbar/search/cart/account/logout/mobile-brand behavior;
- home hero floating widgets, stats/chips, and promo collage;
- product list filters/search/empty state;
- product card image/price/tag/stock/add-to-cart behavior;
- product detail specs/note/gallery/cart/customization behavior;
- cart and checkout forms;
- Razorpay payment page context and form;
- order success;
- account login/register/profile/orders;
- footer attribution.

Use DOM relationship checks with `html.parser`, BeautifulSoup if already available, or focused template-response parsing where practical.

### 6. Documentation And Verification

Update `docs/agent/TEST_STATUS.md` and `docs/agent/HANDOFF.md` so they no longer claim the current state is T0-T20 only.

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

- The public UI is recognizably a light, blouse-only structural adaptation of `web_temp/indichic`, not a home-only patch.
- The design is applied across product, cart, checkout, payment, order success, account, search, cart offcanvas, navbar, and footer surfaces.
- Existing storefront/cart/checkout/Razorpay/account behavior still works.
- Tests prove the new structure and the preserved behavior.
- `docs/agent/TEST_STATUS.md` and `docs/agent/HANDOFF.md` reflect the real current state.
- CSS diff remains scoped and reviewable.
- No copied IndiChic code/assets and no runtime reference to `web_temp/indichic` or `reference.png`.
