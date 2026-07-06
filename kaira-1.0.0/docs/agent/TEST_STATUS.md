# Test Status

## Current State

Django 5.2.15 project scaffolded and passing checks. T0 and T1 complete. No models, admin, or views exist yet.

Django commands now available:

```bash
conda run -n femdes python manage.py check     # PASS
conda run -n femdes python manage.py test       # no tests defined yet
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
python manage.py makemigrations
python manage.py migrate
python manage.py test store.tests.test_models store.tests.test_discounts
```

After T4:

```bash
python manage.py test store.tests.test_admin
```

After T5:

```bash
python manage.py test store.tests.test_cart store.tests.test_storefront
```

After T6:

```bash
python manage.py test store.tests.test_storefront
python manage.py collectstatic --noinput
python manage.py runserver
```

After T7:

```bash
python manage.py seed_demo_store
python manage.py seed_demo_store
python manage.py test store.tests.test_seed
```

Final MVP verification:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py collectstatic --noinput
python manage.py runserver
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
