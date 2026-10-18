# Current Task

> **T35 — Neumorphic admin theme: DONE (2026-10-17)** (notes at end).
> **T34 — Online Orders in the billing app: DONE (2026-10-17)** (notes at end).
> **T33 — Made-to-measure redesign: DONE (2026-10-17)** (notes at end).
> **T32 — Component polish pass: DONE (2026-10-17)** (notes at end).
> **T31 — Concept A + B styling pass: DONE (2026-10-17)** (notes at end).
> **T30 — Customer features + phone OTP login: DONE (2026-10-17)** (notes at end).
> **T29 — Reference-driven redesign: DONE (2026-10-17)** (notes at end).
> **T28 — Customer-facing UI revamp: DONE (2026-10-17).** See notes at the end
> of this file. TASK-027-FIX below is still open: T28 already satisfies its
> markup/JS requirements 1-4 (stable `data-quantity-stepper` / `data-action`
> hooks rendered server-side in product and cart forms, explicit numeric bounds
> with min=0 honored, exact-trigger search focus restore, `<ol>` status steps
> with a single `aria-current="step"`), but the dedicated T27 tests (item 5)
> and the T27 doc/handoff updates have not been written.

## Task ID
TASK-027-FIX — Correct progressive controls and prove client behavior

## Context

Commit `3f5b44c` passes the focused 134-test suite and full 331-test suite, but T27 is not accepted.

The current implementation misses several explicit TASK-027 requirements:

- `static/store/js/femdes.js` calculates bounds with
  `parseInt(input.getAttribute("min"), 10) || 1`. For the cart's valid
  `min="0"`, this produces 1, so the decrement control cannot reach the
  server-supported removal value of 0.
- Quantity buttons are generated dynamically without the required stable
  `data-*` hooks. The product/cart responses contain no decrement/increment
  controls when JavaScript is disabled.
- Escape restores focus with `document.querySelector(".search-button")`,
  which always chooses the first trigger in DOM order. On desktop that is the
  hidden mobile trigger, not the control that opened the popup.
- The order statuses are still an unlabelled `div` of `span` elements, not the
  required labelled list/step sequence.
- The only new storefront test checks script inclusion/order. There are no
  tests for quantity form contracts, button types/hooks/bounds, clamping, exact
  current-status semantics, search focus restoration, or no-JavaScript
  fallback.
- Required T27 browser evidence and task-board/handoff/test-status updates were
  not completed.

Keep this correction limited to T27. Do not change cart/order services, routes,
models, migrations, payment behavior, or unrelated styling.

## Required Fix

1. Render accessible quantity controls in both templates.
   - In the product add-to-cart form and every cart update form, render:
     - a wrapper with a stable `data-quantity-stepper` hook,
     - a decrement button with `type="button"`, a stable action hook, and a
       descriptive `aria-label`,
     - the existing number input with its existing name/value/min/max,
     - an increment button with `type="button"`, a stable action hook, and a
       descriptive `aria-label`.
   - Preserve each form's POST method, existing action, CSRF token, and submit
     button.
   - The forms and number inputs must remain usable when JavaScript is disabled.

2. Correct and simplify `static/store/js/femdes.js`.
   - Use event delegation against the rendered `data-*` hooks; do not create or
     reparent form controls in JavaScript.
   - Parse missing/invalid bounds explicitly. Do not use `||` for numeric bounds
     because zero is valid.
   - Product quantity clamps to `1..stock_quantity`.
   - Cart quantity clamps to `0..99`.
   - Blank, non-numeric, below-minimum, and above-maximum values recover
     deterministically.
   - Step clicks only update the input. They must not submit, navigate, fetch,
     or mutate cart/order state.
   - Keep initialization idempotent and tolerant of absent targets.

3. Fix search focus ownership.
   - Record the exact `.search-button` that opened the popup.
   - Focus `input[name="q"]` only when the popup is visible.
   - Escape must close the visible popup and restore focus to that exact trigger,
     including the desktop trigger when desktop navigation opened it.
   - The close button must also close the popup and restore focus consistently.
   - Do not add a second search UI or replace the server GET search form.

4. Add complete order-status semantics.
   - Render the statuses as a labelled list/step sequence using appropriate
     list/list-item HTML or roles.
   - Preserve all six server-rendered status labels.
   - Exactly one status, matching `order.status`, must receive
     `aria-current="step"`.

5. Add meaningful automated tests.
   - Template/response tests must prove, for both product and cart forms:
     - POST method and exact route action,
     - CSRF input remains present,
     - number input name and exact bounds,
     - decrement/increment buttons are inside the correct form,
     - both step buttons are `type="button"` and expose the expected hooks.
   - Test the quantity calculation as executable JavaScript, not source-text
     matching. Place dependency-free Node tests outside the production static
     tree, for example `store/tests/js/femdes.test.js`, and run them with
     `node --test`.
   - The Node tests must cover:
     - cart decrement `1 -> 0`,
     - cart decrement at `0 -> 0`,
     - product decrement at `1 -> 1`,
     - increment at maximum remains at maximum,
     - blank/non-numeric input recovery,
     - below/above-bound recovery.
   - Order-detail tests must identify the current status element for at least
     two statuses, prove it contains the correct label, prove exactly one
     `aria-current="step"`, and prove the labelled list structure.
   - Keep the existing script inclusion/order test, but it is not sufficient by
     itself.

6. Complete the carried documentation.
   - Update `TASK_BOARD.md` so completed T22-T26 are not `Ready` and T27 is in
     the correct review state.
   - Update `HANDOFF.md` and `TEST_STATUS.md` to the actual final test count.
   - Record the T27 Node command and desktop/mobile browser observations in
     `TEST_STATUS.md`.
   - Preserve historical counts in historical sections.

## Acceptance Criteria

