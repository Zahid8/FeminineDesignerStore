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
| T2 | Ready | Move assets into Django static tree | `static/store/`, moved `css/`, `js/`, `images/`, `style.css` | `python manage.py collectstatic --noinput` |
| T3 | Blocked | Add database models and migrations | `store/models.py`, `store/migrations/`, model tests | `python manage.py test store.tests.test_models store.tests.test_discounts` |
| T4 | Blocked | Configure Django admin | `store/admin.py`, `store/tests/test_admin.py` | `python manage.py test store.tests.test_admin` |
| T5 | Blocked | Add forms, selectors, services, URLs, and views | `store/forms.py`, `store/selectors.py`, `store/services.py`, `store/views.py`, `store/urls.py`, URL config, cart/storefront tests | `python manage.py test store.tests.test_cart store.tests.test_storefront` |
| T6 | Blocked | Convert static HTML into Django templates | `templates/` tree | storefront tests, `collectstatic`, manual browser check |
| T7 | Blocked | Add seed command | `store/management/commands/seed_demo_store.py`, `store/tests/test_seed.py` | run seed twice and seed tests |
| T8 | Blocked | Full verification and docs update | `docs/agent/TEST_STATUS.md`, `docs/agent/HANDOFF.md`, `.agent/CONTINUITY.md` | full Django check/test/static/manual pass |

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

## Required Changes

- T0 through T8 are required for MVP.

## Optional Improvements

Do not start these until T8 is done:

- Payment integration.
- Customer accounts.
- Wishlist persistence.
- Shipping and tax integrations.
- Blog CMS.
- Instagram API integration.
- Custom admin dashboard.
