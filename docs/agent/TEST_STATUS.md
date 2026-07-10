# Test Status

## Current State

Django 5.2.15 project scaffolded, assets migrated, 8 models with migrations, and Django admin configured for all 8 store models. T0 through T17 (with all FIX subtasks) complete. 264 tests pass. All MVP features verified.

Django commands now available:

```bash
conda run -n femdes python manage.py check     # PASS (0 issues)
conda run -n femdes python manage.py test       # PASS (264 tests)
```

## T10/T10-FIX Verification (2026-07-09)

10 storage tests verify local and S3 media modes:

```bash
conda run -n femdes python manage.py test store.tests.test_settings -v 2  # 10 tests, OK
conda run -n femdes python manage.py test                                  # T10 suite OK
DJANGO_MEDIA_STORAGE=s3 AWS_STORAGE_BUCKET_NAME=tb AWS_ACCESS_KEY_ID=k AWS_SECRET_ACCESS_KEY=s conda run -n femdes python manage.py check  # OK
```

Coverage: local FileSystemStorage default, MEDIA_URL="/media/", S3Storage backend, region/endpoint/custom-domain in options, static storage unchanged, missing bucket raises ValueError.

## T9/T9-FIX Verification (2026-07-07)

Blouse catalog and customization flow complete. All historical review findings resolved:

- **T7 image storage (RESOLVED by T7-FIX):** `ProductImage.image.name` uses deterministic `products/demo/<filename>` paths. File-system idempotency tests pass.
- **T9 seed cleanup (RESOLVED by T9-FIX):** Per-prefix `Q()` objects deactivate old SKUs; admin products preserved.
- **T9 customization redirect (RESOLVED by T9-FIX):** POST returns 302 → `/customizations/<uuid>/created/`.
- **T9 measurement validators (RESOLVED by T9-FIX):** `MinValueValidator(Decimal("0.01"))` on all 6 fields.
- **T9 product gallery (RESOLVED by T9-FIX):** Scrollable `.product-gallery-scroll` container.

```bash
conda run -n femdes python manage.py test  # 183 tests, OK
conda run -n femdes python manage.py check  # 0 issues
```

## T5 Verification (2026-07-06)

T5 and T5-FIX are complete. Storefront forms, selectors, services, URLs, views,
and temporary templates are in place. T5-FIX adds aggregate stock validation
across variant cart lines and redirects empty-cart checkout POST requests back
to the cart.

```bash
conda run -n femdes python manage.py test store.tests.test_cart store.tests.test_storefront -v 2  # 44 tests, OK
conda run -n femdes python manage.py test                                                         # 135 tests, OK
conda run -n femdes python manage.py check                                                        # 0 issues
conda run -n femdes python manage.py makemigrations --check --dry-run                             # No changes detected
```

## T4 Verification (2026-07-06)

All 25 admin tests pass after T4-FIX. `ProductImage` and `OrderItem` are both
registered directly with `admin.site` and remain available as inlines under
Product and Order.

```bash
conda run -n femdes python manage.py test store.tests.test_admin -v 2  # 25 tests, OK
conda run -n femdes python manage.py test                              # 91 tests, OK
conda run -n femdes python manage.py check                             # 0 issues
conda run -n femdes python manage.py makemigrations --check --dry-run  # No changes detected
```

## T3 Verification (2026-07-06)

All 66 model and discount tests pass after T3-FIX. 8 models implemented with initial migrations.

```bash
conda run -n femdes python manage.py makemigrations --check --dry-run  # No changes detected
conda run -n femdes python manage.py migrate                           # OK
conda run -n femdes python manage.py test                              # 66 tests, OK
conda run -n femdes python manage.py check                             # 0 issues
```

Models: SiteSettings (one-row), Category, Product (with get_effective_price), ProductImage (one-primary), Discount (scope validation, apply_to_price), NewsletterSubscriber, Order (auto order_number), OrderItem.

## T2 Verification (2026-07-06)

All checks passed. One settings adjustment needed: removed `CompressedManifestStaticFilesStorage` because `vendor.css` references `../images/colorbox/loading.gif` which doesn't exist in the Kaira image set. Default `StaticFilesStorage` used; Whitenoise middleware still serves files at runtime.

```bash
# Pre-move checks
test -f legacy_static/index.html                     # PASS
diff -q index.html legacy_static/index.html          # PASS
test -f style.css && test -f css/vendor.css          # PASS
test -f js/script.min.js                             # PASS
test -f images/main-logo.png                         # PASS
test -f images/product-item-1.jpg                    # PASS

# Move
mv style.css static/store/style.css
mv css static/store/css
mv js static/store/js
mv images static/store/images

# Post-move checks
test -f static/store/style.css                       # PASS
test -f static/store/css/vendor.css                  # PASS
test -f static/store/js/script.min.js                # PASS
test -f static/store/images/main-logo.png            # PASS
test -f static/store/images/product-item-1.jpg       # PASS
test ! -e style.css                                  # PASS (old paths gone)
test ! -e css                                        # PASS
test ! -e js                                         # PASS
test ! -e images                                     # PASS
test ! -d static/store/css/css                       # PASS (no nested dupes)
diff -q index.html legacy_static/index.html          # PASS (legacy intact)

# Django
conda run -n femdes python manage.py collectstatic --noinput  # PASS (208 unmodified)
conda run -n femdes python manage.py check                    # PASS (0 issues)
```

## TASK-001-FIX Verification (2026-07-06)

**Problem found during review:** `store/tests.py` (Django default) conflicted with `store/tests/` package, causing:
```
ImportError: 'tests' module incorrectly imported from .../store/tests
```

