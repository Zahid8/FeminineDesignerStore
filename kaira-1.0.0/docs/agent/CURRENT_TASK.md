# Current Task

## Task ID
TASK-000 — COMPLETE (2026-07-06)

## Completed
T0: Confirm baseline and preserve static source. All validation checks passed.

## Next Task

**T1: Scaffold Django Project**

Use `docs/agent/IMPLEMENTATION_PLAN.md#task-1-scaffold-django-project`.

## Prerequisites

- [x] T0 complete — `legacy_static/` copies exist and diff cleanly.
- [ ] Implementation agent must read all mandatory files per `CLAUDE.md`.
- [ ] Python 3.12+ available.

## Guardrails

- Do not move `css/`, `js/`, `images/`, or `style.css` until T2.
- Do not remove attribution from footer.
- Do not implement optional payment/customer-account/wishlist work during MVP.
- Update this file when the task completes.
