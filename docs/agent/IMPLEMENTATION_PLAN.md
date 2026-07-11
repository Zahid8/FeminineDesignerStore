# FemDes Webstore Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the static Kaira template into a Django-backed FemDes webstore with admin-managed products, pricing, stock, discounts, newsletter subscribers, cart, checkout, and manual orders.

**Architecture:** Build a Django 5.2 LTS server-rendered application around the existing template. Preserve the current Kaira/Bootstrap look by moving assets into Django static files and splitting `index.html` into templates/partials. Use Django admin for staff management and session-backed cart behavior for public users.

**Tech Stack:** Python 3.12+, Django 5.2.x, SQLite for local development, optional PostgreSQL through `DATABASE_URL`, Pillow, WhiteNoise, Bootstrap 5, jQuery, Swiper, existing Kaira CSS/JS assets.

---

## Scope Rules

Required MVP:

- Django scaffold and configuration.
- Static asset migration.
- Catalog, image, discount, newsletter, cart, checkout, order, and site-settings models/services/views.
- Django admin for CRUD.
- Server-rendered storefront pages.
- Automated Django tests.

Optional after MVP:

- Payment gateway.
- Customer accounts.
- Wishlist persistence.
- Shipping/tax integrations.
- Blog CMS.
- Instagram API feed.
- Custom admin dashboard.

Do not implement optional work until all MVP acceptance criteria pass.

## Task 0: Confirm Baseline And Preserve Static Source

**Files to modify:**

- Create: `legacy_static/index.html`
- Create: `legacy_static/readme.txt`
- Create: `.gitignore`
- Create: `.env.example`

**Expected behavior:**

- Original static files remain available for comparison.
- Local/generated files are excluded from future Git tracking if Git is initialized.

**Steps:**

- [ ] Run `test ! -d .git && echo "no git repo"` and confirm the output is `no git repo`.
- [ ] Run `mkdir -p legacy_static`.
- [ ] Copy `index.html` to `legacy_static/index.html`.
- [ ] Copy `readme.txt` to `legacy_static/readme.txt`.
- [ ] Create `.gitignore` with:

```text
.env
.venv/
venv/
__pycache__/
*.pyc
db.sqlite3
media/
staticfiles/
.omx/
```

- [ ] Create `.env.example` with:

```text
DJANGO_SECRET_KEY=replace-with-a-long-random-secret
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_URL=sqlite:///db.sqlite3
DJANGO_CSRF_TRUSTED_ORIGINS=
```

**Tests to run:**

```bash
diff -q index.html legacy_static/index.html
diff -q readme.txt legacy_static/readme.txt
test -f .gitignore
test -f .env.example
```

**Likely edge cases:**

- Existing `legacy_static/` may already exist. Do not delete it; compare contents before overwriting.
- If Git is initialized later, ensure `.gitignore` is committed before generated files are created.

**Acceptance criteria:**

- Diffs report no differences.
- Original static files remain in place.
- No source functionality changes.

## Task 1: Scaffold Django Project

**Files to modify:**

- Create: `requirements.txt`
- Create: `manage.py`
- Create: `femdes_site/__init__.py`
- Create: `femdes_site/settings.py`
- Create: `femdes_site/urls.py`
- Create: `femdes_site/asgi.py`
- Create: `femdes_site/wsgi.py`
- Create: `store/__init__.py`
- Create: `store/apps.py`
- Create: `store/models.py`
- Create: `store/views.py`
- Create: `store/admin.py`
- Create: `store/tests/__init__.py`

**Expected behavior:**

- Django project imports and passes `manage.py check`.

**Steps:**

- [ ] Create `requirements.txt`:

```text
Django>=5.2,<5.3
Pillow>=10.0
dj-database-url>=2.2
python-dotenv>=1.0
whitenoise>=6.6
psycopg[binary]>=3.1
```

