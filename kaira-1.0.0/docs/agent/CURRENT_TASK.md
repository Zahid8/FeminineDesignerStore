# Current Task

## Task ID
TASK-004 — COMPLETE (2026-07-06)

## Completed
T4: All 8 store models registered in Django admin. Product admin with image inline, filters, search, slug prepopulation. Order admin with readonly totals and readonly order-item inline. SiteSettings restricted to one row. 16 admin tests + 66 model tests = 82 pass.

## Next Task

**T5: Add Forms, Selectors, Services, URLs, And Views**

Use `docs/agent/IMPLEMENTATION_PLAN.md#task-5-add-forms-selectors-services-urls-and-views`.

## Prerequisites

- [x] T0–T4 complete.
- [ ] Use conda env `femdes` for all Python commands.

## Guardrails

- Do not remove attribution from footer.
- Do not implement optional payment/customer-account/wishlist work during MVP.
- Use Decimal-based money calculations.
- Session-backed cart behavior.
- Checkout must revalidate stock in a transaction.