**Fix:** Removed `store/tests.py`. All checks pass:

```bash
test ! -f store/tests.py                              # PASS
test -f store/tests/__init__.py                       # PASS
conda run -n femdes python manage.py check            # PASS: no issues
conda run -n femdes python manage.py test -v 2        # PASS: Ran 0 tests, Found 0 test(s)
```

## T1 Verification (2026-07-06)

All checks passed:

```bash
conda run -n femdes python -m pip show Django    # Django 5.2.15
conda run -n femdes python manage.py check        # System check identified no issues (0 silenced)
test -f requirements.txt                          # PASS
test -f manage.py                                 # PASS
test -f femdes_site/settings.py                   # PASS
test -f femdes_site/urls.py                       # PASS
test -f store/apps.py                             # PASS
test -f store/tests/__init__.py                   # PASS
test -d css                                       # PASS (original assets untouched)
test -d js                                        # PASS
test -d images                                    # PASS
test -f style.css                                 # PASS
test ! -d static/store                            # PASS (assets not moved yet)
```

Created/modified files:
- `requirements.txt` — Django 5.2, Pillow, dj-database-url, python-dotenv, whitenoise, psycopg[binary]
- `manage.py` — Django management script
- `femdes_site/__init__.py`, `settings.py`, `urls.py`, `asgi.py`, `wsgi.py` — project package
- `store/__init__.py`, `apps.py`, `models.py`, `views.py`, `admin.py` — app package
- `store/tests/__init__.py` — test package
- `static/`, `templates/` — empty directories for future tasks

Settings configured:
- `python-dotenv` loads `.env` from `BASE_DIR`
- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` from environment
- `store` in `INSTALLED_APPS`
- `WhiteNoiseMiddleware` after `SecurityMiddleware`
- `DATABASES` via `dj_database_url.config()` defaulting to SQLite
- `STATIC_URL`, `STATIC_ROOT`, `STATICFILES_DIRS`, `MEDIA_URL`, `MEDIA_ROOT`
- `DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"`

## T0 Verification (2026-07-06)

All checks passed:

```bash
test ! -d .git && echo "no git repo"           # PASS
test -f legacy_static/index.html                # PASS
test -f legacy_static/readme.txt                # PASS
diff -q index.html legacy_static/index.html     # PASS
diff -q readme.txt legacy_static/readme.txt     # PASS
test -f .gitignore                              # PASS
test -f .env.example                            # PASS
```

## Planning-Pass Verification

Performed during documentation setup:

```bash
find . -maxdepth 5 -type f | sort
find . -maxdepth 4 -type f \( -iname 'readme*' -o -name 'package.json' -o -name 'pyproject.toml' -o -name 'requirements*.txt' -o -name 'setup.py' -o -name 'vite.config.*' -o -name 'next.config.*' -o -name 'webpack.config.*' -o -name 'gulpfile.*' -o -name 'composer.json' -o -name 'Gemfile' -o -name 'Makefile' -o -name 'AGENTS.md' -o -name 'CLAUDE.md' \) -print | sort
wc -l index.html style.css css/*.css js/*.js readme.txt implementation_plan.md AGENTS.md CLAUDE.md
rg -n "<section|<nav|<footer|offcanvas|search-popup|product-carousel|new-arrival|best-sellers|related-products|newsletter|instagram|Cart|Wishlist|price|data-after|script src" index.html
rg -n "Theme Name|font|--bs-|preloader|search-popup|swiper|image-zoom|product-item|single product|product-filter|btn-link|@media|dark theme" style.css
```

Observed:

- `AGENTS.md` and `CLAUDE.md` existed but were empty before this pass.
- No `package.json`, `pyproject.toml`, `requirements.txt`, `Makefile`, or test files existed.
- No `.git/` directory exists.

## Required Future Test Commands

After T2:

```bash
test -f static/store/style.css
test -f static/store/css/vendor.css
test -f static/store/js/script.min.js
test -f static/store/images/main-logo.png
test -f static/store/images/product-item-1.jpg
test ! -e style.css
test ! -e css
test ! -e js
test ! -e images
conda run -n femdes python manage.py collectstatic --noinput
conda run -n femdes python manage.py check
```

After T3:

```bash
conda run -n femdes python manage.py makemigrations --check --dry-run
conda run -n femdes python manage.py migrate
conda run -n femdes python manage.py test store.tests.test_models store.tests.test_discounts
```

After T4:

```bash
conda run -n femdes python manage.py test store.tests.test_admin
```

After T5:

```bash
conda run -n femdes python manage.py test store.tests.test_cart store.tests.test_storefront
```

After T6:

```bash
conda run -n femdes python manage.py test store.tests.test_storefront
conda run -n femdes python manage.py collectstatic --noinput
conda run -n femdes python manage.py runserver
```

After T7:

```bash
conda run -n femdes python manage.py seed_demo_store
conda run -n femdes python manage.py seed_demo_store
conda run -n femdes python manage.py test store.tests.test_seed
```

Final MVP verification:

```bash
conda run -n femdes python manage.py check
conda run -n femdes python manage.py makemigrations --check --dry-run
conda run -n femdes python manage.py test
conda run -n femdes python manage.py collectstatic --noinput
conda run -n femdes python manage.py runserver
```

## Manual Verification Required After Implementation

- Homepage renders with Kaira styling.
- `/shop/` lists active products.
- Product detail page renders image, price, stock, and add-to-cart form.
- Admin can add product with image.
- Admin can change product price.
- Admin can create discount.
- Storefront reflects price and discount changes.
- Cart add/update/remove works.
- Checkout creates order and decrements stock.
- Order appears in admin with line-item snapshots.
