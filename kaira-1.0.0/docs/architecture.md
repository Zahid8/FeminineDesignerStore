# Architecture

## Repository Snapshot

This repository currently contains a static HTML/CSS/JS fashion-store template named Kaira. It has not yet been converted into an application.

Current top-level source:

- `index.html`: one-page storefront template with all content hard-coded.
- `style.css`: custom Kaira theme CSS.
- `css/`: vendor CSS files.
- `js/`: vendor and template JavaScript files.
- `images/`: local template image assets.
- `readme.txt`: upstream template license and credits.
- `implementation_plan.md`: earlier high-detail plan for Django conversion.
- `AGENTS.md`, `CLAUDE.md`, `docs/`: planning and agent coordination docs.

There is no current:

- `package.json`
- Python project
- backend app
- database configuration
- automated test suite
- build script
- Git repository metadata

## Static Template Layout

`index.html` contains the following major regions:

- SVG icon sprite.
- Search popup.
- Cart offcanvas with sample hard-coded grocery-like rows.
- Bootstrap navbar and mobile offcanvas menu.
- Hero/billboard carousel.
- Feature blocks.
- Category image blocks.
- New arrivals product carousel.
- Collection feature block.
- Best sellers product carousel.
- Video block.
- Testimonials carousel.
- Recommended products carousel.
- Blog preview cards.
- Logo bar.
- Newsletter form.
- Instagram image strip.
- Footer with social links, shipping/payment logos, and upstream attribution.

`style.css` defines:

- Jost body font and Marcellus heading font.
- Bootstrap CSS variable overrides.
- Kaira color palette and dark-theme hooks.
- Preloader, search popup, Swiper arrows, image zoom, product card, link hover, single-product, filter, and responsive styles.

`js/script.min.js` initializes:

- Swiper instances for hero, product carousels, testimonials, reviews, and product-detail thumbnails.
- Quantity stepper behavior for `.product-qty`.
- Jarallax.
- Text splitting for `.txt-fx`.
- Search popup open/close behavior.
- Isotope filtering for `.grid` if present.
- Image zoom behavior.
- Colorbox YouTube popup.
- AOS animations.
- HC Sticky for single-product info if present.

## Target Architecture

The target architecture is a Django 5.2 LTS server-rendered webstore.

Key components:

- `femdes_site/`: Django project configuration.
- `store/`: Django app containing models, admin, forms, selectors, services, views, URLs, seed command, and tests.
- `templates/`: Django templates split from the static `index.html`.
- `static/store/`: migrated Kaira CSS, JS, and image assets.
- `media/products/`: uploaded product images.
- SQLite for local development.
- PostgreSQL for production through `DATABASE_URL`.
- WhiteNoise for production static file serving.
- Django admin at `/admin/` as the staff panel.

## Data Flow

Public storefront flow:

1. Customer requests `/`, `/shop/`, or `/products/<slug>/`.
2. Django view calls selector functions for active products, categories, and applicable homepage groups.
3. Template renders Kaira-compatible markup using database-backed objects.
4. Customer submits add-to-cart form.
5. Cart service validates product active status and stock, then stores cart data in session.
6. Cart offcanvas and cart page render from the cart context processor/service.
7. Customer submits checkout form.
8. Checkout service revalidates stock in a transaction, creates an order, creates order item snapshots, decrements stock, and clears the session cart.

Admin flow:

1. Staff logs into Django admin.
2. Staff manages categories, products, product images, discounts, orders, newsletter subscribers, and site settings.
3. Storefront immediately reflects active product/category/discount changes.

## Model Boundary

Required models:

- `SiteSettings`: one-row store settings and contact/social data.
- `Category`: active product group with optional image.
- `Product`: catalog item, price, stock, flags, variants, and descriptions.
- `ProductImage`: one or more images per product.
- `Discount`: global/category/product discount rules.
- `NewsletterSubscriber`: newsletter signup records.
- `Order`: checkout record and totals snapshot.
- `OrderItem`: product line snapshots.

## Service Boundary

Business logic should live in `store/services.py`, not templates:

- Session cart mutation.
- Cart totals.
- Checkout/order creation.
- Stock validation.
- Newsletter subscription.

Query composition should live in `store/selectors.py`:

- Active categories.
- Active products.
- Homepage product groups.
- Product list filtering and sorting.
- Product lookup by slug.

## Template Boundary

Kaira HTML should be split into reusable templates:

- `templates/base.html`
- `templates/store/home.html`
- `templates/store/product_list.html`
- `templates/store/product_detail.html`
- `templates/store/cart.html`
- `templates/store/checkout.html`
- `templates/store/order_success.html`
- `templates/store/partials/icons.html`
- `templates/store/partials/navbar.html`
- `templates/store/partials/search_popup.html`
- `templates/store/partials/cart_offcanvas.html`
- `templates/store/partials/product_card.html`
- `templates/store/partials/category_card.html`
- `templates/store/partials/footer.html`

## Required vs Optional

Required for MVP:

- Django scaffold.
- Asset migration to `static/store/`.
- Database models.
- Admin CRUD.
- Homepage, shop, detail, cart, checkout, order success.
- Discounts.
- Newsletter capture.
- Tests for models, discounts, cart, admin access, storefront views, and checkout.

Optional after MVP:

- Payment gateway.
- Customer accounts.
- Persistent wishlist.
- Shipping carrier APIs.
- Tax calculation.
- Blog CMS.
- Instagram API integration.
- Image optimization pipeline.

## License Constraint

`readme.txt` says the template is free for personal/commercial use as long as the TemplatesJungle credit link remains in the footer. The implementation must preserve that attribution unless the owner confirms a no-attribution license.
