# FemDes Webstore Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert this static Kaira fashion-store HTML template into a database-backed FemDes webstore with a secure admin panel for managing products, images, categories, prices, inventory, discounts, newsletter subscribers, and customer orders.

**Architecture:** Use Django 5.2 LTS as a server-rendered web application. Keep the current Kaira Bootstrap visual design, move static assets into Django static files, convert repeated hard-coded HTML blocks into reusable templates, and drive catalog/cart/order behavior from Django models and sessions. Use SQLite for local development and support PostgreSQL through `DATABASE_URL` for production.

**Tech Stack:** Python 3.12+, Django 5.2.x, SQLite local database, optional PostgreSQL production database via `dj-database-url`, Pillow for product image uploads, WhiteNoise for static serving, Bootstrap/Kaira CSS/JS preserved from the existing template, Django admin for the staff control panel.

---

## 1. Current Repo Assessment

This repo is not a web application yet. It is a static HTML/CSS/JS template.

Current files inspected:

- `index.html`: 1,425-line static homepage. Contains the SVG icon sprite, search popup, cart offcanvas, navbar, hero carousel, feature blocks, category blocks, three repeated product carousel sections, collection feature, video block, testimonials, blog preview, logo bar, newsletter form, Instagram strip, footer, and script tags.
- `style.css`: 1,542-line main Kaira stylesheet. Includes Bootstrap variable overrides, typography, dark theme hooks, search popup styles, Swiper arrow styles, image hover effects, product card styles, single-product styles, filter/sidebar styles, and button/link effects.
- `css/`: vendor CSS plus `normalize.css`, `vendor.css`, `swiper-bundle.min.css`, and `ajax-loader.gif`.
- `js/`: template scripts, including `jquery.min.js`, `plugins.js`, `SmoothScroll.js`, `modernizr.js`, and `script.min.js`. `script.min.js` initializes Swiper carousels, quantity controls, search popup, AOS animation, image zoom, Colorbox video, and sticky product info.
- `images/`: 56 JPG files, 14 PNG files, and 1 SVG logo. These are currently referenced by relative paths such as `images/product-item-1.jpg`.
- `readme.txt`: Template license and credits. The free license says the TemplatesJungle credit link must remain unless the owner has paid for no-attribution rights.
- `.agent/CONTINUITY.md`: local agent continuity file. Preserve it unless the owner asks to remove it.
- `.omx/`: local automation state/log files. Do not treat this as application source.

Important observations:

- There is no `package.json`, Python project, backend framework, database config, or build pipeline.
- There is no Git repository initialized in this directory.
- All product names, prices, cart rows, category links, search categories, and newsletter form behavior are hard-coded.
- Cart and wishlist counters are visual only. They do not update from real state.
- The current homepage links mostly route back to `index.html`.
- Existing Kaira styling can be preserved with server-rendered templates. A SPA rewrite is unnecessary for the requested admin/database workflow.

## 2. MVP Scope

Build these features in the first implementation:

- Storefront homepage at `/` using the existing Kaira design.
- Product listing page at `/shop/`.
- Product detail page at `/products/<slug>/`.
- Category filtering at `/shop/?category=<slug>`.
- Search at `/shop/?q=<query>`.
- Session-backed cart with add, update quantity, remove, and cart summary.
- Checkout form that creates an order for manual fulfillment. Do not collect card details in this app.
- Order success page with order number.
- Django admin panel at `/admin/`.
- Admin CRUD for categories, products, product images, discounts, orders, and newsletter subscribers.
- Admin product controls for active/inactive status, featured status, new-arrival flag, best-seller flag, related/recommended flag, price, stock, SKU, size/color fields, and discount eligibility.
- Discount system supporting active date ranges, percentage discounts, fixed-amount discounts, product scope, category scope, and global scope.
- Newsletter subscription capture.
- Uploaded product images stored under `media/products/`.
- Existing template images moved under Django static files and used for seed/demo products.

Out of MVP:

- Payment gateway integration.
- Customer accounts.
- Wishlist persistence.
- Shipping carrier API integration.
- Tax calculation by jurisdiction.
- Multi-vendor marketplace behavior.
- Advanced returns workflow.
- Real Instagram API integration.

Phase 2 can add Stripe/PayPal checkout, user accounts, email notifications, coupons at checkout, and shipping-rate integrations after the core catalog/admin/order flow works.

## 3. Recommended File Structure

Create this structure:

```text
kaira-1.0.0/
  manage.py
  requirements.txt
  .env.example
  .gitignore
  implementation_plan.md
  femdes_site/
    __init__.py
    asgi.py
    settings.py
    urls.py
    wsgi.py
  store/
    __init__.py
    admin.py
    apps.py
    context_processors.py
    forms.py
    models.py
    selectors.py
    services.py
    urls.py
    views.py
    management/
      __init__.py
      commands/
        __init__.py
        seed_demo_store.py
    migrations/
      __init__.py
    tests/
      __init__.py
      test_admin.py
      test_cart.py
      test_discounts.py
      test_models.py
      test_storefront.py
  templates/
    base.html
    store/
      cart.html
      checkout.html
      home.html
      order_success.html
      product_detail.html
      product_list.html
      partials/
        cart_offcanvas.html
        category_card.html
        footer.html
        hero_slide.html
        icons.html
        navbar.html
        product_card.html
        search_popup.html
  static/
    store/
      css/
        normalize.css
        swiper-bundle.min.css
        vendor.css
      images/
        existing template image files
      js/
        SmoothScroll.js
        jquery.min.js
        modernizr.js
        plugins.js
        script.min.js
      style.css
  media/
    products/
  legacy_static/
    index.html
    readme.txt
```

Notes:

- Move the current `index.html` and `readme.txt` into `legacy_static/` only after Django templates are working. This preserves the original source for comparison.
- Move `css/`, `js/`, `images/`, and `style.css` into `static/store/`.
- Preserve existing filenames unless there is a direct collision with uploaded media.
- Ignore `.omx/`, local databases, virtual environments, and uploaded media in `.gitignore`.

## 4. Environment Setup

Create `requirements.txt`:

```text
Django>=5.2,<5.3
Pillow>=10.0
dj-database-url>=2.2
python-dotenv>=1.0
whitenoise>=6.6
psycopg[binary]>=3.1
```

Create `.env.example`:

```text
DJANGO_SECRET_KEY=replace-with-a-long-random-secret
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_URL=sqlite:///db.sqlite3
DJANGO_CSRF_TRUSTED_ORIGINS=
```

Create `.gitignore`:

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

Setup commands:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
django-admin startproject femdes_site .
python manage.py startapp store
```

Expected result:

- `python manage.py check` exits with `System check identified no issues`.
- `python manage.py runserver` starts a local Django server after URLs/templates are added.

## 5. Settings Configuration

Modify `femdes_site/settings.py`.

Required settings:

```python
from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-before-deploy")
DEBUG = os.getenv("DJANGO_DEBUG", "False") == "True"
ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if host.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "store",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "store.context_processors.cart_summary",
                "store.context_processors.site_settings",
            ],
        },
    }
]

DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=600,
    )
}

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

Modify `femdes_site/urls.py`:

