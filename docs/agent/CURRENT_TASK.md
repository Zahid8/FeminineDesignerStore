# Current Task

## Task ID
TASK-021-FIX — Heavy light-version IndiChic UI adaptation

## Review Context

The T21 implementation is not accepted. It only adds a few home-page hero classes, a three-card stat band, 10 lines of CSS, and one shallow substring test. That does not satisfy the requested heavy inspiration from `web_temp/indichic`, and it does not apply the design system across the customer-facing site.

The owner clarified: take heavy inspiration from `Zahid/Fem_des_shop/web_temp/indichic` and make the FemDes UI very similar to that design style and structural idea, but as a light blouse-only version.

## Goal

Build a structurally similar, light/pastel Django storefront adaptation of the local IndiChic reference across the public storefront. IndiChic design direction is now allowed to supersede Kaira visual and interaction conventions where needed. Do not copy React/Tailwind code, source assets, dark backgrounds, unrelated categories, men/women generic fashion copy, or exact IndiChic text.

## Reference Files To Inspect

Inspect these local files before editing:

- `web_temp/indichic/frontend/src/components/Navbar.js`
- `web_temp/indichic/frontend/src/pages/Home/index.js`
- `web_temp/indichic/frontend/src/pages/Home/components/Banner/index.js`
- `web_temp/indichic/frontend/src/pages/Home/components/Banner/components/Card/index.js`
- `web_temp/indichic/frontend/src/pages/Home/components/Promos/promo.js`
- `web_temp/indichic/frontend/src/pages/Products-section/products.js`
- `web_temp/indichic/frontend/src/pages/Products-section/components/productCollection/productCollection.js`
- `web_temp/indichic/frontend/src/pages/Products-section/components/productCard/productCard.js`

Use them for structural and visual inspiration only.

## Required Implementation

### 1. Site Shell And Navigation

- Update `templates/store/partials/navbar.html` and relevant CSS so the customer-facing shell has an IndiChic-like centered brand/nav balance.
- Keep all existing URLs, account/login/logout behavior, search, cart count, and cart/account access working.
- Kaira-specific search popup/offcanvas/carousel behavior may be replaced if the replacement is fully functional, tested, and visually closer to the IndiChic direction.
- Use light surfaces, rounded pill actions, compact icon/action clusters, and clear mobile behavior.
- Do not remove TemplatesJungle attribution from the footer.

### 2. Home Hero

Replace the current minimal T21 hero treatment with a richer IndiChic-inspired hero structure:

- editorial blouse-focused headline and supporting copy;
- two-column hero composition;
- oversized rounded/capsule image area;
- at least two floating widget/card elements around the hero image or hero copy;
- small stat counters/summary chips similar in structure to the reference;
- pill CTA buttons that keep existing product/detail/shop links working;
- light pastel/off-white background, not black or dark-mode styling.

### 3. Light Promo Image Collage

Replace the current three text-only promo cards with a light version of the IndiChic promo collage:

- use existing product/blouse imagery from current products/static assets;
- create a staggered/vertical collage rhythm with rounded image tiles;
- include blouse-only editorial copy;
- keep it light/pastel, never a copied black section;
- ensure images are real runtime assets already available to the Django app, not files from `web_temp/indichic` or `reference.png`.

### 4. Product Collection And Cards

Update `templates/store/product_list.html`, `templates/store/partials/product_card.html`, and relevant CSS:

- use pill category/tag/search/filter controls inspired by IndiChic;
- keep search, category, tag, empty state, price, tags, stock/new/out-of-stock cues, add-to-cart, and primary-image behavior intact;
- product cards should visually align with the IndiChic card idea: rounded surfaces, image-forward layout, circular/pill action affordances only where behavior exists, and clear blouse product information.

### 5. Product Detail, Cart, Checkout, Payment, Account Pages

Extend the same light design system to:

- `templates/store/product_detail.html`
- `templates/store/cart.html`
- `templates/store/checkout.html`
- `templates/store/razorpay_payment.html`
- `templates/store/order_success.html`
- `templates/store/account_login.html`
- `templates/store/account_register.html`
- `templates/store/account_profile.html`
- `templates/store/account_orders.html`
- `templates/store/partials/cart_offcanvas.html`
- `templates/store/partials/search_popup.html`
- `templates/store/partials/footer.html`

This does not mean a full rewrite of business logic. It means consistent page shells, light cards/panels, pill buttons, airy spacing, rounded image/form/payment/account surfaces, and no regression to behavior.

### 6. CSS Scope

- Keep changes in `static/store/style.css` reviewable and additive where possible.
- Do not reformat or rewrite the whole CSS file.
- Add a clearly named T21-FIX section with reusable classes for the light IndiChic adaptation.
- Avoid one-note dark/slate/purple/brown palettes. Keep blush, pale blue, off-white, soft yellow, coral/warm-brown accents restrained.

## Constraints

- Do not change models, migrations, admin behavior, URLs, view names, form field names, CSRF behavior, cart/session behavior, checkout/order behavior, Razorpay behavior, account auth behavior, or seed data unless a failing test proves it is required.
- Bootstrap/Kaira/Swiper visual and interaction contracts may be changed or removed where the IndiChic-inspired implementation is clearly better, but any replacement must be complete, responsive, and tested.
- Preserve Django URL names, forms, CSRF behavior, session cart semantics, checkout/payment/account behavior, and admin/data behavior.
- Preserve existing product images and uploaded-media behavior.
- `web_temp/indichic` and `reference.png` are references only and must not be runtime/static assets.
- Do not introduce inline styles for the new UI except where the existing template already has unavoidable legacy inline sizing; prefer CSS classes.

## Required Tests

Add meaningful structural tests under `store/tests/`. Do not satisfy this with isolated substring checks only.

Tests must prove:

- navbar has centered/light shell hooks while preserving search, cart, account/logout behavior;
- home has the expanded editorial hero, capsule image, floating widgets, stats/chips, and light collage section;
- product list has pill filter/search/category/tag/empty-state hooks and still filters correctly;
- product cards still render primary image, fallback image, price, active tags, stock/new/out-of-stock cues, and add-to-cart behavior;
- product detail still renders ready-made specs, optional measurement note, gallery/cart/customization behavior, with new visual hooks;
- cart and checkout pages have new visual hooks while form submission behavior remains covered;
- Razorpay page has new payment-shell visual hooks and existing hidden form/context behavior remains covered;
- order success page has new success-shell hooks and order number rendering;
- account login/register/profile/orders pages have new account-shell hooks and existing auth behavior remains covered;
- footer attribution remains present;
- search and cart interactions remain present and functional, whether implemented with the existing Kaira popup/offcanvas or a new tested IndiChic-style replacement.

Use DOM/structure-aware assertions where practical, not only `assertContains(response, "class-name")`.

## Required Verification

Run and record results in `docs/agent/TEST_STATUS.md`:

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

Also document a browser/screenshot pass in `docs/agent/TEST_STATUS.md` for:

- `/`
- `/products/`
- one product detail page
- `/cart/`
- `/checkout/` with cart items
- Razorpay payment page with test settings
- order success page
- account login/register/profile/orders

## Acceptance Criteria

- The public UI is recognizably a light, blouse-only structural adaptation of the local IndiChic reference: centered nav, editorial two-column hero, capsule imagery, floating widgets, stat chips, pill controls, image-collage promo rhythm, and rounded product cards.
- The design is applied beyond the home page to product list/detail, cart, checkout, Razorpay, order success, account pages, search popup, cart offcanvas, and footer.
- The site stays light/pastel and never copies the dark IndiChic promo section.
- Existing storefront, cart, checkout, Razorpay, account, search/cart access, and footer attribution behavior still works.
- If Kaira popup/offcanvas/carousel behavior is replaced, the replacement must be tested and must not break navigation, cart, search, product browsing, checkout, or mobile use.
- Tests are meaningful and cover both structure and behavior.
- CSS diff is scoped and reviewable.
- No assets/code from `web_temp/indichic` or `reference.png` are used at runtime.