- [ ] Run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
django-admin startproject femdes_site .
python manage.py startapp store
mkdir -p store/tests
touch store/tests/__init__.py
```

- [ ] Add `store` to `INSTALLED_APPS`.
- [ ] Add `whitenoise.middleware.WhiteNoiseMiddleware` after `SecurityMiddleware`.
- [ ] Add `.env` loading, `DATABASE_URL`, `STATICFILES_DIRS`, `STATIC_ROOT`, `MEDIA_URL`, and `MEDIA_ROOT` settings as described in `docs/architecture.md`.
- [ ] Update `femdes_site/urls.py` to include `path("", include("store.urls"))` after `store/urls.py` exists in Task 5.

**Tests to run:**

```bash
source .venv/bin/activate
python manage.py check
```

**Likely edge cases:**

- `django-admin` may not be on PATH until the virtual environment is activated.
- `psycopg[binary]` is only needed for production PostgreSQL support; keep it in requirements but local SQLite should still work.

**Acceptance criteria:**

- `python manage.py check` exits successfully.
- No current static assets are moved in this task.

## Task 2: Move Static Assets Into Django Static Tree

**Files to modify:**

- Move: `css/` to `static/store/css/`
- Move: `js/` to `static/store/js/`
- Move: `images/` to `static/store/images/`
- Move: `style.css` to `static/store/style.css`

**Expected behavior:**

- All Kaira assets are available through Django static files.
- Asset names remain unchanged.

**Steps:**

- [ ] Confirm `legacy_static/index.html` exists before moving any assets.
- [ ] Run:

```bash
mkdir -p static/store
mv css static/store/css
mv js static/store/js
mv images static/store/images
mv style.css static/store/style.css
```

- [ ] Update no template references yet unless Task 4 has started.

**Tests to run:**

```bash
test -f static/store/style.css
test -f static/store/css/vendor.css
test -f static/store/js/script.min.js
test -f static/store/images/main-logo.png
test -f static/store/images/product-item-1.jpg
python manage.py collectstatic --noinput
```

**Likely edge cases:**

- If directories were already moved, do not create duplicate `static/store/css/css`.
- `collectstatic` requires valid Django settings from Task 1.

**Acceptance criteria:**

- Static assets exist in `static/store/`.
- `collectstatic` completes.
- Existing filenames are preserved.

## Task 3: Add Database Models

**Files to modify:**

- Modify: `store/models.py`
- Create through command: `store/migrations/0001_initial.py`
- Create: `store/tests/test_models.py`
- Create: `store/tests/test_discounts.py`

**Expected behavior:**

- Database can represent store settings, categories, products, images, discounts, newsletter subscribers, orders, and order items.

**Model requirements:**

- `SiteSettings`: one-row store contact/social/currency data.
- `Category`: `name`, `slug`, `description`, `image`, `is_active`, `sort_order`, timestamps.
- `Product`: `name`, `slug`, `sku`, `category`, descriptions, `price`, `compare_at_price`, `stock_quantity`, flags, options, timestamps.
- `ProductImage`: product image, alt text, primary flag, sort order.
- `Discount`: percent/fixed, global/category/product scope, date range, active flag, priority.
- `NewsletterSubscriber`: unique email, active flag, created timestamp.
- `Order`: order number, status, customer fields, totals, timestamps.
- `OrderItem`: order line snapshot fields.

**Tests to run:**

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py test store.tests.test_models store.tests.test_discounts
```

**Likely edge cases:**

- Percent discounts above 100 must fail validation.
- Fixed discount cannot reduce effective price below zero.
- Product-scoped discounts require a product and no category.
- Category-scoped discounts require a category and no product.
- Global discounts require no product/category.
- Only one primary image should remain per product.
- `compare_at_price` must be empty or greater than/equal to `price`.

**Acceptance criteria:**

- Migrations apply cleanly.
- Model and discount tests pass.
- Effective price calculation is deterministic and Decimal-based.

## Task 4: Configure Django Admin

**Files to modify:**

- Modify: `store/admin.py`
- Create: `store/tests/test_admin.py`

**Expected behavior:**