```python
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("store.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

## 6. Data Model

Implement models in `store/models.py`.

### 6.1 SiteSettings

Purpose: one-row store settings shown across nav/footer and used for currency.

Fields:

- `store_name`: CharField, default `FemDes`.
- `tagline`: CharField, blank allowed.
- `currency_code`: CharField, default `USD`.
- `currency_symbol`: CharField, default `$`.
- `contact_email`: EmailField, blank allowed.
- `contact_phone`: CharField, blank allowed.
- `address`: TextField, blank allowed.
- `instagram_url`, `facebook_url`, `youtube_url`, `pinterest_url`: URLField, blank allowed.
- `free_shipping_text`: CharField, default `Free shipping on selected orders`.
- `updated_at`: DateTimeField auto_now.

Admin behavior:

- Prevent creating more than one row by overriding `has_add_permission`.
- Show store name, currency, email, and updated date.

### 6.2 Category

Purpose: product grouping and category navigation.

Fields:

- `name`: CharField unique.
- `slug`: SlugField unique.
- `description`: TextField blank.
- `image`: ImageField upload_to `categories/`, blank/null.
- `is_active`: BooleanField default true.
- `sort_order`: PositiveIntegerField default 0.
- `created_at`, `updated_at`.

Ordering:

- `sort_order`, then `name`.

### 6.3 Product

Purpose: main catalog entity.

Fields:

- `name`: CharField.
- `slug`: SlugField unique.
- `sku`: CharField unique, blank allowed.
- `category`: ForeignKey Category, related_name `products`, on_delete PROTECT.
- `short_description`: CharField max_length 280, blank allowed.
- `description`: TextField blank.
- `price`: DecimalField max_digits 10, decimal_places 2.
- `compare_at_price`: DecimalField max_digits 10, decimal_places 2, blank/null. Use this for crossed-out original price.
- `stock_quantity`: PositiveIntegerField default 0.
- `low_stock_threshold`: PositiveIntegerField default 3.
- `is_active`: BooleanField default true.
- `is_featured`: BooleanField default false. Used for homepage hero/collection placements if desired.
- `is_new_arrival`: BooleanField default false.
- `is_best_seller`: BooleanField default false.
- `is_recommended`: BooleanField default false.
- `allow_discount`: BooleanField default true.
- `size_options`: CharField blank. Store comma-separated values such as `XS,S,M,L,XL`.
- `color_options`: CharField blank. Store comma-separated values such as `Black,White,Rose`.
- `created_at`, `updated_at`.

Methods:

- `get_absolute_url()`: returns product detail URL.
- `primary_image`: returns first related ProductImage marked primary or first image.
- `active_discounts(now=None)`: returns applicable active discounts from product, category, and global scopes.
- `effective_price(now=None)`: returns discounted price as Decimal, never below `0.00`.
- `discount_label(now=None)`: returns user-facing label such as `20% off` or `$10 off`.
- `is_in_stock`: true when `stock_quantity > 0`.

Validation:

- `price >= 0`.
- `compare_at_price` is empty or greater than/equal to `price`.
- `stock_quantity >= 0`.

### 6.4 ProductImage

Purpose: multiple product images editable in admin.

Fields:

- `product`: ForeignKey Product, related_name `images`, on_delete CASCADE.
- `image`: ImageField upload_to `products/`.
- `alt_text`: CharField blank.
- `is_primary`: BooleanField default false.
- `sort_order`: PositiveIntegerField default 0.
- `created_at`.

Rules:

- At most one primary image per product. Enforce in model `save()` by clearing other primary images for that product when one image is saved with `is_primary=True`.
- Order by `sort_order`, then `id`.

### 6.5 Discount

Purpose: admin-managed offers.

Fields:

- `name`: CharField.
- `discount_type`: CharField choices `PERCENT` and `FIXED`.
- `value`: DecimalField max_digits 10, decimal_places 2.
- `scope`: CharField choices `GLOBAL`, `CATEGORY`, and `PRODUCT`.
- `product`: ForeignKey Product blank/null, on_delete CASCADE.
- `category`: ForeignKey Category blank/null, on_delete CASCADE.
- `starts_at`: DateTimeField blank/null.
- `ends_at`: DateTimeField blank/null.
- `is_active`: BooleanField default true.
- `priority`: PositiveIntegerField default 0.
- `created_at`, `updated_at`.

Validation:

- Percent discount must be greater than 0 and less than or equal to 100.
- Fixed discount must be greater than 0.
- Product scope requires `product`.
- Category scope requires `category`.
- Global scope requires both `product` and `category` empty.
- `ends_at` must be later than `starts_at` when both are present.

Pricing rule:

- Compute all applicable active discounts.
- Apply the single best discount that gives the lowest final price.
- Do not stack discounts in MVP.

### 6.6 NewsletterSubscriber

Purpose: capture newsletter signups from the homepage.

Fields:

- `email`: EmailField unique.
- `is_active`: BooleanField default true.
- `created_at`.

### 6.7 Order

Purpose: checkout record for manual fulfillment.

Fields:

- `order_number`: CharField unique.
- `status`: choices `NEW`, `CONFIRMED`, `PACKED`, `SHIPPED`, `DELIVERED`, `CANCELLED`, default `NEW`.
- `customer_name`: CharField.
- `customer_email`: EmailField.
- `customer_phone`: CharField.
- `shipping_address`: TextField.
- `notes`: TextField blank.
- `subtotal`: DecimalField.
- `discount_total`: DecimalField default 0.
- `shipping_total`: DecimalField default 0.
- `grand_total`: DecimalField.
- `created_at`, `updated_at`.

Rules:

- Generate `order_number` in the format `FD-YYYYMMDD-XXXXXX`.
- Store totals as snapshots. Do not recompute historical orders from current product prices.

### 6.8 OrderItem

Purpose: line item snapshots.

Fields:

- `order`: ForeignKey Order, related_name `items`, on_delete CASCADE.
- `product`: ForeignKey Product, null=True, blank=True, on_delete SET_NULL.
- `product_name`: CharField.
- `sku`: CharField blank.
- `quantity`: PositiveIntegerField.
- `unit_price`: DecimalField.
- `discount_amount`: DecimalField default 0.
- `line_total`: DecimalField.
- `selected_size`: CharField blank.
- `selected_color`: CharField blank.

Rules:

- Preserve product name, SKU, unit price, discount, and selected options even if the product is later edited.

## 7. Admin Panel

Use Django admin as the required admin panel.

Admin URL:

- `/admin/`

Initial admin setup command:

```bash
python manage.py createsuperuser
```

Admin registrations in `store/admin.py`:

- `SiteSettingsAdmin`
- `CategoryAdmin`
- `ProductAdmin` with inline `ProductImageInline`
- `DiscountAdmin`
- `NewsletterSubscriberAdmin`
- `OrderAdmin` with inline `OrderItemInline`

Product admin requirements:

- `list_display`: `name`, `sku`, `category`, `price`, `effective_price_display`, `stock_quantity`, `is_active`, `is_new_arrival`, `is_best_seller`, `updated_at`.
- `list_filter`: `is_active`, `category`, `is_new_arrival`, `is_best_seller`, `is_recommended`, `allow_discount`.
- `search_fields`: `name`, `sku`, `short_description`.
- `prepopulated_fields`: `{"slug": ("name",)}`.
- `readonly_fields`: `created_at`, `updated_at`.
- `fieldsets`: group catalog fields, pricing fields, inventory fields, homepage flags, variants, and timestamps.
- Inline images: at least one image can be uploaded; primary image flag visible.

Discount admin requirements:

- Filter by active status, discount type, scope.
- Search by name.
- Show scope target and date range.
- Validate impossible scope combinations through model clean.

Order admin requirements:

- Staff can inspect and update `status`.
- Order totals and item snapshots are read-only.
- Search by order number, customer email, customer phone, customer name.
- Filter by status and created date.

Security rules:

- Only staff/superusers can access admin.
- Do not create custom public admin endpoints.
- Do not store payment card numbers.

## 8. Storefront Templates

Use server-rendered Django templates.

### 8.1 `templates/base.html`

Responsibilities:

- Load `{% load static %}`.
- Render HTML head.
- Include Bootstrap CSS CDN exactly as current template unless a later task localizes it.
- Include `static/store/css/vendor.css`.
- Include Swiper CSS from current CDN or local `static/store/css/swiper-bundle.min.css`.
- Include `static/store/style.css`.
- Include Google font links currently used by Kaira.
- Include `{% include "store/partials/icons.html" %}` immediately inside body.
- Include search popup partial.
- Include cart offcanvas partial.
- Include navbar partial.
- Render `{% block content %}`.
- Include footer partial.
- Include current JS in the same order:
  - `static/store/js/jquery.min.js`
  - `static/store/js/plugins.js`
  - `static/store/js/SmoothScroll.js`
  - Bootstrap bundle CDN
  - Swiper bundle CDN or local static file
  - `static/store/js/script.min.js`

### 8.2 `templates/store/home.html`

Convert current homepage sections:

- Hero/billboard carousel: use featured products first. Fallback to newest active products.
- Features: keep static text for appointment, pickup, packaging, returns, but replace wording with FemDes store copy.
- Categories: render first three active categories with images.
- New arrivals: render products where `is_new_arrival=True`.
- Collection feature: render one featured product or site-level promotion.
- Best sellers: render products where `is_best_seller=True`.
- Video: keep or remove based on owner preference. MVP can keep static Kaira video block but should replace link with `#` if no real video exists.
- Testimonials: keep static text until admin-managed testimonials are requested.
- Related products: render products where `is_recommended=True`.
- Blog preview: remove from homepage unless the store owner has blog content. If kept, mark as static store journal cards, not fake dates.
- Newsletter: POST to newsletter subscribe view.
- Instagram: keep static image grid and update link from SiteSettings.

