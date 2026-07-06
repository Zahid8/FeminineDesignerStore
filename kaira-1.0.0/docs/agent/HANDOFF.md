# Handoff

## Summary

This repo is a static Kaira Bootstrap fashion-store template being converted into a database-backed FemDes webstore. T0 (baseline preservation) is complete. T1 (Django scaffold) is the next task.

## What Exists Now

- Static source (unchanged):
  - `index.html`
  - `style.css`
  - `css/`
  - `js/`
  - `images/`
  - `readme.txt`
- Baseline preservation (T0 complete):
  - `legacy_static/index.html` — byte-identical copy of `index.html`
  - `legacy_static/readme.txt` — byte-identical copy of `readme.txt`
  - `.gitignore` — excludes env, venv, pycache, db, media, staticfiles, .omx
  - `.env.example` — Django env template
- Agent/planning docs:
  - `AGENTS.md`
  - `CLAUDE.md`
  - `docs/architecture.md`
  - `docs/decisions.md`
  - `docs/agent/IMPLEMENTATION_PLAN.md`
  - `docs/agent/TASK_BOARD.md`
  - `docs/agent/CURRENT_TASK.md`
  - `docs/agent/HANDOFF.md`
  - `docs/agent/TEST_STATUS.md`
- Existing continuity:
  - `.agent/CONTINUITY.md`

## Key Findings

- No `.git/` directory exists in the project root (parent has a git repo).
- No automated tests exist.
- No package or backend configuration exists.
- `index.html` has hard-coded product cards, cart rows, categories, newsletter form, and links.
- `readme.txt` requires keeping the TemplatesJungle credit link unless a no-attribution license has been purchased.

## Architecture Decision

Use Django 5.2 LTS with server-rendered templates and Django admin.

## Next Action

**T1: Scaffold Django Project** — create `requirements.txt`, `manage.py`, `femdes_site/`, `store/`. See `docs/agent/IMPLEMENTATION_PLAN.md#task-1`.

## Do Not Do Yet

- Do not move assets.
- Do not delete static source.
- Do not create database models.
- Do not add payment integration.
- Do not remove upstream attribution.

## Verification Performed

- T0: All 7 validation checks passed (diff, file existence, .gitignore, .env.example).
- Original static files remain unmodified.
