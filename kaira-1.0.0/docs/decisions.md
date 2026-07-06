# Decisions

## 2026-07-06: Use Django 5.2 LTS For The Webstore

**Status:** Accepted.

**Decision:** Convert the static Kaira template into a Django 5.2 LTS server-rendered application.

**Rationale:**

- The existing template is already server-renderable HTML.
- Django provides a secure, mature admin panel without building a custom admin UI.
- Django models and migrations fit the requested database-backed product, price, stock, and discount management.
- Server-rendered templates preserve the current Bootstrap/Kaira frontend with less risk than a SPA rewrite.

**Required consequences:**

- Add `requirements.txt`, `manage.py`, `femdes_site/`, and `store/`.
- Move static assets under `static/store/` during implementation.
- Split `index.html` into templates and partials.
- Add Django tests as functionality is introduced.

**Optional consequences:**

- Add PostgreSQL for production.
- Add Stripe or PayPal later.

## 2026-07-06: Use Django Admin As The First Admin Panel

**Status:** Accepted.

**Decision:** Use Django admin for product/category/discount/order/newsletter/site-settings management.

**Rationale:**

- The user requested an admin panel, not a custom-branded admin experience.
- Django admin is lower-risk and faster for CRUD-heavy store management.
- A lower-cost implementation agent can complete this reliably with tests.

**Required consequences:**

- Register all store models in `store/admin.py`.
- Configure list displays, filters, search fields, inlines, readonly order totals, and slug prepopulation.
- Restrict admin to staff/superusers through Django's built-in auth.

**Optional consequences:**

- Later replace or supplement Django admin with a custom staff dashboard.

## 2026-07-06: Keep Checkout Manual In MVP

**Status:** Accepted.

**Decision:** MVP checkout creates orders for manual fulfillment and does not collect payment card data.

**Rationale:**

- Payment gateways add compliance, secrets, webhook, and deployment complexity.
- The core requested workflow is product/price/discount admin management.
- Manual orders make the first system useful while keeping security risk low.

**Required consequences:**

- Checkout form collects customer name, email, phone, shipping address, and notes.
- Order and order item records snapshot prices and selected options.
- No card fields are rendered or stored.

**Optional consequences:**

- Add Stripe Checkout or PayPal in a later phase.

## 2026-07-06: Preserve Existing Kaira Visual System

**Status:** Accepted.

**Decision:** Preserve existing Kaira CSS classes, fonts, image behavior, carousel behavior, and overall layout while replacing hard-coded content with dynamic data.

**Rationale:**

- The current template is the visual baseline.
- Reusing existing markup and CSS reduces scope and regression risk.
- User history for nearby frontend work favors preserving fonts, local assets, and filenames unless explicitly asked otherwise.

**Required consequences:**

- Do not redesign the frontend during MVP.
- Keep Bootstrap classes and Kaira product-card markup where possible.
- Preserve current asset filenames during migration.

**Optional consequences:**

- Apply brand polish after the database-backed workflow is working.

## 2026-07-06: Preserve Upstream Attribution

**Status:** Accepted.

**Decision:** Keep the TemplatesJungle/ThemeWagon footer attribution unless the owner confirms a no-attribution license.

**Rationale:**

- `readme.txt` states attribution is required for the free template.
- Removing it would create avoidable licensing risk.

**Required consequences:**

- Keep attribution in footer templates.
- Preserve `readme.txt`, preferably under `legacy_static/` after migration.

## 2026-07-06: No Feature Implementation During Documentation Pass

**Status:** Accepted.

**Decision:** This pass only creates planning and handoff documents.

**Rationale:**

- The user explicitly requested architecture/planning docs and said not to implement the feature yet.

**Required consequences:**

- Do not create Django project files in this pass.
- Do not move current `css/`, `js/`, `images/`, `style.css`, or `index.html`.
- Do not create database models yet.