### 8.3 `templates/store/partials/product_card.html`

Render a reusable product card using existing Kaira classes:

```html
<div class="product-item image-zoom-effect link-effect">
  <div class="image-holder position-relative">
    <a href="{{ product.get_absolute_url }}">
      {% if product.primary_image %}
        <img src="{{ product.primary_image.image.url }}" alt="{{ product.primary_image.alt_text|default:product.name }}" class="product-image img-fluid">
      {% else %}
        <img src="{% static 'store/images/product-item-1.jpg' %}" alt="{{ product.name }}" class="product-image img-fluid">
      {% endif %}
    </a>
    <form method="post" action="{% url 'store:add_to_cart' product.id %}">
      {% csrf_token %}
      <input type="hidden" name="quantity" value="1">
      <button type="submit" class="text-decoration-none border-0 bg-transparent p-0" data-after="Add to cart">
        <span>{{ site_settings.currency_symbol }}{{ product.effective_price }}</span>
      </button>
    </form>
    <div class="product-content">
      <h5 class="element-title text-uppercase fs-5 mt-3">
        <a href="{{ product.get_absolute_url }}">{{ product.name }}</a>
      </h5>
    </div>
  </div>
</div>
```

The worker may adjust this snippet to preserve the hover effect exactly, but the final markup must support CSRF-protected POST add-to-cart behavior.

### 8.4 `templates/store/product_list.html`

Required behavior:

- Display active products only.
- Support `?q=`, `?category=`, `?sort=price_asc`, `?sort=price_desc`, `?sort=newest`.
- Sidebar or top filters can use existing `.product-filter` CSS from `style.css`.
- Empty state: show a concise message and link back to `/shop/`.

