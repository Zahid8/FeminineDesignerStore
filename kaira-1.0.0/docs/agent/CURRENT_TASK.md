# Current Task

## Task ID
TASK-003-FIX — COMPLETE (2026-07-06)

## Completed
T3-FIX: SiteSettings validation in clean() + full_clean(); OrderItem now has discount_amount, created_at, sku blank=True; Order collision retry (10 attempts); all validation tests use full_clean(). 66 tests pass.

## Next Task

**T4: Configure Django Admin**

Use `docs/agent/IMPLEMENTATION_PLAN.md#task-4-configure-django-admin`.

## Prerequisites

- [x] T0 complete — `legacy_static/` copies exist.
- [x] T1 complete — Django project scaffolded.
- [x] T2 complete — assets in `static/store/`.
- [x] T3 complete — 8 models, migrations, 66 tests pass.
- [x] T3-FIX complete — validation, OrderItem, collision retry.
- [ ] Use conda env `femdes` for all Python commands.

## Guardrails

- Do not remove attribution from footer.
- Do not implement optional payment/customer-account/wishlist work during MVP.
- Register all store models in admin.
- Restrict admin to staff/superusers.