- Cart steppers can visibly reach 0; product steppers cannot go below 1.
- All malformed and boundary values clamp predictably.
- Quantity step buttons never submit their containing forms.
- Product/cart POST actions, CSRF tokens, inputs, and submit controls remain
  functional without JavaScript.
- Search focus returns to the exact trigger that opened the popup.
- Search closes correctly by Escape and by the visible close button.
- The status timeline is a labelled sequence with exactly one correctly
  labelled `aria-current="step"`.
- JavaScript contains no cart/order/payment business logic or network request.
- No model, migration, route, service, payment, pricing, or stock logic changes.
- `static/store/js/store.js` remains absent.
- Automated tests exercise quantity calculations and template structure.
- Desktop/mobile browser checks report no console errors, overlap, unexpected
  form submission, or focus loss.
- Current-state documentation matches the verified result.

## DeepSeek Self-Validation Loop

Before claiming completion:

1. Fail-first:
   - Add the form-structure and Node quantity tests first.
   - Confirm the current code fails because cart minimum resolves to 1 and
     rendered step buttons/hooks are absent.

2. Focused automated verification:
   ```bash
   node --check static/store/js/femdes.js
   node --test store/tests/js/femdes.test.js
   conda run -n femdes python manage.py test store.tests.test_storefront store.tests.test_cart store.tests.test_accounts store.tests.test_invoices -v 2
   ```

3. Progressive fallback and scope checks:
   ```bash
   test ! -f static/store/js/store.js
   ! rg -n "fetch\(|XMLHttpRequest|Order\.objects|order\.status" static/store/js/femdes.js
   git diff --name-status
   git diff --check
   ```
   With JavaScript disabled, manually submit product add-to-cart, cart update,
   cart remove, search, and load an order detail page.

4. Browser behavior at one desktop and one mobile viewport:
   - Verify product bounds, cart zero, malformed-value recovery, and no
     automatic submission.
   - Open search from each available trigger, then verify input focus, Escape,
     close-button behavior, and focus restoration to the same trigger.
   - Verify the status sequence remains readable with one current step.
   - Record viewport sizes, tested URLs, console result, and observations in
     `TEST_STATUS.md`.

5. Full verification:
   ```bash
   conda run -n femdes python manage.py test -v 1
   conda run -n femdes python manage.py check
   conda run -n femdes python manage.py makemigrations --check --dry-run
   conda run -n femdes python -m pip check
   conda run -n femdes python manage.py collectstatic --noinput
   git diff --check
   ```

6. Final audit:
   - Map every acceptance criterion to a test or recorded browser observation.
   - Confirm the diff is limited to `femdes.js`, the affected templates,
     focused tests, minimal stepper CSS if needed, and required agent docs.


---

## T28 Notes — Customer-facing UI revamp (completed 2026-10-17)

Owner request: make the customer-facing site look "very amazing"; any popular
JavaScript allowed; a stack change was offered. **Decision:** keep Django 5.2
server-rendered templates (per `docs/decisions.md`). The visual gap was entirely
front-end; a rewrite would risk checkout/payment/admin behavior and 331 tests
for no design gain.

Implementation:
- `static/store/css/femdes-theme.css` (new): "Atelier" design system loaded
  after Kaira `style.css` (which is untouched). Palette ivory/blush/wine/gold,
  Cormorant Garamond + Manrope, arch motifs, tinted image frames with
  `mix-blend-mode: multiply` so white studio backgrounds take the brand tone.
- `templates/base.html`: Bootstrap 5.3.0-alpha3 -> 5.3.8; Swiper 9 -> 11.2.10;
  added GSAP 3.15 + ScrollTrigger and Lenis 1.3.27. All CDN tags pinned with
  SRI hashes computed from the downloaded files. `SmoothScroll.js` is no longer
  loaded (Lenis replaces it); the file remains in `static/`. Adds announcement
  bar, Django `messages` rendered as toasts (previously never displayed),
  scroll progress bar, back-to-top, and a head script that swaps broken
  product images for `static/store/images/femdes-placeholder.svg`.
- All storefront, account, order, customization and payment templates
  redesigned; every test-locked Kaira/IndiChic hook kept.
- `static/store/js/femdes.js`: T27 steppers/search focus plus hero Swiper
  (fade + GSAP word reveal), scroll reveals, parallax, Lenis wiring (paused
  while offcanvas/search are open), gallery zoom + thumbnail sync, toasts.
  Everything degrades to the server-rendered page without JS or with
  `prefers-reduced-motion`.
- Staff pages and `invoice.html` inherit the theme but were not redesigned.

Known data issues (not code): demo categories have placeholder names ("D",
"Review Cat"), and most demo products use Kaira stock photos. Upload real
product/category images in Django admin for the design to land fully.


---

## T29 Notes — Reference-driven redesign (completed 2026-10-17)

Owner request: study famous fashion sites and adopt their best UI; then
"don't push up the drama"; use popular CSS/JS frameworks. References and the
pattern → source mapping live in `docs/agent/design-references/README.md`.

- `static/store/css/femdes-theme.css` rewritten ("Maison" v2): Jost body
  (already loaded by Kaira) + Cormorant Garamond display, tracked uppercase
  labels, hairline rules, square corners, wine accent used sparingly. Marquee,
  spinning stamp, floating badges and outlined giant footer text removed.
- Header: two-tier (utility row with centred logo + icons, centred tracked
  nav), compacts on scroll; desktop mega menu (Alpine.js) with category links
  and two image tiles; mobile offcanvas keeps category sub-list.
- `HomeBanner` model + admin + migration `0015_home_banner`: staff can upload
  full-bleed campaign slides (image, optional mobile crop, eyebrow, title,
  subtitle, CTA, light/dark text theme). With no banners the home page falls
  back to a full-height split hero built from featured/new products.
