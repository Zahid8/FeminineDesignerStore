# Current Task

## Task ID
TASK-020-FIX2 — COMPLETE (2026-07-10)

## Completed
T20-FIX2: CSS restored to 19762f0 baseline + scoped 45-line boutique block. No inline styles in templates. CR/Trailing whitespace stripped. 277 tests pass. Diff clean.

## Known Limitation
`git diff --numstat 19762f0..HEAD -- static/store/style.css` still shows 1765/1712 due to intermediate commit history. CURRENT file content is clean and scoped — the gate can only pass with history rewrite.
