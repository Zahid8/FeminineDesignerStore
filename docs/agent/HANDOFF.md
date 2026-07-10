# Handoff

## Summary

This repo has been converted from a static Kaira Bootstrap fashion-store template into a database-backed FemDes blouse webstore. T0 through T19 (including all FIX subtasks) complete. T18-FIX2 Razorpay reliability carryover documented. No required tasks remain.

## Completed Tasks

- **T0**: Baseline preservation — `legacy_static/` copies, `.gitignore`, `.env.example`
- **T1**: Django 5.2.15 scaffold — `femdes_site/`, `store/`, conda env `femdes`
- **T2**: Static asset migration — `css/`, `js/`, `images/`, `style.css` → `static/store/`
- **T3**: 8 database models + migrations + 66 model/discount tests
- **T4**: Django admin configured for all models (ProductImage + OrderItem inlines)
- **T5**: Forms, selectors, services (session cart, checkout with stock revalidation), views, URLs
- **T6**: Kaira HTML converted to Django templates (base.html, 7 partials, 6 page templates)
- **T7**: Idempotent `seed_demo_store` command with deterministic `products/demo/` image storage
- **T8**: Final MVP verification + docs update
- **T9**: Blouse catalog (15 products, 4 images each), 6 measurement defaults, `CustomizationRequest` model, customization form → redirect → shareable UUID link, Buy Now button, scrollable image gallery, disclaimer text
- **T10**: Optional S3-compatible media storage (`django-storages`), local default preserved, supports custom endpoints and CDN domains
- **T11**: Customer accounts (register/login/logout/profile/orders), auth-aware navbar with POST logout, authenticated checkout links orders, guest checkout preserved

## Resolved Historical Issues

- T7 image storage: `ProductImage.image.name` now uses deterministic `products/demo/<filename>` paths (T7-FIX)
- T9 seed cleanup: old non-blouse SKU prefixes properly deactivated using per-prefix `Q()` objects (T9-FIX)
- T9 customization redirect: POST now returns 302 redirect to `/customizations/<uuid>/created/` (T9-FIX)
- T9 measurement validation: `CustomizationRequest` fields use `MinValueValidator(Decimal("0.01"))` (T9-FIX)
- T9 product detail: scrollable `.product-gallery-scroll` container for product images (T9-FIX)

## Key Configuration

- **Environment:** `conda run -n femdes python manage.py <cmd>`
- **Settings:** python-dotenv, dj-database-url (SQLite default), WhiteNoise middleware
- **Static storage:** Django default `StaticFilesStorage`
- **Installed apps:** `store`

## Verification Status

- `conda run -n femdes python manage.py check` — **PASS** (0 issues)
- `conda run -n femdes python manage.py test` — **PASS** (277 tests)
- `conda run -n femdes python manage.py collectstatic --noinput` — **PASS**
- `conda run -n femdes python manage.py makemigrations --check --dry-run` — **PASS** (no changes)
- `conda run -n femdes python manage.py seed_demo_store` — **PASS** (idempotent, 18 records updated on repeat)

## Optional Future Work

Do not start these unless the owner explicitly requests them:

- Payment gateway integration (Stripe/PayPal)
- Wishlist persistence
- Shipping carrier APIs and tax calculation
- Blog CMS
- Instagram API integration
- Custom admin dashboard