### 8.5 `templates/store/product_detail.html`

Required behavior:

- Show product images using existing single-product CSS classes.
- Show product name, price, compare-at price when available, discount label, stock status, short description, full description.
- Show size/color selectors only when options exist.
- Add-to-cart form posts product id, quantity, size, and color.
- Disable add-to-cart when out of stock or inactive.
- Show recommended products below.

### 8.6 Cart and Checkout Templates

`cart.html`:

- List each cart item.
- Show image, name, selected size/color, unit price, quantity control, line total.
- Quantity changes POST to cart update view.
- Remove button POSTs to cart remove view.
- Show subtotal, discount total, and grand total.

`cart_offcanvas.html`:

- Replace current hard-coded grocery sample rows.
- Use `cart_summary` context processor.
- If empty, show `Your cart is empty`.
- Include link to `/cart/` and `/checkout/`.

`checkout.html`:

- Form fields: name, email, phone, shipping address, notes.
- Show order summary.
- Do not show payment fields.
- POST creates order and clears cart.

`order_success.html`:

- Show order number, customer email, total, and a short fulfillment message.

## 9. Views, Selectors, and Services

Keep business logic out of templates.

### 9.1 `store/selectors.py`

Create query helpers:

- `active_categories()`
- `active_products()`
- `homepage_products()`
- `filter_products(query, category_slug, sort)`
- `get_product_by_slug(slug)`
- `recommended_products(exclude_product=None, limit=8)`

### 9.2 `store/services.py`

Create business logic helpers:

- `get_cart(request)`: returns session cart dict.
- `save_cart(request, cart)`: marks session modified.
- `add_to_cart(request, product, quantity, selected_size="", selected_color="")`.
- `update_cart_item(request, cart_key, quantity)`.
- `remove_cart_item(request, cart_key)`.
- `cart_items(request)`: returns display-ready cart item objects with product, quantity, selected options, unit price, line discount, and line total.
- `cart_totals(request)`: returns subtotal, discount total, and grand total.
- `create_order_from_cart(request, form)`: creates Order and OrderItems in a transaction, decrements stock, clears cart.
- `subscribe_email(email)`: creates or reactivates NewsletterSubscriber.

Cart key format:

```text
<product_id>:<selected_size>:<selected_color>
```

Stock rule:

- Adding to cart cannot exceed current `stock_quantity`.
- Checkout validates stock again inside a database transaction.
- Stock decrements only after an order is created.

### 9.3 `store/forms.py`

Create forms:

- `CheckoutForm`
  - `customer_name`
  - `customer_email`
  - `customer_phone`
  - `shipping_address`
  - `notes`
- `NewsletterForm`
  - `email`
- `AddToCartForm`
  - `quantity`
  - `selected_size`
  - `selected_color`

Form validation:

- Quantity must be integer 1 through 99.
- Email must be valid.
- Phone must be non-empty and at least 7 characters after trimming.
- Shipping address must be non-empty.

### 9.4 `store/views.py`

Create views:

- `home(request)`.
- `product_list(request)`.
- `product_detail(request, slug)`.
- `add_to_cart(request, product_id)`: POST only.
- `cart_detail(request)`.
- `update_cart(request, cart_key)`: POST only.
- `remove_from_cart(request, cart_key)`: POST only.
- `checkout(request)`: GET and POST.
- `order_success(request, order_number)`.
- `newsletter_subscribe(request)`: POST only.

Redirect behavior:

- After add-to-cart, redirect to `HTTP_REFERER` if safe, else `/cart/`.
- After newsletter signup, redirect back to referring page with a success/error message.
- After checkout success, redirect to order success page.

### 9.5 `store/urls.py`

URL patterns:

```python
from django.urls import path
from . import views

app_name = "store"

urlpatterns = [
    path("", views.home, name="home"),
    path("shop/", views.product_list, name="product_list"),
    path("products/<slug:slug>/", views.product_detail, name="product_detail"),
    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/update/<str:cart_key>/", views.update_cart, name="update_cart"),
    path("cart/remove/<str:cart_key>/", views.remove_from_cart, name="remove_from_cart"),
    path("checkout/", views.checkout, name="checkout"),
    path("orders/<str:order_number>/success/", views.order_success, name="order_success"),
    path("newsletter/subscribe/", views.newsletter_subscribe, name="newsletter_subscribe"),
]
```

## 10. Migration From Static Template

Perform migration in this order:

1. Create a safety copy of the original template:

```bash
mkdir -p legacy_static
cp index.html legacy_static/index.html
cp readme.txt legacy_static/readme.txt
```

2. Create static destination:

```bash
mkdir -p static/store
mv css static/store/css
mv js static/store/js
mv images static/store/images
mv style.css static/store/style.css
```