- PLP: tabs-style category/tag filter bar, toolbar with count, server-side
  `?sort=` (whitelisted in `selectors.PRODUCT_SORTS`) and a grid-density
  toggle persisted in localStorage.
- PDP: `Product.color_choices` / `size_choices` parse the existing
  `color_options` / `size_options` text fields into radio chips inside the
  add-to-cart form; outlined Add to Cart + filled Buy Now + Customize; "Order
  on WhatsApp" and a floating WhatsApp button appear only when
  `SiteSettings.whatsapp_url` is set; sticky mobile buy bar submits the main
  form via `form="pdp-cart-form"`.
- Cards: `Product.secondary_image` powers a hover image swap.
- Search popup: live results fetched from the server-rendered `/shop/?q=`.
- Footer: newsletter row with underline input, link columns collapse to
  `<details>` on mobile.
- Alpine.js 3.17.4 added (SRI-pinned, deferred); Bootstrap/Swiper/GSAP/Lenis
  unchanged from T28.

Known data issues remain: demo categories have placeholder names and most
demo products use Kaira stock photos; upload real media in Django admin.


---

## T30 Notes — Customer features + phone OTP login (completed 2026-10-17)

Owner request: integrate every necessary feature seen on similar sites, plus
phone-number OTP login (Indian numbers first, extendable). A Playwright survey
of Torani, Masaba, Raw Mango, Anita Dongre, Sabyasachi, Zimmermann, Toteme and
Jaypore decided the scope; the feature × site table and the deliberate skips
(reviews, gift cards, currency switch) are in
`docs/agent/design-references/README.md`.

Commits: `e0ca55e` (T28–T30 part 1), `c67ea3e` (A), `d3e05e4` (B), `1b29a30` (C), plus a docs/polish commit.

| Area | What | Where |
|------|------|-------|
| Auth | Phone OTP sign-in/verification (hashed single-use codes, 5 min expiry, 5 attempts, resend cooldown, per-phone/per-IP hourly limits); password reset | `store/phone.py`, `store/sms.py`, `store/otp.py`, `store/views_phone.py` |
| Wishlist | Session for guests, DB for accounts, merged on sign-in; hearts on cards/PDP; `/wishlist/` | `store/wishlist.py`, `store/apps.py` |
| SEO | sitemap.xml, robots.txt, canonical + OpenGraph, Product and FAQPage JSON-LD, 404/500 | `store/sitemaps.py`, `store/seo.py` |
| Checkout | Shipping fee + free-shipping threshold, payment choice (Razorpay / UPI / COD), editable UPI + customization advance, order emails; cart and order share `compute_totals()` | `store/services.py` |
| Catalogue | Filters (availability, price, size, colour, occasion, fabric, ready-to-ship, sale), pagination + load more, occasions, fulfilment + dispatch note, fabric/care, country of origin, complete-the-look, size charts, low-stock, back-in-stock emails | `store/selectors.py`, `store/stock_alerts.py` |
| Content & service | Policy pages, FAQ, client diaries, appointment booking, guest order tracking, grievance officer / GSTIN display | `store/views_extra.py` |

Bug fixed on the way: orders with sale items stored the discounted amount as
the subtotal and also showed a discount row, so the discount looked like it
was never applied. Subtotal is now list price; Subtotal − Discount + Shipping = Total.

### Deploy checklist

1. `python manage.py migrate` (applies 0015–0021; 0021 restates pre-T30 discounted order subtotals so invoices add up — totals unchanged).
2. Set env vars (all listed in `.env.example`):
   - Email: `DJANGO_EMAIL_HOST`, `DJANGO_EMAIL_PORT`, `DJANGO_EMAIL_HOST_USER`,
     `DJANGO_EMAIL_HOST_PASSWORD`, `DJANGO_DEFAULT_FROM_EMAIL`, optional
     `STORE_NOTIFY_EMAIL`. Without a host, emails only print to the console.
   - SMS: `SMS_BACKEND=store.sms.TwilioSmsBackend` + `TWILIO_ACCOUNT_SID`,
     `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`. **Indian SMS requires DLT
     registration of the sender ID and OTP template** with the provider. To use
     MSG91/Gupshup instead, subclass `store.sms.BaseSmsBackend`.
   - `PHONE_LOGIN_COUNTRIES` (default `IN`; add e.g. `IN,AE` to extend).
   - Behind a hosting proxy: `CLIENT_IP_HEADER=HTTP_X_FORWARDED_FOR`
     (otherwise every visitor shares the proxy IP and the per-IP OTP limit
     of 20/hour throttles the whole store).
   - `SITE_URL` for links in background (back-in-stock) emails.
3. In Django admin fill: Site settings → Payments (UPI ID, advance, COD),
   Shipping, Product pages (price note, low-stock), Legal & grievance officer;
   WhatsApp URL; Occasions; Size charts; Pages (shipping, returns, privacy,
   terms); FAQs; Client diaries; product fabric/care/dispatch/sizes/colours.
   Nothing was seeded — features stay hidden until content exists.

### Known limitations
- Price filter and "On sale" use list price / compare-at price, not
  Discount-model sale prices.
- Cancelling an order does not restore stock, so it will not trigger
  back-in-stock alerts.

### Still open
- TASK-027-FIX item 5 dedicated tests.
- Demo categories/products still use placeholder names and stock photos.


---

## T31 Notes — Concept A primary + Concept B supporting (completed 2026-10-17)

Owner brief: combine a primary visual style with supporting elements; chose
A (Luxury Boutique: ivory/charcoal, editorial hero, 4-column grid, discreet
gold/brown accents, Swiss-style type) as primary with B (Modern Instagram
Boutique: warm sections, highlighted new arrivals/bestsellers, clear sale
prices, promo banners, mobile quick-add) supporting. Concept C not used.

