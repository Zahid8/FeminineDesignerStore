# Current Task

## Task ID
TASK-010 — COMPLETE (2026-07-09)

## Completed
T10: Added optional S3-compatible media storage via django-storages. Local filesystem remains default. Set DJANGO_MEDIA_STORAGE=s3 with AWS_* env vars to enable. Supports custom endpoint (R2, Spaces, B2) and custom domain (CDN). 183 tests pass.

## Optional Future Work

- Payment gateway integration
- Customer accounts and authentication
- Wishlist persistence
- Shipping carrier APIs and tax calculation
- Blog CMS
- Instagram API integration
- Custom admin dashboard
