# Current Task

## Task ID
TASK-006 — COMPLETE (2026-07-06)

## Completed
T6: Converted Kaira static HTML into Django templates. base.html with Kaira shell, 7 partials (icons, navbar, search_popup, cart_offcanvas, product_card, category_card, footer), 6 page templates. All static references use {% static %}. Attribution preserved. 145 tests pass.

## Next Task

**T7: Add Seed Command**

Use `docs/agent/IMPLEMENTATION_PLAN.md#task-7-add-seed-command`.

## Prerequisites

- [x] T0–T6 complete.
- [ ] Use conda env `femdes` for all Python commands.

## Guardrails

- Do not remove upstream attribution.
- Do not implement optional features.
- Seed must be idempotent.
