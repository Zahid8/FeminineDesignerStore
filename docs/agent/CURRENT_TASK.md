# Current Task

## Task ID
TASK-020-FIX — Complete reference-inspired blouse storefront redesign

## Why This Fix Is Needed

The T20 commit is too narrow for the accepted task. It only changes a few home hero strings and one CSS block, adds no tests, leaves the prior whole-file `style.css` churn unresolved, commits the local `reference.png` file as a tracked binary, and still documents open Razorpay reliability work while claiming no required work remains.

## Scope

Fix only the gaps below. Do not rewrite unrelated business logic or redesign admin pages.

1. Complete the blouse-only visual pass across the public customer flow:
   - Home page.
   - Product list/search/empty results.
   - Product cards/carousels.
   - Product detail, including ready-made specs and measurement note areas.
   - Cart and empty cart.
   - Checkout.
   - Razorpay payment page.
   - Order success.
   - Account login/register/profile/orders.
   - Navbar, search popup, cart offcanvas, footer, alerts/messages.
2. Use `reference.png` for inspiration only:
   - Pastel/off-white section bands, airy spacing, rounded product/lifestyle imagery, warm CTA treatment, subtle blouse/sewing boutique accents are acceptable.
   - Do not copy baby branding, baby imagery, baby text, childish motifs, or the exact layout.
   - Remove `reference.png` from Git tracking; it is a local reference artifact, not product source.
3. Keep existing behavior intact:
   - Do not change URLs, view names, forms, CSRF behavior, cart/session behavior, checkout/order creation, Razorpay routes, account auth behavior, admin behavior, model schema, migrations, or seed data unless a test proves a required regression fix.
   - Preserve Kaira/Bootstrap/Swiper structure, TemplatesJungle attribution, product image rendering, price display, active tags, stock/new/out-of-stock cues, add-to-cart buttons, and payment/manual-fallback behavior.
4. Fix the CSS reviewability and regression issues:
   - Resolve the carried T19-FIX3 issue: `git diff --numstat 19762f0..HEAD -- static/store/style.css` must no longer show a whole-file rewrite-scale churn.
   - Keep new CSS scoped and readable. Avoid broad global overrides that accidentally restyle admin or hidden flows.
   - Remove unused CSS such as `.section-wave` if no template uses it, or wire it deliberately.
   - Restore or replace the deleted `.empty-state`, badge, mobile responsive, and logo sizing rules so empty states and mobile layouts do not regress.
   - Move new inline home hero styles into CSS classes.
5. Add meaningful tests, not shallow string checks:
   - Use structural assertions for rendered DOM where practical.
   - Cover home hero/boutique sections, product cards, product list empty/search state, product detail specs/note, cart/empty cart, checkout, Razorpay payment page, order success, account pages, search popup, footer/attribution, and mobile-safe/class hooks where server-rendered tests can prove them.
   - Tests must prove existing behavior is preserved while new visual hooks are present.
6. Keep TASK-018-FIX2 visible unless actually fixed:
   - If Razorpay order-create failure is still unresolved, do not claim "No required tasks remain".
   - If you fix it, add focused tests proving gateway order creation failure does not strand the user with a cleared cart and unreachable unpaid local order.

## Required Verification

Run and record all commands in `docs/agent/TEST_STATUS.md`:

```bash
conda run -n femdes python manage.py test store.tests.test_storefront store.tests.test_cart store.tests.test_razorpay -v 2
conda run -n femdes python manage.py test -v 1
conda run -n femdes python manage.py check
conda run -n femdes python manage.py makemigrations --check --dry-run
conda run -n femdes python manage.py collectstatic --noinput
conda run -n femdes python -m pip check
git diff --check
git diff --numstat 19762f0..HEAD -- static/store/style.css
rg -n "No required tasks remain|T0 through T19|T18-FIX2 Razorpay reliability carryover documented" docs/agent/HANDOFF.md docs/agent/TEST_STATUS.md docs/agent/CURRENT_TASK.md
```

Also run a browser/screenshot pass for at least:

- `/`
- `/products/`
- one product detail page
- `/cart/`
- `/checkout/` with cart items
- Razorpay payment page with test settings
- order success page
- account login/register/profile/orders

Document the browser/screenshot result in `docs/agent/TEST_STATUS.md`.

## Acceptance Criteria

- The public site has a cohesive, reference-inspired blouse boutique visual system across the whole customer flow, not only the home hero.
- No public page contains baby/kids reference copy or imagery copied from `reference.png`.
- `reference.png` is not tracked as product source.
- Existing storefront, cart, checkout, Razorpay, account, and admin behavior still pass tests.
- New tests are structural and would fail if the visual hooks or critical page sections were removed.
- CSS diff is scoped and reviewable, with no whole-file churn from the T19 baseline.
- Docs accurately state whether TASK-018-FIX2 remains open or has been fixed.
