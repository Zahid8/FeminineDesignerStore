# Test Status

## Current State

Django 5.2.15 project scaffolded, assets migrated, 8 models with migrations, and Django admin configured for all 8 store models. T0 through T25 complete. 330 tests. PDF deferred. T25-FIX (strengthened search/filter tests) complete. T28/T29 redesign and T30 customer features complete (448 tests). TASK-027-FIX item 5 (dedicated stepper/search/status tests) is still unwritten.

Django commands now available:

```bash
conda run -n femdes python manage.py check     # PASS (0 issues)
conda run -n femdes python manage.py test       # PASS (448 tests)
```

## T34 Verification — Online Orders API (2026-10-17)

```bash
conda run -n femdes python manage.py test   # PASS (472 tests)
# billing app (separate repo): npm run typecheck, npm run lint, npx vitest run — 217 passed
```
End-to-end: billing app production build at :3010 against the demo webstore at
:8766 with `WEBSTORE_API_TOKEN=demo-token-123` — list rendered 6 orders, detail
opened, status→Confirmed and payment→Paid saved; webstore API then reported
`confirmed / paid / paid_at set`. No page errors.

## T33 Verification — Made-to-measure (2026-10-17)

```bash
conda run -n femdes python manage.py test   # PASS (466 tests)
```
`docs/agent/browser-checks/builder.js`: fills the builder, toggles cm,
chooses sleeves, reviews, adds to bag; toast and cart line confirmed on
desktop and mobile with no page errors. Screenshots in
`docs/agent/screenshots/t33/`.

## T32 Verification — Component polish (2026-10-17)

```bash
conda run -n femdes python manage.py test   # PASS (448 tests)
```
One assertion updated (`test_selected_options_reach_cart`: cart renders
colour and size as separate chips). Full-page audit captures of every page at
both widths via `docs/agent/browser-checks/audit.js`; selected
screenshots in `docs/agent/screenshots/t32/`.

## T31 Verification — Concept A + B styling (2026-10-17)

```bash
conda run -n femdes python manage.py test   # PASS (448 tests)
```
`test_redesign.ConceptBMerchandisingTests` (5): −% badge and sale price
class, `percent_off` edge cases, announcement bar from settings (hidden when
blank), promo banner renders as a band not a hero, nav category links and
primary Add to Cart. Screenshots in `docs/agent/screenshots/t31/`.

## T30 Verification — Customer features + phone OTP (2026-10-17)

```bash
conda run -n femdes python manage.py check                          # PASS
conda run -n femdes python manage.py test                           # PASS (443 tests)
conda run -n femdes python manage.py makemigrations --check --dry-run  # No changes detected
conda run -n femdes python manage.py collectstatic --noinput        # OK
```

New test modules: `test_phone_otp` (normalisation, OTP expiry/attempts/
single-use/throttles, account linking, views, proxy IP, Twilio backend,
password reset, SEO), `test_wishlist`, `test_checkout_money` (totals,
shipping threshold, payment routing, emails, settings-driven UPI),
`test_catalog_features` (facets, pagination, product details, size charts,
stock alerts), `test_content_service` (pages, FAQ, diaries, appointments,
order tracking).

Bug found by tests: OTP wrong-attempt counter was rolled back by
`transaction.atomic()` when the error was raised inside the block (unlimited
guessing). Fixed by raising after the block exits.

Browser walkthrough `docs/agent/browser-checks/features.js` against a copy of
the dev DB with sample attributes (`/tmp/fd_demo.sqlite3`, server on :8766;
the real dev DB was not modified): wishlist heart toggles without reload and
updates the header count; filter drawer submits clean URLs and shows chips;
size guide dialog opens; cart shows shipping + free-shipping progress;
checkout lists UPI + COD; FAQ, page, appointment and track-order pages return
200; full OTP sign-in on mobile using the console SMS code; no page errors.
Screenshots in `docs/agent/screenshots/t30/`.

