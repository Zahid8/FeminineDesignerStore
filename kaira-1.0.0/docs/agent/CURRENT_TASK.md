# Current Task

## Task ID
TASK-006-FIX2 — COMPLETE (2026-07-07)

## Completed
T6-FIX2: Added `search` and `close` SVG symbols. Search popup now has `.btn-close-search` close control. All search controls use `#search` icon (not `#shopping-bag`). Carousel tests strengthened with DOM-relationship checks and icon-arrow control assertions. 152 tests pass.

## Next Task

**T7: Add Seed Command**

Use `docs/agent/IMPLEMENTATION_PLAN.md#task-7-add-seed-command`.

## Prerequisites

- [x] T0–T6 complete (including all FIX tasks).
- [ ] Use conda env `femdes` for all Python commands.

## Guardrails

- Seed must be idempotent.
- Do not remove upstream attribution.
- Do not implement optional features.