3. Convert image/CSS/JS references:

- `css/vendor.css` becomes `{% static 'store/css/vendor.css' %}`.
- `style.css` becomes `{% static 'store/style.css' %}`.
- `js/script.min.js` becomes `{% static 'store/js/script.min.js' %}`.
- `images/product-item-1.jpg` becomes `{% static 'store/images/product-item-1.jpg' %}` for static decorative images.
- Uploaded product images use `{{ product.primary_image.image.url }}`.

4. Split `index.html`:

- SVG sprite lines near the top into `templates/store/partials/icons.html`.
- Search popup into `templates/store/partials/search_popup.html`.
- Cart offcanvas into `templates/store/partials/cart_offcanvas.html`.
- Navbar into `templates/store/partials/navbar.html`.
- Footer into `templates/store/partials/footer.html`.
- Main homepage sections into `templates/store/home.html`.
- Shared product card into `templates/store/partials/product_card.html`.

5. Preserve Kaira CSS class names unless a class conflicts with Django form behavior.

6. Replace fake `index.html` links:

- Home: `{% url 'store:home' %}`.
- Shop: `{% url 'store:product_list' %}`.
- Product links: `{{ product.get_absolute_url }}`.
- Cart: `{% url 'store:cart_detail' %}`.
- Checkout: `{% url 'store:checkout' %}`.
- Newsletter: `{% url 'store:newsletter_subscribe' %}`.

## 11. Seed Data

Create `store/management/commands/seed_demo_store.py`.

Purpose:

- Create initial FemDes site settings.
- Create categories based on existing template/product groups: Dresses, Shirts, Jackets, Sweaters, Accessories.
- Create demo products using existing template names and prices from `index.html`.
- Copy existing static product images into `media/products/demo/` for local demo use so seeded ProductImage rows use normal uploaded-media URLs.

Initial product seeds:

- `Dark florish onepiece`, price `95.00`, category `Dresses`, image `product-item-1.jpg`, new arrival true.
- `Baggy Shirt`, price `55.00`, category `Shirts`, image `product-item-2.jpg`, new arrival true.
- `Cotton off-white shirt`, price `65.00`, category `Shirts`, image `product-item-3.jpg`, new arrival true.
- `Crop sweater`, price `50.00`, category `Sweaters`, image `product-item-4.jpg`, best seller true.
- `Handmade crop sweater`, price `50.00`, category `Sweaters`, image `product-item-6.jpg`, recommended true.

Command:

```bash
python manage.py seed_demo_store
```

Expected output:

```text
Created or updated FemDes demo store data.
```

The seed command must be idempotent. Running it multiple times must not duplicate categories, products, or site settings.

## 12. Implementation Tasks

### Task 1: Baseline and Safety

**Files:**

- Create: `.gitignore`
- Create: `.env.example`
- Modify: none

Steps:

- [ ] Confirm current directory with `pwd`.
- [ ] Confirm no Git metadata with `test ! -d .git && echo "no git repo"`.
- [ ] Create `.gitignore` exactly as specified in Section 4.
- [ ] Create `.env.example` exactly as specified in Section 4.
- [ ] Create `legacy_static/` and copy `index.html` plus `readme.txt`.
- [ ] Run `diff -q index.html legacy_static/index.html` and verify no differences.

### Task 2: Django Project Scaffold

**Files:**

- Create: `requirements.txt`
- Create: `manage.py`
- Create: `femdes_site/*`
- Create: `store/*`

Steps:

- [ ] Create virtual environment and install requirements.
- [ ] Run `django-admin startproject femdes_site .`.
- [ ] Run `python manage.py startapp store`.
- [ ] Add `store` to `INSTALLED_APPS`.
- [ ] Configure settings as described in Section 5.
- [ ] Configure root URLs as described in Section 5.
- [ ] Run `python manage.py check`.

Expected result:

```text
System check identified no issues
```

### Task 3: Static Asset Migration

**Files:**

- Move: `css/` to `static/store/css/`
- Move: `js/` to `static/store/js/`
- Move: `images/` to `static/store/images/`
- Move: `style.css` to `static/store/style.css`

Steps:

- [ ] Create `static/store/`.
- [ ] Move template asset folders and stylesheet.
- [ ] Verify these files exist:
  - `static/store/style.css`
  - `static/store/css/vendor.css`
  - `static/store/js/script.min.js`
  - `static/store/images/main-logo.png`
  - `static/store/images/product-item-1.jpg`
- [ ] Run `python manage.py collectstatic --noinput`.

Expected result:

- `staticfiles/` is created.
- No missing static file errors during collection.

### Task 4: Models and Migrations

**Files:**

- Modify: `store/models.py`
- Create: `store/migrations/0001_initial.py` through `makemigrations`
- Test: `store/tests/test_models.py`
- Test: `store/tests/test_discounts.py`