- Tokens: `--fd-accent` brown-gold replaces wine for eyebrows, links,
  buttons, filters; wine is kept only for sale prices, −% badges and errors.
  Body font Inter (Jost remains as fallback); announcement bar is charcoal.
- Header: up to four category links beside Shop (desktop); Shop mega menu
  unchanged.
- Hero: split hero now has one primary CTA plus a text link.
- `SiteSettings.announcement_text/url` drive the top bar (blank hides it).
- `HomeBanner.placement` = hero | promo; promo banners render as image +
  copy bands after New Arrivals (alternating sides). Migration 0022.
- Cards/PDP: −N% badge (`percent_off` filter), Bestseller badge, sale price in
  wine; Add to Cart is the filled primary button, Buy Now outlined; mobile
  quick-add targets are 44px; Best Sellers section sits on a cream band.


---

## T32 Notes — Component polish (completed 2026-10-17)

Owner asked for every component to be made excellent. Audited every page at
1440 and 390 px (`docs/agent/browser-checks/audit.js`) and fixed what fell short:

- Cart page: product image thumbnails, Item/Quantity/Total columns, dispatch
  note, Remove + Move to wishlist, Update button only appears after a change,
  sticky order summary with WhatsApp option and payment icons, "You may also
  like" suggestions (`cart_suggestions` in `cart_detail`).
- Cart drawer: thumbnails, inline quantity stepper that submits automatically,
  free-shipping progress at top, sticky totals footer.
- Auth: `partials/form_fields.html` replaces `form.as_p`; placeholders,
  autocomplete, help text behind a "Requirements" disclosure.
- Feedback: "added to your bag" toast with a View bag link (`extra_tags="cart"`).
- Utility pages use `fd-page-header is-compact`.
- Product page: thumbnails stack vertically beside the image on desktop.
- Cards: "N colours" line; badges never overlap the heart; only the first
  badge shows on phones.
- Home editorial uses the product photo only if its file exists on storage
  (`_editorial_image`), otherwise a lifestyle photo.


---

## T33 Notes — Made-to-measure redesign (completed 2026-10-17)

Owner asked to redesign product customization (UI and functionality), then
to replace the unprofessional disclaimer and the "send a link on WhatsApp for
the advance" step with something customer-friendly.

- Custom fit is now a cart line: `services.add_to_cart(custom=...)` stores
  `{"measurements": {...inches}, "sleeve_style", "notes"}`; the cart key
  includes a fingerprint so different measurement sets are separate lines;
  `OrderItem.customization` snapshots it; unit price = effective price +
  `Product.customization_fee` (or `SiteSettings.customization_fee`);
  dispatch shows `customization_lead_time`. Payment happens at checkout.
- `store/measurements.py` is the single spec (keys, labels, ranges, hints,
  sleeve styles, cm→in). `CustomFitForm` validates ranges and converts units.
- PDP: Ready-made / Made-to-measure fit switch; 3-step Alpine builder
  (measurements with in/cm toggle + inline SVG guide; style + notes; review
  with price, lead time and terms). Works without JS (all steps visible).
- Saved measurements: logged-in customers get the last order's measurements
  prefilled (`CustomerProfile.saved_measurements`).
- Secondary path "Request a fitting call": saves a `CustomizationRequest`
  (reference `FIT-XXXXXXXX`, staff email via `STORE_NOTIFY_EMAIL`), confirmation
  page with next steps, one-tap WhatsApp (prefilled message) and
  "Add to bag with these measurements" (session prefill). No advance payment
  or link-copying.
- `SiteSettings.customization_terms` (admin-editable) replaces the disclaimer
  on the PDP, cart/checkout and request pages. `customization_advance_amount`
  is retained but no longer shown.
- Tests: `store/tests/test_custom_fit.py` (18). Two older tests updated:
  "Disclaimer" → "Made-to-measure terms"; related products exclude the
  product itself.


---

## T34 Notes — Online Orders in the Feminine Designer billing app (2026-10-17)

Owner asked to route webstore orders into the billing system
(`~/Projects/Zahid/Feminine_Designer`, Next.js 16 + Supabase on Vercel) as an
"Online Orders" section, following that app's design principles.

