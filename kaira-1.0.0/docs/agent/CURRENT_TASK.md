# Current Task

## Task ID
TASK-003 — COMPLETE (2026-07-06)

## Completed
T3: Implemented 8 store models (SiteSettings, Category, Product, ProductImage, Discount, NewsletterSubscriber, Order, OrderItem) with all validations, properties, and methods. 64 tests pass. Migrations clean.

## Next Task

**T4: Configure Django Admin**

Use `docs/agent/IMPLEMENTATION_PLAN.md#task-4-configure-django-admin`.

## Prerequisites

- [x] T0 complete — `legacy_static/` copies exist.
- [x] T1 complete — Django project scaffolded.
- [x] T2 complete — assets in `static/store/`.
- [x] T3 complete — 8 models, migrations, 64 tests pass.
- [ ] Use conda env `femdes` for all Python commands.

## Guardrails

- Do not remove attribution from footer.
- Do not implement optional payment/customer-account/wishlist work during MVP.
- Register all store models in admin.
- Restrict admin to staff/superusers.