Steps:

- [ ] Implement all models from Section 6.
- [ ] Implement validation in model `clean()` methods.
- [ ] Implement `Product.effective_price()`.
- [ ] Implement `Product.primary_image`.
- [ ] Implement ProductImage primary-image enforcement.
- [ ] Write model tests:
  - Product cannot have negative price.
  - Percent discount above 100 fails validation.
  - Product-scoped discount requires product.
  - Category-scoped discount requires category.
  - Global discount requires no product/category.
  - Best active discount wins.
  - Effective price never goes below zero.
  - Only one primary image remains for a product.
- [ ] Run `python manage.py makemigrations`.
- [ ] Run `python manage.py migrate`.
- [ ] Run `python manage.py test store.tests.test_models store.tests.test_discounts`.

### Task 5: Admin Panel

**Files:**

- Modify: `store/admin.py`
- Test: `store/tests/test_admin.py`

Steps:

- [ ] Register all models.
- [ ] Add ProductImage inline to Product admin.
- [ ] Add list displays, filters, search fields, prepopulated slug fields, and readonly fields from Section 7.
- [ ] Make order item inlines read-only.
- [ ] Make order totals read-only.
- [ ] Restrict SiteSettings to one row.
- [ ] Write admin tests:
  - Anonymous user is redirected from `/admin/`.
  - Superuser can access product changelist.
  - Product admin page contains price, stock, active flag, and image inline.
- [ ] Run `python manage.py test store.tests.test_admin`.

### Task 6: Selectors, Forms, and Services

**Files:**

- Create/modify: `store/selectors.py`
- Create/modify: `store/forms.py`
- Create/modify: `store/services.py`
- Test: `store/tests/test_cart.py`

Steps:

- [ ] Implement query selectors from Section 9.1.
- [ ] Implement forms from Section 9.3.
- [ ] Implement cart session helpers from Section 9.2.
- [ ] Implement order creation in a transaction.
- [ ] Implement stock validation at add-to-cart and checkout.
- [ ] Write cart/service tests:
  - Add active in-stock product to cart.
  - Cannot add inactive product.
  - Cannot add quantity greater than stock.
  - Updating quantity changes cart total.
  - Removing item clears it from cart.
  - Checkout creates order and order items.
  - Checkout decrements stock.
  - Checkout clears session cart.
- [ ] Run `python manage.py test store.tests.test_cart`.

### Task 7: Template Conversion

**Files:**

- Create: `templates/base.html`
- Create: `templates/store/home.html`
- Create: all partials listed in Section 3
- Modify: none outside templates

Steps:

- [ ] Copy the SVG symbol block from `legacy_static/index.html` into `templates/store/partials/icons.html`.
- [ ] Create `base.html` with Kaira head/script order and `{% static %}` paths.
- [ ] Move search popup markup into `search_popup.html`.
- [ ] Move navbar into `navbar.html` and replace static links with Django URLs.
- [ ] Move cart offcanvas into `cart_offcanvas.html` and connect it to `cart_summary`.
- [ ] Move footer into `footer.html` and connect contact/social values to `site_settings`.
- [ ] Create reusable `product_card.html`.
- [ ] Create `home.html` and render database products/categories.
- [ ] Ensure all forms include `{% csrf_token %}`.
- [ ] Run server and visually compare homepage layout to the original static page.

Manual verification:

- Homepage loads without missing CSS.
- Product cards keep image zoom and price hover effect.
- Swiper carousels still initialize.
- Search popup still opens and closes.
- Cart offcanvas opens.

### Task 8: Storefront Views and URLs

**Files:**

- Modify: `store/views.py`
- Modify: `store/urls.py`
- Test: `store/tests/test_storefront.py`

Steps:

- [ ] Implement views from Section 9.4.
- [ ] Implement URL patterns from Section 9.5.
- [ ] Create product listing template.
- [ ] Create product detail template.
- [ ] Create cart template.
- [ ] Create checkout template.
- [ ] Create order success template.
- [ ] Write storefront tests:
  - `/` returns 200.
  - `/shop/` returns active products.
  - inactive products are hidden.
  - `/shop/?q=shirt` filters products.
  - `/shop/?category=<slug>` filters products.
  - product detail returns 200 for active product.
  - product detail returns 404 for inactive product.
  - add-to-cart requires POST.
  - newsletter signup creates subscriber.
- [ ] Run `python manage.py test store.tests.test_storefront`.

### Task 9: Seed Command

**Files:**

- Create: `store/management/commands/seed_demo_store.py`
- Test: add seed command coverage to `store/tests/test_models.py` or a new `test_seed.py`

Steps:

