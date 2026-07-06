# Current Task

## Task ID
TASK-002-FIX — COMPLETE (2026-07-06)

## Completed
T2-FIX: Removed accidentally tracked `.claude/settings.local.json.tmp.*` from git, added `.claude/` to `.gitignore`. All asset and Django checks still pass.

## Next Task

**T3: Add Database Models And Migrations**

Use `docs/agent/IMPLEMENTATION_PLAN.md#task-3-add-database-models`.

## Prerequisites

- [x] T0 complete — `legacy_static/` copies exist.
- [x] T1 complete — Django project scaffolded.
- [x] T2 complete — assets in `static/store/`.
- [x] T2-FIX complete — `.claude/` gitignored.
- [ ] Use conda env `femdes` for all Python commands.

## Guardrails

- Do not remove attribution from footer.
- Do not implement optional payment/customer-account/wishlist work during MVP.
- Write tests before or alongside model changes.
- Use Decimal-based money calculations.
- Only one primary image per product.
- Percent discounts above 100 must fail validation.
- Fixed discount cannot reduce effective price below zero.