## T29 Verification — Reference-driven redesign (2026-10-17)

```bash
conda run -n femdes python manage.py check                          # PASS (0 issues)
conda run -n femdes python manage.py test                           # PASS (351 tests)
conda run -n femdes python manage.py makemigrations --check --dry-run  # No changes detected
conda run -n femdes python manage.py collectstatic --noinput        # OK
```

New tests: `store/tests/test_redesign.py` (17): HomeBanner rendering/order/
inactive/CTA fallback/theme/admin; product sort whitelist and filter
preservation; colour/size choices parsing, radio rendering inside the cart
form, options reaching the cart; sticky buy bar `form=` wiring;
`secondary_image` + hover image hook; WhatsApp float/PDP button only when
`SiteSettings.whatsapp_url` is set.

Changed tests: the three primary-image tests in `test_storefront` now assert
the card's `<img class="product-image">` `src` (helper `_primary_card_srcs`)
and the hero block, because cards now also render a second hover image.

Browser evidence (`docs/agent/screenshots/after/*.jpg`, 1440 and 390 widths,
no page errors) and `docs/agent/browser-checks/behave.js` (all passed):
steppers, search open/focus/Escape, offcanvas cart, mobile menu, anchor
offset, no-JS reveal state, sort select navigates to `?sort=price_asc`,
density toggle persists in localStorage, mega menu opens on hover, live
search returns 4 cards, sticky buy bar appears after scrolling past the buy
panel. One demo `HomeBanner` was created in the local dev DB for screenshots.

Known gap: TASK-027-FIX item 5 (dedicated stepper/search tests) still
unwritten; T29's `ProductOptionTests.test_sticky_bar_submits_the_cart_form`
and the storefront search tests cover part of it.

## T28 Verification — UI revamp (2026-10-17)

```bash
conda run -n femdes python manage.py check                          # PASS (0 issues)
conda run -n femdes python manage.py test                           # PASS (351 tests)
conda run -n femdes python manage.py makemigrations --check --dry-run  # No changes detected
conda run -n femdes python manage.py collectstatic --noinput        # OK
```

Browser evidence (Playwright Chromium, 1440x900 and 390x844): before/after
full-page screenshots in `docs/agent/screenshots/{before,after}/` for home,
shop, product detail, cart, checkout, login and contact. No JS page errors.
The only console error is a pre-existing 404 for demo media
`/media/products/demo/primary.jpg` (missing file in local `media/`); the new
head-script image fallback swaps it for `femdes-placeholder.svg`.

Reusable scripts: `docs/agent/browser-checks/{shot,behave,vp}.js` (need
`npm i playwright` in a scratch dir and the dev server on 127.0.0.1:8765).

New tests: `test_storefront.FlashMessageToastTests` (3) prove Django messages
render as toasts (none when empty, info toast after empty-cart checkout
redirect, `is-error` toast when add-to-cart exceeds stock).

Scripted interaction checks (all passed): product stepper clamps 1..stock and
recovers blank input to 1; cart stepper reaches 0; desktop search trigger opens
the popup, focuses `q`, Escape closes it and returns focus to the same trigger;
cart offcanvas and mobile menu open; Collections dropdown opens without
navigating; `#customize-section` anchor lands below the sticky header; the
head-script fallback replaced 3 broken demo images with the placeholder; with
JavaScript disabled no reveal element is hidden (`after/nojs_home.png`).

Test changes:
- `test_invoices.TimelineActiveStatusTests.test_each_status_is_active` now
  asserts the `<ol>` stepper semantics (`is-current` + `aria-current="step"` on
  exactly the matching step, all six labels in order) instead of Bootstrap
  badge class strings. It was already failing on the uncommitted T27-FIX
  `<span>`→`<li>` change.
- `test_customization...test_no_images_renders_placeholder` now expects
  `femdes-placeholder.svg` instead of the Kaira `product-item-1.jpg` stock
  photo (a male model, wrong for a blouse store).

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

