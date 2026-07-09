# Current Task

## Task ID
TASK-015

## Title
Add customer wishlist persistence

## Goal
Let shoppers save products to a wishlist and return to them later, while keeping
guest checkout, accounts, cart, customization, categories/tags, and manual UPI
payment tracking unchanged.

## Carryover Preflight From TASK-014-FIX
Before implementing wishlist behavior, clear the remaining non-functional review
items from T14-FIX:

1. Sync current agent docs so top-level/current state reflects T14-FIX
   completion and the actual 253-test suite.
2. Remove stale current-state claims such as T0 through T11, T0 through T13,
   211 tests, 236 tests, and 238 tests from `docs/agent/HANDOFF.md`,
   `docs/agent/TEST_STATUS.md`, `docs/agent/TASK_BOARD.md`, and
   `docs/agent/CURRENT_TASK.md`.
3. Strengthen the ready-made specs ordering test so it proves:
   - stock badge appears before `Ready-Made Specifications`;
   - `Ready-Made Specifications` appears before `Buy Now`;
   - `Buy Now` appears before `Qty`;
   - `Qty` appears before `Add to Cart`.

These are docs/test cleanup items only. Do not rewrite the payment tracking
implementation unless a strengthened test exposes a real behavior bug.

## Scope
Add wishlist behavior using the existing Django/server-rendered architecture.
Support both anonymous shoppers and authenticated customers:

- anonymous users store wishlist product IDs in the session;
- authenticated users persist wishlist rows in the database;
- logging in may merge any session wishlist items into the authenticated
  wishlist.

## Files Expected to Change
- `store/models.py`
- `store/migrations/`
- `store/admin.py`
- `store/services.py`
- `store/views.py`
- `store/urls.py`
- `templates/store/partials/navbar.html`
- `templates/store/partials/product_card.html`
- `templates/store/product_detail.html`
- `templates/store/wishlist.html`
- `store/tests/test_models.py`
- `store/tests/test_admin.py`
- `store/tests/test_storefront.py`
- `store/tests/test_accounts.py`
- `docs/agent/HANDOFF.md`
- `docs/agent/TASK_BOARD.md`
- `docs/agent/TEST_STATUS.md`
- `.agent/CONTINUITY.md`

## Required Behavior
1. Add a persistent `WishlistItem` model for authenticated users with:
   - user;
   - product;
   - created timestamp;
   - uniqueness constraint for user + product.
2. Register wishlist items in Django admin with useful list display, filters,
   and search.
3. Anonymous users can add/remove products from a session-backed wishlist.
4. Authenticated users can add/remove products from their persistent wishlist.
5. Wishlist add/remove actions must use POST and CSRF protection.
6. Wishlist page must list saved active products only.
7. Wishlist page must not crash if a saved product has no category.
8. Products in inactive categories must not be publicly shown in the wishlist.
9. Product cards and product detail pages must expose a wishlist add/remove
   control using existing Kaira/Bootstrap styling.
10. Navbar must show a wishlist link/count.
11. If an anonymous user logs in with wishlist items in the session, merge those
    items into the user's persistent wishlist and clear the session wishlist.
12. Duplicate wishlist adds must be idempotent and must not create duplicates.
13. Removing an item that is not in the wishlist must not crash.
14. Existing cart, checkout, accounts, payment tracking, customization,
    categories/tags, seed data, and media storage behavior must remain
    unchanged.

## Non-Goals
- Do not add product recommendations.
- Do not add email reminders.
- Do not add wishlist sharing.
- Do not add live payment gateway behavior.
- Do not require login to use a wishlist.
- Do not change cart behavior or checkout flow.
- Do not create a new frontend framework.

## Implementation Notes
- Prefer small service helpers for wishlist read/add/remove/count behavior.
- Reuse the public product visibility rule already used by product listing and
  product detail: active product with active category or no category.
- Keep session wishlist data simple, such as a list of product IDs.
- Use `get_active_products()` or equivalent selector logic so wishlist display
  does not leak inactive-category products.
- Preserve the owner’s current product-detail placement of Ready-Made
  Specifications below stock and before purchase controls.
- Keep UI text short and practical.

## Edge Cases to Cover
- Anonymous add/remove/list wishlist.
- Authenticated add/remove/list wishlist.
- Session wishlist merges into account on login.
- Duplicate add is idempotent for both session and authenticated wishlist.
- Removing a missing wishlist product does not 500.
- Deleted products do not break wishlist rendering.
- Product without category renders in wishlist.
- Product in inactive category is hidden from wishlist.
- Navbar count updates for session and authenticated users.

## Acceptance Criteria
- Carryover T14-FIX docs/test cleanup is complete.
- `WishlistItem` model has migration and uniqueness coverage.
- Wishlist admin configuration is tested.
- Session wishlist behavior is covered by tests.
- Authenticated wishlist behavior is covered by tests.
- Login merge behavior is covered by tests.
- Product card/detail wishlist controls are covered by tests.
- Wishlist page renders saved products and empty state.
- Existing tests still pass.
- `python manage.py makemigrations --check --dry-run` reports no changes after
  the migration is created.
- Stale-doc search returns no matches for current-state stale phrases.
- No unrelated files are modified.

## Validation Commands
```bash
conda run -n femdes python manage.py test store.tests.test_models store.tests.test_admin store.tests.test_accounts store.tests.test_storefront store.tests.test_customization -v 2
conda run -n femdes python manage.py test -v 1
conda run -n femdes python manage.py check
conda run -n femdes python manage.py makemigrations --check --dry-run
rg -n "T0 through T11|T0 through T13|211 tests pass|236 tests|238 tests|TASK-014-FIX is now ready|T14 ready" docs/agent/HANDOFF.md docs/agent/TEST_STATUS.md docs/agent/TASK_BOARD.md docs/agent/CURRENT_TASK.md
```