Approach: the billing app pulls from a token-protected JSON API on the
webstore (no shared database; Vercel cannot reach the shop's SQLite/Postgres).

Webstore (`store/views_api.py`, tests in `store/tests/test_api.py`):
- `GET /api/online-orders/?status=&payment_status=&since=&q=&limit=` — newest
  first, items with made-to-measure summaries, links to admin/staff pages.
- `GET|POST /api/online-orders/<number>/` — detail; POST JSON
  `{status, payment_status, payment_notes}` updates the order (choices validated,
  `paid_at` set when marked paid).
- Auth: `Authorization: Bearer <WEBSTORE_API_TOKEN>`; 503 until the env var is
  set; `/api/` disallowed in robots.txt.

Billing app (changes left **uncommitted** there pending owner approval):
- `src/lib/webstore/env.ts`, `src/services/online-orders/online-order-service.ts`
  (+ vitest), `src/app/online-orders/{page,loading,actions}.tsx`,
  `src/app/online-orders/[orderNumber]/page.tsx`,
  `src/components/online-orders/*`, sidebar entry (`app-shell-frame.tsx`,
  `--color-section-online`), "Online Orders" button on the Orders page (phone
  tabs intentionally stay at five), `.env.example` vars
  `WEBSTORE_API_URL` / `WEBSTORE_API_TOKEN`.
- Verified with a production build against the demo webstore: list, detail,
  status + payment update synced back (`docs/agent/browser-checks/billing.js`,
  screenshots in `docs/agent/screenshots/t34/`).

Deploy: set `WEBSTORE_API_TOKEN` on the webstore host and the same token plus
`WEBSTORE_API_URL` on Vercel, then redeploy the billing app.

## T35 notes — Neumorphic admin theme (2026-10-17)

- `templates/admin/base_site.html` overrides Django's admin base: FD monogram
  brand, Cormorant/Inter fonts, loads `static/store/css/admin-neu.css`.
- `admin-neu.css` remaps Django admin CSS variables to the store palette
  (ivory / ink / brown-gold) and adds soft raised/pressed shadows on cards,
  sidebar, filters, inputs, buttons, paginator and the login card. Tables
  stay flat inside raised containers for readability. Dark and auto themes
  (Django's theme toggle) have their own palette.
- `admin.site.site_header/site_title` = "FemDes Admin", `index_title` =
  "Store management" (store/admin.py).
- Login rules use `body.login` so they beat Django's later-loaded login.css.
- Verified by Playwright screenshots (login, index, changelist, change form;
  light + dark + mobile login) — script in /tmp/fdshot/admin.js.

## T35-FIX — Made-to-measure ignores stock (2026-10-17)

- Bug (owner report, deployed site): "Add Made-to-Measure to Bag" did nothing
  on products with stock 0. The PDP offers the builder on sold-out products,
  but `services.add_to_cart` rejected them as out of stock.
- Owner decision: made-to-measure is stitched to order, so custom lines skip
  stock checks (add, update, checkout) and do not decrement stock. Ready-made
  lines keep all stock rules. Tests: `MadeToMeasureStockTests`.
- E2E browser verification (production-like: DEBUG=False, whitenoise, port
  8770, `docs/agent/browser-checks/e2e_mtm.js`, 28/28 pass) found and fixed:
  1. Alpine `x-model` with empty `m: {}` blanked every server-prefilled
     measurement (product defaults, saved measurements, fitting-request
     prefill, values re-shown after a validation error). `m` is now seeded
     from the bound form values.
  2. Checkout hid the made-to-measure terms on mixed carts (`dictsort` on
     `custom`); now uses `cart.has_custom` from `get_cart_summary`.
  3. After a validation error the page reloaded at the top; the builder now
     scrolls itself into view when the form has errors.

## T36 — Admin cloned from the billing app's design (2026-10-17)

- Owner: the neumorphic admin "isn't that good… just like the billing system
  UI". The admin now mirrors Feminine_Designer's "soft boutique" system:
  wine-gradient sidebar with a coloured icon tile per section (Sales,
  Catalogue, Customers, Content, Settings), blush background, Fraunces +
  Plus Jakarta Sans, raised cards, pressed inputs, wine→rose primary buttons,
  peach table headers, pill status badges, light-only (no theme toggle).
- Files: `templates/admin/{base_site,nav_sidebar,index}.html`,
  `store/templatetags/fd_admin.py` (icons, grouped nav, dashboard stats),
  `static/store/css/admin-neu.css`, `static/store/js/admin-fd.js` (mobile
  drawer + status pills on change lists).
- Dashboard: open orders, payments to review, paid this month, fitting
  requests (7 days), new appointments, low stock, recent orders, fitting
  requests, recent actions, quick actions.
- Sidebar keeps Django's `#nav-sidebar` / `#nav-filter` / `th[scope=row] a`
  structure so the built-in menu filter still works.
- Browser check: `docs/agent/browser-checks/admin_theme.js` (no JS errors).

## T37 — Delivered stage + order type for the billing app (2026-10-17)

- `Order.STATUS_CHOICES` gains "delivered" (migration 0025, choices only);
  customer timelines include it.
- API: `order_type` (ready_made / made_to_measure / mixed) + label on every
  order, `order_types` in list responses, `?type=ready_made|made_to_measure`
  filter (made_to_measure includes mixed). Tests: `OrderTypeAndDeliveredTests`.
- Billing app (Feminine_Designer, same day): stage tracker, one-tap next
  stage, Shipped/Delivered/Fulfilled tabs, type badges and filter.
  Browser check: `docs/agent/browser-checks/billing_stages.js` (18/18).

## T37-FIX — Made-to-measure still "not adding" on the live site (2026-10-17)

- Reproduced on https://zahidhussain909.pythonanywhere.com: the only product
  prefills 4 of 6 required measurements (Opening, Bicep empty). The builder
  let customers reach Review and submit; the server rejected it and re-rendered
  with errors far below the guide image on phones, so nothing seemed to happen
  and the bag stayed empty. (With all six filled it already worked live.)
- Fix: client-side validation in the builder (required + range, in or cm):
  "Continue to style" and "Add Made-to-Measure to Bag" (and the fitting-call
  submit) are guarded; failing jumps to step 1, opens the field, scrolls it to
  the centre and focuses it, with an inline message per field; Review lists
  exactly what is missing. Server errors re-render and focus the first error.
  femdes.js no longer marks a prevented submit as busy.
- Checks: `browser-checks/mtm_guard.js` (24/24 desktop+mobile),
  `browser-checks/e2e_mtm.js` (28/28 on a DEBUG=False server), 488 tests OK.

## T38 — Online order bills in the billing app (2026-10-18)

- Billing app (Feminine_Designer 78e17bd): per-order bill PDF in the in-store
  receipt design, public signed link `/bill/online/{order}/{sig}`, and
  WhatsApp messages (confirmation / shipped / delivered / payment reminder)
  carrying the bill link; templates editable in Settings. No webstore changes.
- Browser check: `docs/agent/browser-checks/billing_bill.js` (12/12).

## T39 — Google Maps location + full order details in billing (2026-10-18)

- Optional "Google Maps location" on checkout/profile (store/locations.py
  accepts only Google Maps links, extracts the URL from pasted share text;
  "Use my current location" fills a maps?q=lat,lng link). Order.location_url
  and CustomerProfile.location_url (migration 0026); shown on confirmation,
  My Orders, invoice, staff page, admin; remembered on the profile.
- Checkout keeps the order notes when the form re-renders with an error
  (they were silently lost before).
- API: location_url, payment_notes, Razorpay ids, customer account /
  verified phone / orders_count, item sleeve/tailor notes/category/photo/
  absolute product link. Billing app shows all of it (Delivery card with
  Maps button + copy, Customer, Payment, Order info, item photos).
- Browser check: `browser-checks/location_e2e.js` (27/27, shop → billing → bill PDF).

## T40 — Soft studio UI pass (2026-10-18)

- Owner: measurement guide and builder "going out of the box", Add to Cart
  "ugly", make every page amazing, sprinkle neumorphism, may use billing
  colours, add Three.js-style animation.
- Builder now lives in its own full-width row under the gallery/buy panel
  (`#customize-row`; Alpine `fit` state moved up to `section.fd-pdp`), so
  the guide, product guide image and 3-column measurement grid fit on
  desktop; steps wrap into a pill track on mobile. No page scrolls sideways
  any more (checkout `row.g-5` gutter fixed on phones).
- `femdes-theme.css` §21: billing wine→rose primary buttons (pill), raised
  ivory secondary buttons, pressed inputs/steppers/unit toggle, raised
  cards (summary, checkout, auth, dialogs, notes), pill chips/badges,
  rounded media, round icon buttons, payment/fit option cards.
- `static/store/js/silk.js`: Three.js (r158, SRI, lazy-loaded on first
  approach) silk shader behind the home made-to-measure band (wine) and the
  newsletter band (ivory); renders only while visible, DPR ≤ 1.5,
  reduced-motion = still frame. Markup: `<canvas data-silk data-silk-palette>`
  inside a `.has-silk` section.
- Checks: `browser-checks/overflow.js` (0 sideways pages), `audit.js`
  before/after captures, e2e_mtm 28/28 and mtm_guard 24/24 on a
  DEBUG=False server, 495 tests OK.
- Follow-up (owner): the measurement guide must not sit above the inputs.
  The guide (diagram, product guide image, note, per-field how-to) now lives
  in `#measure-guide-dialog`, opened by the "How to measure" button next to
  the unit toggle; the builder form is a single column (3 fields per row on
  desktop). Check: `browser-checks/guide_dialog.js`.
- Gallery: slides carry their own cream background + isolation so the next
  photo no longer flashes white mid-transition (verified: 0 pure-white
  samples across 6 frames of a slide).
- Mobile pass: no sideways scroll at 360px or 390px; tap targets ≥ 40px for
  text buttons, links, steppers, header icons, filter pills, footer socials
  (`browser-checks/taps.js`). Fresh mobile captures reviewed for every page.

## T41 — Customer bill matches the billing app (2026-10-18)

- `templates/store/invoice.html` is now a standalone sheet in the billing
  app's receipt design (Fraunces + Plus Jakarta Sans, wine band with logo,
  info strip, item summary with measurements, delivery address + terms,
  payment summary, signatures, thank-you). Responsive: 2-column strip and
  stacked columns on phones; print styles for A4.
- `store/billing_links.py` signs `/bill/online/{ORDER}/{sig}` exactly like
  the billing app (shared HMAC context + test vector), so with
  `BILLING_APP_URL` + `BILL_LINK_SECRET` set the shop's "Download PDF" (bill
  page, order success page) serves the identical PDF the staff app produces.
  Without them the page offers "Save as PDF" (print).
