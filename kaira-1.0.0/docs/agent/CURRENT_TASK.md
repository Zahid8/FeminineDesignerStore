# Current Task

## Task ID
TASK-002 — COMPLETE (2026-07-06)

## Completed
T2: Moved `css/`, `js/`, `images/`, `style.css` into `static/store/`. `collectstatic` and `check` pass. Note: removed `CompressedManifestStaticFilesStorage` because `vendor.css` references missing `colorbox/loading.gif`; Django default `StaticFilesStorage` used (Whitenoise middleware still serves at runtime).

## Next Task

**T3: Add Database Models And Migrations**

Use `docs/agent/IMPLEMENTATION_PLAN.md#task-3-add-database-models`.

## Prerequisites

- [x] T0 complete — `legacy_static/` copies exist.
- [x] T1 complete — Django project scaffolded.
- [x] T2 complete — assets in `static/store/`.
- [ ] Use conda env `femdes` for all Python commands.

## Guardrails

- Do not remove attribution from footer.
- Do not implement optional payment/customer-account/wishlist work during MVP.
- Write tests before or alongside model changes.
