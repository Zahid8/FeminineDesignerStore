# CLAUDE.md

Guidance for Claude or any delegated coding model working in this repository.

## Role

You are operating on a static Kaira fashion-store template planned for conversion into the FemDes webstore. Your job is to follow the planning documents exactly and keep each change small, testable, and reversible.

## Start Here

Read these files in order:

1. `.agent/CONTINUITY.md`
2. `AGENTS.md`
3. `docs/architecture.md`
4. `docs/decisions.md`
5. `docs/agent/IMPLEMENTATION_PLAN.md`
6. `docs/agent/CURRENT_TASK.md`
7. `docs/agent/TEST_STATUS.md`

## Hard Constraints

- Do not implement webstore functionality unless the user explicitly asks you to implement.
- Do not remove or overwrite current Kaira assets without first preserving the original in `legacy_static/`.
- Do not remove upstream footer attribution unless the owner confirms a no-attribution license.
- Do not invent a different stack unless the user explicitly changes the decision in `docs/decisions.md`.
- Do not treat `.omx/` as application source.
- Do not assume Git is available; this directory currently has no `.git/`.

## Expected Implementation Style

When implementation is authorized:

- Use Django 5.2 LTS and server-rendered templates.
- Keep the Kaira frontend appearance intact while replacing hard-coded data with database-backed data.
- Use Django admin for staff product/category/discount/order management.
- Use session-backed cart behavior for the public storefront.
- Use Decimal-based money calculations and order-item price snapshots.
- Write tests before or alongside behavior changes.
- Update `docs/agent/TASK_BOARD.md`, `docs/agent/CURRENT_TASK.md`, and `docs/agent/TEST_STATUS.md` after each completed task.

## Verification

For planning-only tasks, verify by checking file existence and scanning for placeholders.

For implementation tasks, run the commands specified in the task. Minimum expected Django checks after scaffold exists:

```bash
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
python manage.py collectstatic --noinput
```

Record failures honestly in `docs/agent/TEST_STATUS.md` with the exact failing command and next fix.
