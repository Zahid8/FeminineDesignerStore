# Current Task

## Task ID
TASK-004-FIX — COMPLETE (2026-07-06)

## Completed
T4-FIX: ProductImage and OrderItem now directly registered with admin.site. ProductImageAdmin with list_display/filters/search. OrderItemAdmin with all snapshot fields readonly, add/delete disabled. 91 tests pass (66 model + 25 admin).

## Next Task

**T5: Add Forms, Selectors, Services, URLs, And Views**

Use `docs/agent/IMPLEMENTATION_PLAN.md#task-5-add-forms-selectors-services-urls-and-views`.

## Prerequisites

- [x] T0–T4 complete (including all FIX tasks).
- [ ] Use conda env `femdes` for all Python commands.

## Guardrails

- Do not remove attribution from footer.
- Do not implement optional payment/customer-account/wishlist work during MVP.
- Use Decimal-based money calculations.
- Session-backed cart behavior.
- Checkout must revalidate stock in a transaction.
