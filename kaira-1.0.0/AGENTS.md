# FemDes/Kaira Agent Guide

This repository is currently a static Kaira fashion-store template that is planned to become a Django-backed FemDes webstore. Agents must treat this as a planning-first conversion until implementation is explicitly requested.

## Current Repository State

- No Git repository is initialized in this directory.
- Existing source is static HTML/CSS/JS:
  - `index.html`: complete one-page storefront template.
  - `style.css`: Kaira custom stylesheet.
  - `css/`: vendor CSS and Swiper CSS.
  - `js/`: jQuery, template plugins, SmoothScroll, and Kaira initialization script.
  - `images/`: current template images and logos.
  - `readme.txt`: upstream template license and credits.
- `implementation_plan.md` is an earlier root-level planning artifact. The canonical agent plan now lives in `docs/agent/IMPLEMENTATION_PLAN.md`.
- `.agent/CONTINUITY.md` is the living workspace continuity file. Read it at the start of each turn.
- `.omx/` is local automation state and must not be treated as product source.

## Required Workflow

1. Read `.agent/CONTINUITY.md` before acting.
2. Inspect relevant source files before making claims.
3. Do not implement the webstore feature unless the user explicitly asks for implementation.
4. Keep changes scoped and reversible. Prefer small patch-style edits.
5. Preserve the Kaira visual conventions unless a task explicitly changes them:
   - Bootstrap 5 layout classes.
   - Jost body font and Marcellus heading font.
   - Existing image filenames and local asset paths during migration.
   - Existing product-card, carousel, search popup, offcanvas cart, and footer styling.
6. Preserve the TemplatesJungle attribution in the footer unless the owner confirms a no-attribution license.
7. Do not delete original static files during planning. During implementation, copy them to `legacy_static/` before moving assets.
8. Keep required changes separate from optional improvements.

## Architecture Direction

The approved planning direction is a Django 5.2 LTS server-rendered application:

- Django admin provides the staff/admin panel.
- SQLite is used for local development.
- PostgreSQL is supported for production through `DATABASE_URL`.
- Product, category, discount, cart, order, newsletter, and site settings behavior are modeled in Django.
- The existing static Kaira template is split into Django templates and partials.
- Existing assets are moved under `static/store/` only during implementation.
- Uploaded product images live under `media/products/`.

## Verification Expectations

Current static repo has no automated test suite or build script. Before implementation, verification is inspection-based:

- `find . -maxdepth 5 -type f | sort`
- `wc -l index.html style.css css/*.css js/*.js readme.txt`
- `rg -n "<section|product-carousel|newsletter|offcanvas|script src" index.html`

After Django implementation begins, each task must run the exact verification listed in `docs/agent/IMPLEMENTATION_PLAN.md` and update `docs/agent/TEST_STATUS.md`.

## Planning Documents

Use these documents as the source of truth:

- `docs/architecture.md`: current and target architecture.
- `docs/decisions.md`: decisions and rationale.
- `docs/agent/IMPLEMENTATION_PLAN.md`: lower-cost-agent execution plan.
- `docs/agent/TASK_BOARD.md`: task status and order.
- `docs/agent/CURRENT_TASK.md`: current next action.
- `docs/agent/HANDOFF.md`: handoff summary.
- `docs/agent/TEST_STATUS.md`: verification status.