- Staff can manage store data through `/admin/`.

**Required admin features:**

- Product image inline under Product.
- Product list filters for active, category, new arrival, best seller, recommended, discount allowed.
- Product search by name, SKU, and short description.
- Slug prepopulation from name.
- Readonly order totals and order-item snapshots.
- Order search by order number, email, phone, and customer name.
- SiteSettings restricted to one row.

**Tests to run:**

```bash
python manage.py test store.tests.test_admin
```

**Likely edge cases:**

- Anonymous user must be redirected from admin.
- Superuser must access product changelist.
- Staff without proper permissions should not mutate models outside assigned permissions.

**Acceptance criteria:**

- All models are registered.
- Product images are editable inline.
- Orders preserve readonly historical line data.

## Task 5: Add Forms, Selectors, Services, URLs, And Views

**Files to modify:**

- Create: `store/forms.py`
- Create: `store/selectors.py`
- Create: `store/services.py`
- Create: `store/urls.py`
- Modify: `store/views.py`
- Modify: `femdes_site/urls.py`
- Create: `store/tests/test_cart.py`
- Create: `store/tests/test_storefront.py`

**Expected behavior:**

- Storefront views render database-backed pages.
- Cart behavior is session-backed.
- Checkout creates manual orders and decrements stock.

**Required public routes:**

```python
path("", views.home, name="home")
path("shop/", views.product_list, name="product_list")
path("products/<slug:slug>/", views.product_detail, name="product_detail")
path("cart/", views.cart_detail, name="cart_detail")
path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart")
path("cart/update/<str:cart_key>/", views.update_cart, name="update_cart")
path("cart/remove/<str:cart_key>/", views.remove_from_cart, name="remove_from_cart")
path("checkout/", views.checkout, name="checkout")
path("orders/<str:order_number>/success/", views.order_success, name="order_success")
path("newsletter/subscribe/", views.newsletter_subscribe, name="newsletter_subscribe")
```

**Tests to run:**

```bash
python manage.py test store.tests.test_cart store.tests.test_storefront
```

**Likely edge cases:**

- Adding inactive product must fail.
- Adding out-of-stock product must fail.
- Checkout must revalidate stock in a transaction.
- Empty cart checkout must redirect to cart.
- Search with no matches must render an empty state.
- Newsletter duplicate signup must not crash.

**Acceptance criteria:**

- Required routes exist.
- Cart count and totals reflect session state.
- Checkout creates order and order items with price snapshots.

## Task 6: Convert Static HTML Into Templates

**Files to modify:**

- Create: `templates/base.html`
- Create: `templates/store/home.html`
- Create: `templates/store/product_list.html`
- Create: `templates/store/product_detail.html`
- Create: `templates/store/cart.html`
- Create: `templates/store/checkout.html`
- Create: `templates/store/order_success.html`
- Create: `templates/store/partials/icons.html`
- Create: `templates/store/partials/navbar.html`
- Create: `templates/store/partials/search_popup.html`
- Create: `templates/store/partials/cart_offcanvas.html`
- Create: `templates/store/partials/product_card.html`
- Create: `templates/store/partials/category_card.html`
- Create: `templates/store/partials/footer.html`

**Expected behavior:**

- The Kaira layout renders through Django templates using database data.

**Steps:**

- [ ] Copy the SVG icon sprite from `legacy_static/index.html` into `icons.html`.
- [ ] Move the head/script shell into `base.html`.
- [ ] Convert static asset references to concrete `{% static %}` paths such as `{% static 'store/style.css' %}`, `{% static 'store/js/script.min.js' %}`, and `{% static 'store/images/main-logo.png' %}`.
- [ ] Move navbar/search/cart/footer into partials.
- [ ] Replace hard-coded product cards with `product_card.html`.
- [ ] Replace hard-coded category cards with `category_card.html`.
- [ ] Keep carousel wrapper classes required by `js/script.min.js`.
- [ ] Preserve TemplatesJungle/ThemeWagon attribution.

