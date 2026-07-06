# Handoff

## Summary

This repo is a static Kaira Bootstrap fashion-store template being converted into a database-backed FemDes webstore. T0 (baseline preservation), T1 (Django scaffold), and T1-FIX (test discovery) are complete. T2 (asset migration) is the next task.

## What Exists Now

- Static source (unchanged):
  - `index.html`
  - `style.css`
  - `css/`
  - `js/`
  - `images/`
  - `readme.txt`
- Baseline preservation (T0):
  - `legacy_static/index.html` — byte-identical copy
  - `legacy_static/readme.txt` — byte-identical copy
  - `.gitignore`
  - `.env.example`
- Django scaffold (T1):
  - `requirements.txt` — Django 5.2.15, Pillow, dj-database-url, python-dotenv, whitenoise, psycopg[binary]
  - `manage.py`
  - `femdes_site/` — project package with env-loaded settings, WhiteNoise, dj-database-url, static/media config
  - `store/` — app package with `tests/__init__.py`
  - `static/`, `templates/` — empty directories ready for future tasks
  - Conda environment: `femdes` (Python 3.12.13)
- Agent/planning docs:
  - `AGENTS.md`, `CLAUDE.md`
  - `docs/architecture.md`, `docs/decisions.md`
  - `docs/agent/IMPLEMENTATION_PLAN.md`, `docs/agent/TASK_BOARD.md`, `docs/agent/CURRENT_TASK.md`, `docs/agent/HANDOFF.md`, `docs/agent/TEST_STATUS.md`
  - `.agent/CONTINUITY.md`

## Key Configuration

- **Environment:** Use `conda run -n femdes python manage.py <cmd>` (NOT `.venv`)
- **Settings:** `.env` loaded via python-dotenv; `dj_database_url` for DATABASES; WhiteNoise for static files
- **Default DB:** SQLite at `db.sqlite3` when `DATABASE_URL` is unset
- **Installed apps:** `store` added to `INSTALLED_APPS`

## Verification Status

- `conda run -n femdes python manage.py check` — **PASS** (0 issues)
- All 12 file-existence checks passed

## Next Action

**T2: Move static assets into Django static tree** — move `css/`, `js/`, `images/`, `style.css` into `static/store/`. See `docs/agent/IMPLEMENTATION_PLAN.md#task-2`.

## Do Not Do Yet

- Do not create database models.
- Do not configure Django admin.
- Do not create storefront views/URLs.
- Do not split `index.html` into templates.
- Do not add payment integration.
- Do not remove upstream attribution.
