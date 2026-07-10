# Current Task

## Task ID
TASK-021 — Light IndiChic-inspired blouse UI pass

## Goal

Use `web_temp/indichic` as a design reference and make the FemDes customer-facing UI feel similar in structure and polish, but as a light, pastel blouse boutique. Do not make the site dark.

## Reference To Inspect

Before implementation, inspect these files:

- `web_temp/indichic/frontend/src/pages/Home/index.js`
- `web_temp/indichic/frontend/src/pages/Home/components/Banner/index.js`
- `web_temp/indichic/frontend/src/pages/Home/components/Banner/components/Card/index.js`
- `web_temp/indichic/frontend/src/pages/Home/components/Promos/promo.js`
- `web_temp/indichic/frontend/src/components/Navbar.js`
- `web_temp/indichic/frontend/src/pages/Products-section/products.js`
- `web_temp/indichic/frontend/src/pages/Products-section/components/productCollection/productCollection.js`
- `web_temp/indichic/frontend/src/pages/Products-section/components/productCard/productCard.js`

Use these for layout inspiration only. Do not copy React/Tailwind code, dark backgrounds, source assets, unrelated categories, men/women clothing copy, or exact text.

## Required Design Direction

Adapt these IndiChic ideas into the existing Django/Kaira storefront:

1. Light centered navigation
   - Keep the existing Django/Kaira navigation behavior.
   - Add a cleaner centered brand/nav balance inspired by IndiChic.
   - Keep icons/actions readable on a light background.

2. Editorial hero
   - Use a large blouse-focused hero statement with supporting copy.
   - Keep the hero light and pastel, not black.
   - Use oversized rounded/capsule product or lifestyle imagery.
   - Add small floating product/discount/stat widgets if they improve the layout.
   - Keep the existing product/CTA links working.

3. Pill controls and utility actions
   - Use rounded pill CTAs, category/filter buttons, and action buttons.
   - Adapt search/cart/account/payment controls visually without changing URLs or behavior.

4. Product and collection cards
   - Add rounded product-card surfaces inspired by IndiChic cards.
   - Include circular or pill-shaped add/cart/wishlist-style action affordances only where existing behavior supports them.
   - Preserve product image, price, tags, stock/new/out-of-stock cues, add-to-cart, and Swiper/Kaira compatibility.

5. Light promo/editorial collage
   - Add or adapt a light blouse-focused promo/editorial section inspired by IndiChic's vertical fashion image collage.
   - Use existing blouse/product imagery where available.
   - Do not use dark full-section backgrounds.

6. Keep the pastel screenshot direction
   - Retain pale blue/off-white wave bands or soft section transitions.
   - Keep restrained blush, muted blue, soft yellow, warm coral/brown accents.
   - Keep the site feminine, airy, and blouse-only.

## Scope

Apply the visual system across the customer-facing flow, not only the home page:

- `templates/store/home.html`
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
- relevant `templates/store/partials/*`
- `static/store/style.css`
- relevant `store/tests/*`

## Constraints

- Do not change models, migrations, admin behavior, URLs, view names, form field names, CSRF behavior, cart/session behavior, checkout/order behavior, Razorpay behavior, account auth behavior, or seed data unless required by a failing test.
- Preserve Kaira/Bootstrap/Swiper contracts and TemplatesJungle attribution.
- Keep `static/store/style.css` scoped and reviewable; do not recreate whole-file churn.
- `reference.png` and `web_temp/indichic` are local references only. They must not become runtime/static assets.
- Avoid dark-mode styling. This task is explicitly for a light version.

## Required Tests

Add meaningful structural tests under `store/tests/`. Existing passing tests are not enough.

Tests must cover:

- home hero layout hooks;
- IndiChic-inspired light hero/card/pill/widget classes;
- product list category/search/empty-state hooks;
- product card action and price/stock/tag behavior still rendering;
- product detail specs/note/cart behavior still rendering;
- cart and checkout visual hooks plus form behavior;
- Razorpay payment page visual hooks plus payment form/context behavior;
- order success page;
- account login/register/profile/orders pages;
- navbar/search popup/cart offcanvas/footer attribution.

## Required Verification

Run and record results in `docs/agent/TEST_STATUS.md`:

```bash
conda run -n femdes python manage.py test store.tests.test_storefront store.tests.test_cart store.tests.test_razorpay -v 2
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

- The public storefront clearly reflects a light IndiChic-inspired design: centered clean nav, editorial hero, rounded capsule imagery, pill CTAs/filters, floating widgets/badges, rounded product cards, and light promo collage rhythm.
- The UI stays light/pastel and blouse-focused; no dark IndiChic section is copied.
- Existing storefront/cart/checkout/payment/account behavior still works.
- Structural tests prove the new visual hooks and key behavior.
- CSS diff is scoped and reviewable.
- No reference assets from `web_temp/indichic` or `reference.png` are used at runtime.
