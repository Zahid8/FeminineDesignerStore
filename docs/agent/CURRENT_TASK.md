# Current Task

## Task ID
TASK-016-FIX3

## Title
Synchronize final T16 test-count documentation

## Goal
Finish the T16/FIX2 documentation sync only. The application behavior for
optional SKU and optional measurement display is approved by tests, but the
agent handoff docs still contain stale full-suite counts.

## Blocking Review Findings

The required stale-count validation still fails:

```bash
rg -n "236 tests|253 tests" docs/agent/HANDOFF.md docs/agent/TEST_STATUS.md docs/agent/CURRENT_TASK.md
```

Current matches:

- `docs/agent/HANDOFF.md` still says `PASS (236 tests)`.
- `docs/agent/TEST_STATUS.md` still says `PASS (253 tests)` in the command
  comment.

## Scope

Documentation-only. Do not modify application code, migrations, templates,
tests, deployment docs, settings, seed data, or database behavior.

## Files Expected to Change

- `docs/agent/HANDOFF.md`
- `docs/agent/TEST_STATUS.md`
- `docs/agent/CURRENT_TASK.md`
- `.agent/CONTINUITY.md`

## Required Behavior

1. `docs/agent/HANDOFF.md` must report the current full-suite result as
   `260 tests`.
2. `docs/agent/TEST_STATUS.md` must report the current full-suite result as
   `260 tests` everywhere in current-state command comments.
3. Do not rewrite historical sections unless they are framed as current state.
4. Do not change application code.

## Acceptance Criteria

- The stale-count search below returns no matches.
- `git diff --name-only HEAD^..HEAD` shows only documentation/continuity files
  for this docs-only fix.
- No source code, migrations, templates, or tests are modified.

## Validation Commands

```bash
rg -n "236 tests|253 tests" docs/agent/HANDOFF.md docs/agent/TEST_STATUS.md docs/agent/CURRENT_TASK.md
git diff --check HEAD^..HEAD
```
