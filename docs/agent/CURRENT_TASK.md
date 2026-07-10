# Current Task

## Task ID
TASK-016-FIX2 — COMPLETE (2026-07-10)

## Completed
T16-FIX2: SKU normalization in clean() prevents uniqueness validation on blank SKU. Data migration converts legacy sku="" to NULL. Tests tightened (specific exceptions, legacy simulation, NULL persistence). 260 tests pass.