## T35 — Neumorphic admin theme (2026-10-17)

- `python manage.py check` — no issues
- `python manage.py test` — 474 tests OK (2 new AdminThemeTests)
- `python manage.py makemigrations --check --dry-run` — no changes
- `python manage.py collectstatic --noinput` — OK

## T35-FIX — Made-to-measure ignores stock (2026-10-17)

- `python manage.py check` — no issues
- `python manage.py test` — 482 tests OK (MadeToMeasureStockTests, BuilderPrefillAndTermsTests)
- `node docs/agent/browser-checks/e2e_mtm.js` (DEBUG=False server, port 8770) — 28/28 PASS, no JS errors
- `python manage.py makemigrations --check --dry-run` — no changes

## T36 — Billing-style admin (2026-10-17)

- `python manage.py check` — no issues; `makemigrations --check` — no changes
- `python manage.py test` — 483 tests OK (AdminThemeTests updated + sidebar grouping test)
- `node docs/agent/browser-checks/admin_theme.js` — login, dashboard, change lists, change forms, mobile drawer; no JS errors

## T37 — Delivered stage + order type (2026-10-17)

- `python manage.py test` — 486 tests OK (timeline test updated for Delivered); `makemigrations --check` — no changes
- Billing app: `vitest` 226 OK, `tsc --noEmit` OK, `eslint .` OK
- `node docs/agent/browser-checks/billing_stages.js` against a production build — 18/18 PASS, no JS errors

## T37-FIX — Builder validation (2026-10-17)

- `python manage.py test` — 488 tests OK (BuilderClientValidationTests)
- `node docs/agent/browser-checks/mtm_guard.js` — 24/24 PASS (desktop + mobile)
- `node docs/agent/browser-checks/e2e_mtm.js` (DEBUG=False server) — 28/28 PASS

## T40 — Soft studio UI pass (2026-10-18)

- `python manage.py test` — 495 OK; `check` — no issues; `collectstatic` — OK
- `node docs/agent/browser-checks/overflow.js` — no page scrolls sideways (desktop + mobile)
- `node docs/agent/browser-checks/e2e_mtm.js` — 28/28; `mtm_guard.js` — 24/24 (DEBUG=False server)

## T41 — Customer bill (2026-10-18)

- `python manage.py test` — 499 OK (InvoicePageTests, BillingLinkTests; older invoice tests updated to the new layout)
- `node docs/agent/browser-checks/invoice_check.js` — phone + desktop OK; billing PDF link returns 200 application/pdf

## T42 — Standard address (2026-10-18)

- `python manage.py test` — 504 OK; `makemigrations --check` — 0027 committed
- `browser-checks/e2e_mtm.js` 28/28, `location_e2e.js` 27/27 on the DEBUG=False server (both fill the new fields)

## T44 — Admin handoff (2026-10-18)

- `python manage.py test` — 514 OK (test_sso.py: valid/expired/replayed/tampered/other-user/disabled)
- Billing: vitest 235 OK, tsc OK, eslint OK
- `browser-checks/handoff.js` — 6/6: login required, big button, new tab opens /admin/ signed in as manager, superuser pages open, link single-use

## T46 — Surface polish (2026-10-18)

- `python manage.py test` — 514 OK
- `browser-checks/qa_design.js` (5 widths) — 0 design issues; only demo-DB missing images and a labelled 13px radio remain (scrollers like the category bar now exempt from clip checks)
- `browser-checks/btnwrap.js` — 2 known wraps at 360px ("Add to Bag with These Measurements", full-width button)

## T47 — Product photos (2026-10-18)

- `python manage.py test` — 514 OK
- `browser-checks/gallery_pswp.js` (phone + desktop, DEBUG on and off) — viewer opens from tap and from the expand button, next works, closes, carousel follows; no JS errors
- `browser-checks/qa_design.js` — unchanged baseline (demo-DB missing images, labelled 13px radio)
