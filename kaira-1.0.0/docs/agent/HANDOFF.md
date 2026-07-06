# Handoff

## Summary

This repo is a static Kaira Bootstrap fashion-store template being converted into a database-backed FemDes webstore. T0 (baseline preservation), T1 (Django scaffold), T1-FIX (test discovery), and T2 (asset migration) are complete. T3 (database models) is the next task.

## What Exists Now

- Static source preserved:
  - `legacy_static/index.html` — byte-identical copy
  - `legacy_static/readme.txt` — byte-identical copy
  - `index.html` — original template (unchanged)
  - `readme.txt` — original license (unchanged)
- Django scaffold (T1):
  - `requirements.txt` — Django 5.2.15, Pillow, dj-database-url, python-dotenv, whitenoise, psycopg[binary]
  - `manage.py`
  - `femdes_site/` — project package with env-loaded settings
  - `store/` — app package
  - Conda env: `femdes` (Python 3.12.13)
- Asset migration (T2):
  - `static/store/css/` — vendor CSS + Kaira CSS
  - `static/store/js/` — jQuery, plugins, SmoothScroll, script.min.js
  - `static/store/images/` — all Kaira images
  - `static/store/style.css` — Kaira custom stylesheet
  - `staticfiles/` — collected output (gitignored)
- Agent/planning docs:
  - `AGENTS.md`, `CLAUDE.md`
  - `docs/architecture.md`, `docs/decisions.md`
  - `docs/agent/IMPLEMENTATION_PLAN.md`, `docs/agent/TASK_BOARD.md`, `docs/agent/CURRENT_TASK.md`, `docs/agent/HANDOFF.md`, `docs/agent/TEST_STATUS.md`
  - `.agent/CONTINUITY.md`

## Key Configuration

- **Environment:** `conda run -n femdes python manage.py <cmd>`
- **Settings:** python-dotenv, dj-database-url (SQLite default), WhiteNoise middleware
- **Static storage:** Django default `StaticFilesStorage` (not manifest — `vendor.css` references missing `colorbox/loading.gif`)
- **Installed apps:** `store`

## Verification Status

- `conda run -n femdes python manage.py check` — **PASS**
- `conda run -n femdes python manage.py test` — **PASS** (0 tests)
- `conda run -n femdes python manage.py collectstatic --noinput` — **PASS**

## Next Action

**T3: Add database models and migrations** — implement `store/models.py` with SiteSettings, Category, Product, ProductImage, Discount, NewsletterSubscriber, Order, OrderItem. See `docs/agent/CURRENT_TASK.md`.

## Do Not Do Yet

- Do not create database models (that's T3).
- Do not configure Django admin.
- Do not create storefront views/URLs.
- Do not split `index.html` into templates.
- Do not add payment integration.
- Do not remove upstream attribution.
