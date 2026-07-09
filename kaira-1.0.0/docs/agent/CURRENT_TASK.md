# Current Task

## Task ID
TASK-010-FIX2

## Title
Finish media-storage documentation sync and strengthen local URL test

## Goal
Close the remaining TASK-010-FIX review gaps without changing the implemented
S3-compatible media-storage feature.

## Scope
Small corrective task only. Keep the existing storage implementation and new
storage tests unless the strengthened assertion exposes a real bug.

## Files Expected to Change
- `store/tests/test_settings.py`
- `README.md`
- `docs/agent/HANDOFF.md`
- `docs/agent/TEST_STATUS.md`
- `.agent/CONTINUITY.md`

## Required Behavior
1. Strengthen the local media URL test:
   - `test_media_url_default` must assert `settings.MEDIA_URL == "/media/"`.
   - Do not use a loose substring assertion for this contract.
2. Update `README.md` so it no longer says S3-compatible object storage is
   "added later".
3. Add concise production media storage instructions to `README.md`:
   - local mode remains the default,
   - set `DJANGO_MEDIA_STORAGE=s3` to use object storage,
   - list required variables,
   - list optional endpoint/custom-domain variables,
   - show a short S3-compatible provider example,
   - state that static files still use `collectstatic`.
4. Update `docs/agent/HANDOFF.md`:
   - current verification must say 193 tests, not 183,
   - remove `Production media storage (S3/object storage)` from optional future
     work,
   - include T10-FIX as completed/verified.
5. Update `docs/agent/TEST_STATUS.md` with a short T10/T10-FIX verification
   section listing the storage tests and 193-test suite.

## Non-Goals
- Do not change S3 storage behavior unless the exact `/media/` assertion fails.
- Do not add payment, accounts, wishlist, shipping, blog, Instagram, or admin
  dashboard work.
- Do not call remote object-storage APIs.
- Do not modify product, customization, cart, checkout, or order behavior.

## Acceptance Criteria
- `store/tests/test_settings.py` asserts exact `/media/`.
- `README.md` documents the current S3 media-storage support and no longer
  presents it as future work.
- `docs/agent/HANDOFF.md` no longer lists production media storage as optional
  future work.
- `docs/agent/HANDOFF.md` reports 193 tests for the current suite.
- `docs/agent/TEST_STATUS.md` has a T10/T10-FIX verification section.
- Existing 193 tests pass.
- `makemigrations --check --dry-run` reports no model changes.
- `collectstatic --noinput` succeeds.
- `git diff --stat` shows only the files listed above unless the exact media URL
  assertion exposes a real settings bug.

## Validation Commands
```bash
conda run -n femdes python manage.py test store.tests.test_settings -v 2
conda run -n femdes python manage.py check
conda run -n femdes python manage.py makemigrations --check --dry-run
conda run -n femdes python manage.py test -v 1
conda run -n femdes python manage.py collectstatic --noinput
DJANGO_MEDIA_STORAGE=s3 AWS_STORAGE_BUCKET_NAME=test-bucket AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test conda run -n femdes python manage.py check
git diff --stat
```

## Reviewer Notes
The current implementation passes 193 tests and direct S3-mode probing with a
bucket, but the previous fix missed required README/HANDOFF updates and left
the local `MEDIA_URL` test weaker than the acceptance criterion.