- [ ] Implement idempotent demo seed command from Section 11.
- [ ] Ensure the command creates SiteSettings if absent.
- [ ] Ensure categories are created with stable slugs.
- [ ] Ensure products are created with stable slugs/SKUs.
- [ ] Ensure product images are assigned.
- [ ] Run `python manage.py seed_demo_store`.
- [ ] Run it again and verify object counts do not increase.

### Task 10: Full Verification

Commands:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py collectstatic --noinput
python manage.py runserver
```

Manual browser verification:

- Visit `http://127.0.0.1:8000/`.
- Visit `http://127.0.0.1:8000/shop/`.
- Visit one product detail page.
- Add a product to cart.
- Open cart offcanvas.
- Update cart quantity on `/cart/`.
- Complete checkout.
- Confirm order appears in `/admin/store/order/`.
- Edit a product price in admin.
- Confirm storefront reflects the new price.
- Add an active discount in admin.
- Confirm storefront reflects the discounted price.
- Mark product inactive.
- Confirm product disappears from `/shop/`.

## 13. Deployment Plan

For local development:

```bash
source .venv/bin/activate
cp .env.example .env
python manage.py migrate
python manage.py seed_demo_store
python manage.py createsuperuser
python manage.py runserver
```

For production:

- Set `DJANGO_DEBUG=False`.
- Set a strong `DJANGO_SECRET_KEY`.
- Set `DJANGO_ALLOWED_HOSTS` to the production domain.
- Use PostgreSQL with `DATABASE_URL`.
- Run `python manage.py migrate`.
- Run `python manage.py collectstatic --noinput`.
- Serve with Gunicorn or a platform-provided WSGI runner.
- Persist `MEDIA_ROOT` on durable storage. Product uploads must not disappear between deployments.
- Configure HTTPS.
- Restrict admin accounts to trusted staff.
- Back up database and media files regularly.

Production environment variables:

```text
DJANGO_SECRET_KEY=<strong-secret>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=femdes.example.com,www.femdes.example.com
DATABASE_URL=postgresql://user:password@host:5432/femdes
DJANGO_CSRF_TRUSTED_ORIGINS=https://femdes.example.com,https://www.femdes.example.com
```

## 14. Security and Data Integrity Requirements

- Use POST for cart mutations, checkout, newsletter signup, and admin edits.
- Keep CSRF protection enabled.
- Never expose admin forms publicly.
- Validate uploaded images through Django/Pillow.
- Limit uploaded image size in form/model validation to 5 MB.
- Do not store raw payment details.
- Use Decimal for all monetary calculations.
- Store order item price snapshots.
- Revalidate stock at checkout inside `transaction.atomic()`.
- Do not allow inactive products to be added to cart.
- Do not delete products that exist in historical orders. Mark them inactive instead.
- Keep `readme.txt` license terms available in `legacy_static/` and preserve attribution unless the owner has paid for no-attribution rights.

## 15. Acceptance Criteria

The implementation is complete when:

- `python manage.py check` passes.
- `python manage.py test` passes.
- `python manage.py makemigrations --check --dry-run` reports no model changes.
- `python manage.py collectstatic --noinput` passes.
- Homepage uses database products/categories instead of hard-coded product cards.
- Admin can add a product with images.
- Admin can edit product price and stock.
- Admin can deactivate a product and remove it from the public storefront.
- Admin can create a discount and public product prices reflect it.
- Customers can add products to cart.
- Customers can update/remove cart items.
- Customers can submit checkout and create an order.
- Orders appear in admin with line-item snapshots.
- Newsletter form creates subscribers.
- Existing Kaira styling, product-card hover behavior, navbar, footer, and carousel presentation remain visually recognizable.

## 16. Suggested Commit/Checkpoint Sequence

If Git is initialized later, use these commits:

```bash
git add .gitignore .env.example requirements.txt femdes_site store manage.py
git commit -m "chore: scaffold Django webstore"

git add static legacy_static templates
git commit -m "feat: convert Kaira template to Django templates"

git add store/models.py store/admin.py store/migrations
git commit -m "feat: add catalog discount and order models"

git add store/forms.py store/services.py store/selectors.py store/views.py store/urls.py
git commit -m "feat: add storefront cart and checkout flow"

git add store/management store/tests
git commit -m "test: cover webstore catalog cart admin and checkout"
```

Because the current directory has no Git repository, do not rely on Git as the only rollback mechanism until the owner intentionally initializes it.

## 17. References Used For Framework Assumptions

- Django 5.2 documentation via Context7 for project setup, migrations, templates, admin URLs, static/media file serving, `ImageField`, and testable Django app structure.
- Existing local Kaira template files in this repository for visual structure, CSS classes, JS initialization behavior, and asset paths.
