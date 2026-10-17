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