- Checks: `browser-checks/invoice_check.js` (no sideways scroll on phone,
  PDF link present; PDF fetched from the billing app = 200 application/pdf).
- Owner: no guide in the customize section at all (it is already in the
  product page's "Measurement Guide" accordion). The "How to measure" button
  and dialog were removed; the builder is just the fields and the step
  buttons.
- Owner: keep the original customize design (in the buy column under the
  fit tabs); only the two guide images go. Restored: builder back inside
  `.fd-fit`, two fields per row, measurement note + "Not sure? Book a
  fitting…" text under the fields, Continue button right below.

## T42 — Standard Indian address at checkout (2026-10-18)

- `store/addresses.py`: states/UTs list, 6-digit PIN and 10-digit mobile
  validation (+91 / leading 0 accepted, stored as 10 digits), `compose()`
  for the printable block.
- Order and CustomerProfile gain address_line1/2, city, state, pincode,
  country (migration 0027); `shipping_address` stays as the composed text
  used by bills, emails, staff pages and the billing app. API adds
  `shipping` {line1, line2, city, state, pincode, country}.
- `AddressFieldsMixin` (CheckoutForm, ProfileEditForm): structured fields
  with proper autocomplete hints; legacy free-text `shipping_address` posts
  still accepted (API/tests). Checkout mobile number is now required.
  Logged-in customers get name/phone/address remembered and prefilled.
- Partial `store/partials/address_fields.html` used by checkout and profile
  edit. Tests: StructuredAddressTests; older tests given valid mobiles.

## T43 — Admin deletes audit (2026-10-18)

- Audit of every admin permission override and FK delete rule. Blockers
  found and fixed: OrderItemAdmin denied delete to everyone (now superuser
  only, so orders delete with their items); CustomizationRequest.product
  was PROTECT (now SET_NULL + `product_name` snapshot, migration 0028 with
  backfill, `display_name` used by emails/pages). Users delete cleanly
  (profile/wishlist cascade, orders and appointments keep their data).
- Billing app holds no copy of shop data: it reads the API live, so a shop
  deletion disappears from Online Orders immediately (API list/detail test).

## T44 — "Edit storefront" handoff from the billing app (2026-10-18)

- `store/views_sso.py` + `/admin/handoff/?t=…` (before admin urls): verifies a
  short-lived (≤30 min), single-use token signed with the shared
  WEBSTORE_API_TOKEN (context "feminine-designer/storefront-admin/v1"),
  signs in the `STOREFRONT_MANAGER_USERNAME` superuser (default "manager",
  created on first use with an unusable password) and opens the admin.
- Billing app: `src/lib/webstore/storefront-admin.ts` mints the token,
  `/storefront-admin` (staff-only via middleware) redirects to the shop; a
  big "Edit storefront" card sits at the top of Online Orders. Shared test
  vector in both test suites. Browser check: `browser-checks/handoff.js`.

## T45 — Full design QA (2026-10-18)

- `browser-checks/qa_design.js`: every customer page at 360/390/768/1024/1440
  for sideways scroll, text escaping or touching its box, clipped/overlapping
  text, contrast, broken images, phone tap targets, JS/HTTP errors;
  `btnwrap.js` for button labels wrapping; `screens.js` phone screen captures.
- Fixed: order tables stack as labelled rows on phones (orders, order
  detail, order success); checkout sideways scroll (phone + tablet gutters);
  eyebrow and WhatsApp-button contrast; image-less category tiles (wine text,
  no muddy overlay); stat boxes; card badges single-line; underline links
  and breadcrumbs alignment; button labels on phones; tap targets ≥ 36px.
- Final run: 0 design issues (only demo-only missing images remain).

## T46 — Surface polish (2026-10-18)

- `femdes-theme.css` T46 layer: category bar as a pressed track with a raised
  active pill (edge fade on phones), sort/density and sign-in tabs as
  segmented controls, newsletter and search as pressed pill fields,
  product-detail/FAQ accordions as one raised panel with +/− chips,
  frosted-glass buttons over hero/editorial photos, dashed "stitch" seam on
  the made-to-measure builder and review price, cart lines on a raised panel.
- Fixed while checking: "Optional details" label spacing in the builder;
  hero scroll cue crossing the button on short desktop screens; cart line
  grid spilling past the panel at 360px and 1024px.
- Layout and flow unchanged (surface treatment only).

## T47 — Product photos (2026-10-18)

- Product page gallery shows the whole photo (`object-fit: contain`); the
  frame takes the first photo's shape (square to 3:4) and is capped to the
  screen height on desktop. Hover zoom removed.
- Tap/click the photo or the expand button: full-screen PhotoSwipe 5.4.4
  viewer (MIT, vendored in `static/store/vendor/photoswipe/`, loaded only
  when first opened) with pinch/double-tap/wheel zoom, swipe, keyboard and
  counter, in the studio cream palette. Closing returns the gallery to the
  photo the customer was on.
- Product cards: 4:5 frame, whole photo shown instead of a crop.

## T48 — Blouse catalogue import (2026-10-18)

- 22 lookbook canvases (2×2: front, back, worn front, worn back) split by
  `catalogue/split_canvas.py` (cuts on the white gutters, trims, squares to
  1080px; full-bleed studio shots are centre-cropped instead of boxed).
- `catalogue/2026-10-blouses/`: photos + `catalogue.json` (names and copy
  written from the photos; ₹2,200, stock 10, Blouses, new arrival,
  SKUs FD-BL-101…122, colour, fabric, care, occasions).
- `python manage.py import_catalogue <folder> [--dry-run]`: validates first,
  creates products + ordered photos (first = primary, alt text per view),
  reuses category/occasions, skips existing slugs and taken SKUs.

## T49 — Home hero photo (2026-10-18)

- Split hero (featured products) showed square photos cropped into a 4:5
  phone frame (straps cut off). Photo now uses `object-fit: contain` and the
  phone frame is square, so the whole blouse shows edge to edge; desktop
  half-column shows the full photo too.

## T50 — Razorpay completed (2026-10-18)

- `store/payments.py`: idempotent `mark_paid` (callback + webhook both safe,
  one "payment received" email), `mark_failed`, `release_unpaid_orders`
  (cancel + restock online orders unpaid after UNPAID_ORDER_RELEASE_MINUTES,
  lazily from checkout/billing API and `manage.py release_unpaid_orders`),
  late payment after auto-cancel revives the order and re-takes stock.
- `POST /razorpay/webhook/` (HMAC-SHA256 of raw body with
  RAZORPAY_WEBHOOK_SECRET; payment.captured / order.paid / payment.failed;
  amount + currency checked).
- Order pages (`order_success`, payment, verify) are private: the placing
  browser (session), the signed-in owner, staff, or a signed `?k=` link
  (used in emails). Strangers get 404.
- Payment page opens Checkout automatically, retry button, failure/dismiss
  messages, 15-min Checkout timeout, WhatsApp help; success page shows
  "Almost there — Pay now" / "Order cancelled"; account orders get Pay now.

## T51 — Real OTP SMS + Google sign-in (2026-10-18)

- `store/sms.py`: `send_otp(to, code, minutes, store)` path for DLT
  providers; `Msg91OtpBackend` (POST control.msg91.com/api/v5/otp with
  template_id/mobile/authkey/otp) and `TwoFactorOtpBackend`; friendly errors,
  failed sends discard the code. Console backend counts as "not live": in
  production the OTP page says mobile sign-in is being set up and offers
  Google/email instead of silently never sending.
- Once a real SMS backend is set, `/accounts/login/` opens the Mobile OTP
  screen (tab first); `?method=email` keeps email login one tap away.
  Register page leads with "Continue with mobile" + Google.
- Google sign-in (`views_google.py`, GIS button partial): ID token verified
  with google-auth (audience, issuer, expiry); links by `CustomerProfile.
  google_sub` (migration 0029), links an existing customer by verified email
  (never staff), else creates a passwordless account; profile page can
  connect Google. Hidden when GOOGLE_CLIENT_ID is empty.

## T52 — Checkout & sign-in quality of life (2026-10-18)

- PIN code autofill: `store/pincode.py` (India Post api.postalpincode.in,
  cached 30 days, state mapped to our dropdown) + `GET /api/pincode/<pin>/`;
  typing a 6-digit PIN fills city and state and shows "Delivering to …";
  PIN field now sits above City/State.
- Guests see "Faster checkout: sign in" on checkout (bag is kept).
- OTP screen: auto-submits at 6 digits, WebOTP autofill on Android Chrome
  (needs the SMS to end with "@<domain> #<code>"); brand-new mobile accounts
  go to "add your name and email".

## T53 — Orders like Amazon/Myntra (2026-10-18)

- Order: courier_name, tracking_number (AWB), tracking_url, expected_delivery,
  shipped/delivered/cancelled timestamps, cancel_reason/cancelled_by
  (migration 0030, backfills a timeline for existing orders). `OrderEvent`
  logs every status change (dated tracking timeline). `OrderRequest`:
  exchange (ready-made, 7 days), free alteration (made to measure, 30 days),
  damaged/missing/wrong (48 h) — per the online-order terms.
- `store/orders.py` + `views_orders.py`: customer cancel before processing
  (reason, restock, refund-due note + emails), request form with item
  checkboxes, Buy again, timeline builder. Staff cancels (admin, billing
  API) also restock.
- Pages: My Orders as cards with photo stack + status headline ("On the way ·
  arriving by…", "Delivered on…") + Track parcel / Pay now; order detail with
  actions, vertical dated timeline + courier/AWB/Track parcel, item rows with
  photos, requests + replies, price details with "You saved"; order
  confirmation and guest Track Order use the same timeline/items/actions.
- Billing API: tracking, timeline, cancellation (refund_due), requests;
  POST accepts courier / tracking_number / tracking_url / expected_delivery.

## T54 — Bag like Myntra/Amazon (2026-10-18)

- Coupons (`Coupon`, `store/coupons.py`, admin with "times used"): percent
  (with cap) or amount off, minimum order, dates, total + per-customer
  limits, first-order-only, offers list in the bag. Code kept in session,
  re-checked on every total and at order time (order stores coupon_code +
  coupon_discount, included in discount_total). Migration 0031 also adds the
  address book (`Address`, seeded from profile addresses) and gift message.
- Bag: checkout steps (Bag → Address → Payment), MRP struck through + % off
  per line, price details (Total MRP / Discount on MRP / Coupon / Delivery /
  Total / You save), coupon box + offers, Save for later (session) with Move
  to bag, Move to wishlist now really moves, sticky mobile Checkout bar,
  trust row, UPI/cards/net banking/wallets line (PayPal logo removed).
- Delivery estimates: `store/delivery.py` + `/api/delivery/<pin>/`; "Deliver
  to" PIN check on the bag and product page (remembers the PIN, prefilled
  from the default address) updates each line's "Delivery by …"; made-to-
  measure dates add the stitching lead time. DELIVERY_DAYS_MIN/MAX settings.

## T55 — Checkout like Amazon (2026-10-18)

- Address book (`Address`, `views_addresses.py`): My Addresses page (add,
  edit, delete, make default — always one default), saved addresses as
  radio cards at checkout (default preselected; "Add a new address" reveals
  the form; new addresses saved with a label unless unticked; a different
  recipient's name/phone go on the shipping label). Someone else's address
  id is ignored.
- Checkout: steps, item photos with MRP, per-line "Delivery by …" from the
  chosen address / typed PIN, coupon box + offers, price details + You save,
  delivery instructions, "This is a gift" message, Place order · ₹total,
  sticky mobile Place order bar, policy link.
- Billing API + app: coupon (code/discount) and gift message; Gift flag in
  the list and a gift card note on the order.

## T56 — Ratings & reviews (2026-10-18)

- `ProductReview` (migration 0032): 1–5 stars, title, text, fit (runs
  small / true / large), optional photo, verified purchase, publish toggle
  (admin list-editable), one review per customer per product (editable).
- Only customers whose order with the piece is delivered can review
  (`store/reviews.py`); "★ Rate & review" on delivered order items.
- Product page: rating chip under the name, Ratings & reviews panel
  (average, 5→1 bars, "Most say it runs small (x%)", review list with
  Verified buyer); product cards show "4.7 ★ (3)" (subquery annotations on
  get_active_products); JSON-LD aggregateRating for Google.

## T57 — Account menu + catalogue photos (2026-10-18)

- Header account icon opens a menu on hover (mouse) or tap (touch/keyboard):
  signed in → greeting, My orders, Track an order, Wishlist (count), Saved
  addresses, Profile, Store admin (staff), Sign out; guests → Sign in /
  Create account, Track an order, Wishlist, Help. Phones get a bottom sheet
  with a dimmed backdrop (tap outside / Esc closes). Green dot = signed in.
- Decorative images now come from the catalogue (`selectors.catalogue_photos`,
  named slots): sign-in/register visuals, home editorial + made-to-measure,
  hero fallback, menu tiles. Categories without an image/cover use their
  newest product's photo. Stock template photos remain only as fallbacks.

## T58 — Admin thumbnails + responsive admin (2026-10-18)

- Product images show real thumbnails: `ImagePreviewWidget`
  (store/templates/admin/widgets/image_preview.html) in the product's image
  rows and the Product images page; Photo column in the product list,
  Image column in the product-images list. Django's "Image for …" caption
  (which overlapped Choose file) is hidden.
- Tablets/phones: change lists and tabular inlines become labelled cards
  (admin-fd.js copies column names into data-labels; two cards per row on
  tablets); filters drop below; form labels stack; save buttons full width.
  Order edit page grouped into Order / Customer / Delivery address / Courier
  & tracking / Payment / Money / Cancellation.