**Tests to run:**

```bash
python manage.py test store.tests.test_storefront
python manage.py collectstatic --noinput
python manage.py runserver
```

Manual checks:

- `/` loads with styling.
- Search popup opens.
- Cart offcanvas opens.
- Product carousel sections initialize.
- Product cards show database-backed prices.

**Likely edge cases:**

- Missing `{% load static %}` causes broken assets.
- Swiper selectors require matching carousel IDs/classes.
- Button forms inside hover-effect links may need small markup adjustment while preserving appearance.

**Acceptance criteria:**

- Homepage visually resembles original Kaira template.
- Public product data comes from database queries, not hard-coded repeated cards.

## Task 7: Add Seed Command

**Files to modify:**

- Create: `store/management/__init__.py`
- Create: `store/management/commands/__init__.py`
- Create: `store/management/commands/seed_demo_store.py`
- Create: `store/tests/test_seed.py`

**Expected behavior:**

- Local developer can populate demo FemDes data from existing assets.

**Required seed data:**

- Site settings for FemDes.
- Categories: Dresses, Shirts, Jackets, Sweaters, Accessories.
- Demo products based on current template names and prices.
- Product images copied from `static/store/images/` into `media/products/demo/` and attached through `ProductImage`.

**Tests to run:**

```bash
python manage.py seed_demo_store
python manage.py seed_demo_store
python manage.py test store.tests.test_seed
```

**Likely edge cases:**

- Command must be idempotent.
- Missing static image should produce a clear command error.

**Acceptance criteria:**

- Running seed twice does not duplicate categories/products/settings.
- Homepage has enough products/categories to render.

## Task 8: Full Verification And Documentation Update

**Files to modify:**

- Modify: `docs/agent/TEST_STATUS.md`
- Modify: `docs/agent/TASK_BOARD.md`
- Modify: `docs/agent/HANDOFF.md`
- Modify: `.agent/CONTINUITY.md`

**Expected behavior:**

- Project status is accurate after implementation.

