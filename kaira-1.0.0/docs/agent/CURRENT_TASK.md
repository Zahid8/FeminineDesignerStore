# Current Task

## Task ID
TASK-001 — COMPLETE (2026-07-06)

## Completed
T1: Scaffold Django project shell. All 12 validation checks passed. `python manage.py check` reports 0 issues.

## Next Task

**T2: Move Static Assets Into Django Static Tree**

Use `docs/agent/IMPLEMENTATION_PLAN.md#task-2-move-static-assets-into-django-static-tree`.

## Prerequisites

- [x] T0 complete — `legacy_static/` copies exist.
- [x] T1 complete — Django project scaffolded and passing checks.
- [ ] Use conda env `femdes` for all Python commands.

## Guardrails

- Confirm `legacy_static/index.html` exists before moving any assets.
- Move `css/`, `js/`, `images/`, `style.css` into `static/store/`.
- Do not rename files during the move.
- Do not remove attribution from footer.
- Do not implement optional payment/customer-account/wishlist work during MVP.
