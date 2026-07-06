# Test Status

## Current State

No automated test suite exists yet because the repository is currently a static HTML/CSS/JS template. T0 baseline preservation is complete.

No Django project exists yet, so these commands are not currently available:

```bash
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
python manage.py collectstatic --noinput
```

## T0 Verification (2026-07-06)

All checks passed:

```bash
test ! -d .git && echo "no git repo"           # PASS: no git repo
test -f legacy_static/index.html                # PASS
test -f legacy_static/readme.txt                # PASS
diff -q index.html legacy_static/index.html     # PASS: byte-for-byte identical
diff -q readme.txt legacy_static/readme.txt     # PASS: byte-for-byte identical
test -f .gitignore                              # PASS
test -f .env.example                            # PASS
```

Created files:
- `legacy_static/index.html` — byte-identical copy of `index.html`
- `legacy_static/readme.txt` — byte-identical copy of `readme.txt`
- `.gitignore` — excludes `.env`, `.venv/`, `venv/`, `__pycache__/`, `*.pyc`, `db.sqlite3`, `media/`, `staticfiles/`, `.omx/`
- `.env.example` — Django local environment template with `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DATABASE_URL`, `DJANGO_CSRF_TRUSTED_ORIGINS`

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

After T1:

```bash
source .venv/bin/activate
python manage.py check
```

After T3:

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