**Tests to run:**

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py collectstatic --noinput
python manage.py runserver
```

Manual checks:

- Add product in admin.
- Change product price in admin.
- Add discount in admin.
- Confirm price changes on storefront.
- Add to cart.
- Update quantity.
- Complete checkout.
- Confirm order appears in admin.

**Likely edge cases:**

- `makemigrations --check --dry-run` may fail if a model change lacks migration.
- `collectstatic` may fail on missing static references.
- Manual checkout may fail if stock was consumed by previous tests.

**Acceptance criteria:**

- Test status doc records exact passing commands.
- Task board is updated.
- Handoff includes remaining optional work only.

---

## Post-MVP Reference Feature Roadmap

The owner requested feature inspiration from `web_temp/indichic/ECommerceSite-Django`.
Use it as a local reference for feature shape only. Do not copy its code, cookie-based
cart, old Bootstrap snippets, inline CSS, fake card payment handling, or unsafe profile
password update behavior.

FemDes already has these reference-equivalent features:

- Django admin-backed product, category, tag, discount, order, payment, and site settings management.
- Customer registration, login, logout, profile page, and account orders.
- Session-backed add/update/remove cart.
- Product search, category filters, and tag filters.
- Checkout with guest support and authenticated order linking.
- Manual UPI payment tracking and Razorpay order/payment verification.
- Product image management through Django admin.

The missing or incomplete reference-inspired features are tracked below as separate
DeepSeek-sized tasks.

## Task 22: Customer Profile Details And Editable Account Profile

**Reference files:**

- `web_temp/indichic/ECommerceSite-Django/ecom/models.py` (`Customer`)
- `web_temp/indichic/ECommerceSite-Django/ecom/forms.py` (`CustomerForm`)
- `web_temp/indichic/ECommerceSite-Django/ecom/views.py` (`my_profile_view`, `edit_profile_view`)
- `web_temp/indichic/ECommerceSite-Django/templates/ecom/my_profile.html`
- `web_temp/indichic/ECommerceSite-Django/templates/ecom/edit_profile.html`

**Files to modify:**

- `store/models.py`
- `store/forms.py`
- `store/views.py`
- `store/urls.py`
- `store/admin.py`
- `templates/store/account_profile.html`
- Create: `templates/store/account_profile_edit.html`
- `store/tests/test_accounts.py`
- `store/tests/test_admin.py`
- migrations

**Expected behavior:**

- Registered customers have persistent profile details: phone, shipping address, optional profile image.
- Profile details can be edited from the account area.
- Checkout GET is prefilled for authenticated users from profile data.
- Guest checkout remains unchanged.
- Staff can inspect/search customer profiles from admin.

**Tests to run:**

```bash
conda run -n femdes python manage.py test store.tests.test_accounts store.tests.test_admin store.tests.test_models store.tests.test_storefront -v 2
conda run -n femdes python manage.py test -v 1
conda run -n femdes python manage.py check
conda run -n femdes python manage.py makemigrations --check --dry-run
conda run -n femdes python manage.py collectstatic --noinput
conda run -n femdes python -m pip check
git diff --check
```

**Acceptance criteria:**

- Customer profile is created reliably for registered users.
- Profile edit is authenticated, validates email uniqueness, and does not expose password changes.
- Checkout prefill works only for GET and never overwrites POST data.
- Admin profile management is searchable and tested.

## Task 23: Customer Order Tracking And Invoice Download

**Reference files:**

- `web_temp/indichic/ECommerceSite-Django/ecom/views.py` (`my_order_view`, `download_invoice_view`)
- `web_temp/indichic/ECommerceSite-Django/templates/ecom/my_order.html`
- `web_temp/indichic/ECommerceSite-Django/templates/ecom/download_invoice.html`

**Files to modify:**

- `requirements.txt` if a PDF library is added
- `store/views.py`
- `store/urls.py`
- `store/selectors.py` or service helper if useful
- `templates/store/account_orders.html`
- Create: `templates/store/account_order_detail.html`
- Create: `templates/store/invoice.html`
- `store/tests/test_accounts.py`
- Create or extend: `store/tests/test_invoices.py`

**Expected behavior:**

- Authenticated customers can open an order detail/tracking page for their own orders.
- Order tracking displays a status timeline derived from existing `Order.status`.
- Customers can download an invoice PDF for their own order.
- Unauthorized users cannot access other customers' order detail or invoice.

**Implementation notes:**

- Prefer a maintained PDF approach such as ReportLab if adding a dependency.
- If PDF dependency is too heavy for one task, first implement a printable HTML invoice and a tested service boundary, then add PDF in the next task.
- Do not copy the reference app's `xhtml2pdf` code blindly.

**Tests to run:**

```bash
conda run -n femdes python manage.py test store.tests.test_accounts store.tests.test_invoices -v 2
conda run -n femdes python manage.py test -v 1
conda run -n femdes python manage.py check
conda run -n femdes python manage.py makemigrations --check --dry-run
conda run -n femdes python -m pip check
git diff --check
```

**Acceptance criteria:**

- Order tracking timeline matches each supported order status.
- Invoice contains store identity, order number/date/status, customer details, item snapshots, totals, and payment status.
- PDF response uses `application/pdf` and meaningful filename.
- Cross-user access is blocked.

## Task 24: Staff Operations Dashboard

**Reference files:**

- `web_temp/indichic/ECommerceSite-Django/ecom/views.py` admin dashboard/customer/product/order views
- `web_temp/indichic/ECommerceSite-Django/templates/ecom/admin_dashboard.html`
- `web_temp/indichic/ECommerceSite-Django/templates/ecom/admin_view_booking.html`
- `web_temp/indichic/ECommerceSite-Django/templates/ecom/view_customer.html`
- `web_temp/indichic/ECommerceSite-Django/templates/ecom/admin_products.html`
- `web_temp/indichic/ECommerceSite-Django/templates/ecom/update_order.html`

**Files to modify:**

- `store/views.py`
- `store/urls.py`
- `store/admin.py` only if needed
- Create: `templates/store/staff_dashboard.html`
- Create: `templates/store/staff_orders.html`
- Create: `templates/store/staff_order_update.html`
- Create: `templates/store/staff_customers.html`
- `store/tests/test_admin.py`
- Create or extend: `store/tests/test_staff_views.py`

**Expected behavior:**

- Staff users have an operations dashboard with counts for customers, products, orders, paid/pending payments, and recent orders.
- Staff can list orders and update order status through a small tested view.
- Staff can list customer profiles and link to Django admin change pages where appropriate.
- Non-staff users cannot access staff views.

**Constraints:**

- Keep Django admin as the source of truth for product CRUD unless the owner explicitly requests a separate product CRUD UI.
- Do not add destructive customer/product/order delete views in public templates.
- Use permission/staff checks, not only login checks.

**Acceptance criteria:**

- Dashboard stats are correct.
- Staff-only access is enforced.
- Order status update validates allowed statuses and does not change payment status.
- Existing Django admin remains functional.

## Task 25: Customer-Facing Order Status Notifications And Search

**Reference files:**

- `web_temp/indichic/ECommerceSite-Django/templates/ecom/my_order.html`
- `web_temp/indichic/ECommerceSite-Django/ecom/views.py` order status handling

**Files to modify:**

- `store/models.py` if status timestamp fields are needed
- `store/views.py`
- `store/urls.py`
- `templates/store/account_orders.html`
- `templates/store/account_order_detail.html`
- `store/tests/test_accounts.py`
- migrations if new fields are added

**Expected behavior:**

- Account orders can be filtered/searched by order number/status.
- Order tracking clearly shows pending, confirmed, processing/shipped, completed, cancelled states.
- Status changes made by staff/admin are reflected on customer pages.

**Acceptance criteria:**

- Customer can only search/filter their own orders.
- Empty states are clear.
- Status filters and timeline are tested.

## Task 26: Contact And Feedback Capture

**Reference files:**

- `web_temp/indichic/ECommerceSite-Django/ecom/models.py` (`Feedback`)
- `web_temp/indichic/ECommerceSite-Django/ecom/forms.py` (`FeedbackForm`, `ContactusForm`)
- `web_temp/indichic/ECommerceSite-Django/ecom/views.py` (`send_feedback_view`, `contactus_view`)
- `web_temp/indichic/ECommerceSite-Django/templates/ecom/contactus.html`
- `web_temp/indichic/ECommerceSite-Django/templates/ecom/view_feedback.html`

**Files to modify:**

- `store/models.py`
- `store/forms.py`
- `store/views.py`
- `store/urls.py`
- `store/admin.py`
- Create: `templates/store/contact.html`
- Create: `templates/store/contact_success.html`
- tests under `store/tests/`
- migrations

**Expected behavior:**

- Public contact/feedback form stores submissions safely.
- Admin can review and search submissions.
- Optional email sending must fail gracefully and be covered by tests.

**Acceptance criteria:**

- CSRF-protected POST creates one feedback/contact row.
- Invalid submissions show form errors.
- Admin search/list display is tested.

## Task 27: Client-Side Interaction Polish

**Reference area:**

- Reference app advertises basic client-side interaction, but its implementation is mostly older templates. Use the feature idea only.

**Files to modify:**

- `static/store/js/` or a new small `static/store/js/femdes.js`
- affected templates/partials
- `store/tests/test_storefront.py`
- browser verification notes in `docs/agent/TEST_STATUS.md`

**Expected behavior:**

- Quantity controls, cart/remove affordances, search UI, and order tracking interactions feel immediate and polished.
- All behavior progressively enhances existing server-rendered forms.
- Site still works without JavaScript.

**Acceptance criteria:**

- No business logic depends only on JavaScript.
- Form submissions and CSRF remain intact.
- Browser pass confirms cart/search/order-tracking interactions.
