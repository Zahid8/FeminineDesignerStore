# Task Board

## Status Legend

- `Blocked`: cannot start until a prerequisite is resolved.
- `Ready`: can be picked up by an implementation agent.
- `In Progress`: currently being modified.
- `Review`: implementation done, waiting for verification/review.
- `Done`: accepted and verified.

## Board

| ID | Status | Task | Files | Verification |
| --- | --- | --- | --- | --- |
| T0 | Done | Confirm baseline and preserve static source | `.gitignore`, `.env.example`, `legacy_static/index.html`, `legacy_static/readme.txt` | `diff -q` checks and file existence checks |
| T1 | Done | Scaffold Django project | `requirements.txt`, `manage.py`, `femdes_site/`, `store/` | `python manage.py check` |
| T2 | Done | Move assets into Django static tree (+ cleanup) | `static/store/`, moved `css/`, `js/`, `images/`, `style.css`, `.gitignore` | `python manage.py collectstatic --noinput` |
| T3 | Done | Add database models and migrations (+ fixes) | `store/models.py`, `store/migrations/`, model tests | `python manage.py test store.tests.test_models store.tests.test_discounts` |
| T4 | Done | Configure Django admin (+ fixes) | `store/admin.py`, `store/tests/test_admin.py` | `python manage.py test store.tests.test_admin` |
| T5 | Done | Add forms, selectors, services, URLs, and views | `store/forms.py`, `store/selectors.py`, `store/services.py`, `store/views.py`, `store/urls.py`, URL config, cart/storefront tests | `python manage.py test store.tests.test_cart store.tests.test_storefront` |
| T6 | Done | Convert static HTML into Django templates | `templates/` tree | storefront tests, `collectstatic`, manual browser check |
| T7 | Done | Fix seed command image storage idempotency | `store/management/commands/seed_demo_store.py`, `store/tests/test_seed.py` | run seed twice, seed tests, full tests |
| T8 | Done | Full verification and docs update | `docs/agent/TEST_STATUS.md`, `docs/agent/HANDOFF.md`, `.agent/CONTINUITY.md` | full Django check/test/static/manual pass |
| T9 | Done | Add blouse catalog + customization (+ fixes) | `store/models.py`, `store/admin.py`, `store/views.py`, seed, templates, tests | 183 tests, collectstatic, seed idempotent |
| T10 | Done | Add production media storage (+ tests + docs) | `requirements.txt`, `femdes_site/settings.py`, `.env.example`, `store/tests/test_settings.py`, docs | 193 tests, check, collectstatic |
| T11 | Done | Add customer accounts (+ redirect fix + navbar logout + docs) | auth views/forms/templates, nullable order user link, account tests, docs | 211 tests, check, migration dry-run |
| T12 | Done | Use placeholder images, carousel, ready-made specs (+ tests + docs) | seed command, product detail template, tests, docs | 218 tests, seed idempotent |
| T13 | Done | Add admin-managed categories and storefront product tags | models, migration, admin, selectors/views, templates, tests, docs | 224 tests, check, migration dry-run |
| T14 | Done | Add manual UPI payment tracking for orders/customizations (+ T14-FIX) | order/customization payment fields, admin, templates, tests, docs | 253 tests, check, migration dry-run |
| T15 | Ready | Add customer wishlist persistence | wishlist model/services, views, templates, admin, tests | focused wishlist tests, full suite, check, migration dry-run |
| T18 | Done | Fix checkout 500 + add Razorpay payment gateway | services.py, models, settings, views, URLs, templates, tests | 267 tests, check, migration dry-run |

## Dependency Order

1. T0 must complete first.
2. T1 depends on T0.
3. T2 depends on T1.
4. T3 depends on T1.
5. T4 depends on T3.
6. T5 depends on T3.
7. T6 depends on T2 and T5.
8. T7 depends on T2, T3, and T6.
9. T8 depends on all previous tasks.
10. T12 depends on T9 and T11.
11. T13 depends on T12.
12. T14 depends on T13.
13. T15 depends on T14.

## Required Changes

- T0 through T8 are required for MVP.
- T12 is an owner-requested storefront polish task after the account work.
- T13 is an owner-requested category/tag management task and includes the
  remaining T12 documentation sync as preflight cleanup.
- T14 is an owner-requested next task carrying the remaining T13 test/docs
  cleanup into a manual UPI payment-tracking implementation.
- T15 is an owner-requested optional store feature carrying the remaining T14
  docs/test cleanup into wishlist persistence.

## Optional Improvements

Do not start these until T8 is done:

- Live payment gateway integration.
- Wishlist persistence.
- Shipping and tax integrations.
- Blog CMS.
- Instagram API integration.
- Custom admin dashboard.
