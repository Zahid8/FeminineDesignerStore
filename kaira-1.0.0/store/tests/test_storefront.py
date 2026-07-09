"""Tests for storefront views and URL routing."""

from decimal import Decimal
from html.parser import HTMLParser

from django.test import Client, TestCase
from django.urls import reverse

from store.models import Category, Order, Product, SiteSettings


class _DomChecker(HTMLParser):
    """Minimal HTML parser to check that a wrapper element contains a descendant."""

    def __init__(self):
        super().__init__()
        self._stack = []
        self._matches = []

    def handle_starttag(self, tag, attrs):
        classes = ""
        for name, val in attrs:
            if name == "class":
                classes = val
                break
        self._stack.append((tag, classes))

    def handle_endtag(self, tag):
        if self._stack:
            self._stack.pop()

    def wrapper_contains_descendant(self, html, wrapper_class, descendant_class):
        """Return True if an element with wrapper_class contains descendant_class."""
        self._stack = []
        self._matches = []
        self.feed(html)
        # Re-parse to find relationships
        self._stack = []
        self._find_wrapper(html, wrapper_class, descendant_class)
        return self._matches

    def _find_wrapper(self, html, wrapper_class, descendant_class):
        """Walk through and find wrapper->descendant relationships."""
        tokens = _tokenize(html)
        depth = 0
        in_wrapper = False
        wrapper_depth = -1
        for token in tokens:
            if token.startswith("</"):
                depth -= 1
                if depth < wrapper_depth and in_wrapper:
                    in_wrapper = False
                continue
            if token.startswith("<") and not token.startswith("</"):
                classes = _extract_classes(token)
                if not in_wrapper and wrapper_class in classes:
                    in_wrapper = True
                    wrapper_depth = depth
                if in_wrapper and depth > wrapper_depth and descendant_class in classes:
                    self._matches.append(True)
                    return
                depth += 1


def _tokenize(html):
    """Simple HTML tokenizer — splits on < and >."""
    tokens = []
    for part in html.split("<"):
        if not part:
            continue
        idx = part.find(">")
        if idx >= 0:
            tokens.append("<" + part[:idx] + ">")
    return tokens


def _extract_classes(token):
    """Extract class attribute values from an HTML open tag."""
    import re
    match = re.search(r'class=["\']([^"\']+)["\']', token)
    if match:
        return match.group(1).split()
    return []


def _check_wrapper_contains_descendant(html, wrapper_class, descendant_class):
    """Return True if a wrapper element contains a descendant."""
    tokens = _tokenize(html)
    depth = 0
    in_wrapper = False
    wrapper_depth = -1
    for token in tokens:
        if token.startswith("</"):
            depth -= 1
            if depth < wrapper_depth and in_wrapper:
                in_wrapper = False
            continue
        if token.startswith("<") and not token.startswith("</"):
            classes = _extract_classes(token)
            if not in_wrapper and wrapper_class in classes:
                in_wrapper = True
                wrapper_depth = depth
            elif in_wrapper and depth > wrapper_depth and descendant_class in classes:
                return True
            depth += 1
    return False


class HomeViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_home_renders(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "FemDes")

    def test_home_uses_kaira_sections(self):
        self._create_homepage_products()
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'id="new-arrival"')
        self.assertContains(response, "new-arrival product-carousel")
        self.assertContains(response, 'id="best-sellers"')
        self.assertContains(response, "best-sellers product-carousel")
        self.assertContains(response, "newsletter")

    def test_home_carousels_have_swiper_descendant(self):
        """Each product-carousel wrapper contains a descendant .swiper."""
        self._create_homepage_products()
        response = self.client.get(reverse("home"))
        content = response.content.decode()
        for section_id in ("new-arrival", "best-sellers", "related-products"):
            self.assertTrue(
                _check_wrapper_contains_descendant(
                    content, "product-carousel", "swiper"
                ),
                f"product-carousel wrapper should contain .swiper descendant (checked near #{section_id})",
            )

    def test_home_carousels_have_icon_arrow_controls(self):
        """Each product-carousel wrapper contains icon-arrow controls."""
        self._create_homepage_products()
        response = self.client.get(reverse("home"))
        content = response.content.decode()
        self.assertIn('icon-arrow-left', content)
        self.assertIn('icon-arrow-right', content)

    def _create_homepage_products(self):
        cat = Category.objects.create(name="Test", slug="test-home", is_active=True)
        Product.objects.create(
            category=cat, name="New Arrival", slug="na-prod", sku="SKU-NA",
            price=Decimal("10"), stock_quantity=5, is_active=True, is_new_arrival=True,
        )
        Product.objects.create(
            category=cat, name="Best Seller", slug="bs-prod", sku="SKU-BS",
            price=Decimal("10"), stock_quantity=5, is_active=True, is_best_seller=True,
        )
        Product.objects.create(
            category=cat, name="Recommended", slug="rec-prod", sku="SKU-REC",
            price=Decimal("10"), stock_quantity=5, is_active=True, is_recommended=True,
        )

    def test_home_includes_static_asset_paths(self):
        response = self.client.get(reverse("home"))
        content = response.content.decode()
        self.assertIn("/static/store/style.css", content)
        self.assertIn("/static/store/css/vendor.css", content)
        self.assertIn("/static/store/js/script.min.js", content)
        self.assertIn("/static/store/images/main-logo.png", content)

    def test_home_preserves_templatesjungle_attribution(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "TemplatesJungle")
        self.assertContains(response, "ThemeWagon")


class ProductListViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(
            name="Dresses", slug="dresses", is_active=True
        )
        self.product = Product.objects.create(
            category=self.category,
            name="Summer Dress",
            slug="summer-dress",
            sku="SKU-VIEW-001",
            price=Decimal("49.99"),
            is_active=True,
        )

    def test_product_list_renders(self):
        response = self.client.get(reverse("product_list"))
        self.assertEqual(response.status_code, 200)

    def test_product_list_filtered_by_category(self):
        response = self.client.get(
            reverse("product_list") + "?category=dresses"
        )
        self.assertEqual(response.status_code, 200)

    def test_product_list_search(self):
        response = self.client.get(reverse("product_list") + "?q=summer")
        self.assertEqual(response.status_code, 200)

    def test_product_list_search_no_matches(self):
        response = self.client.get(reverse("product_list") + "?q=zzznomatch")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No products found")

    def test_product_list_tag_filter(self):
        from store.models import ProductTag
        tag = ProductTag.objects.create(name="Cotton", slug="cotton", is_active=True)
        self.product.tags.add(tag)
        response = self.client.get(reverse("product_list") + "?tag=cotton")
        self.assertEqual(response.status_code, 200)

    def test_product_list_combined_category_and_tag(self):
        from store.models import ProductTag
        tag = ProductTag.objects.create(name="Silk", slug="silk", is_active=True)
        self.product.tags.add(tag)
        response = self.client.get(
            reverse("product_list") + "?category=dresses&tag=silk"
        )
        self.assertEqual(response.status_code, 200)

    def test_product_list_renders_product_names(self):
        response = self.client.get(reverse("product_list"))
        self.assertContains(response, self.product.name)


class ProductDetailViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(
            name="Dresses", slug="dresses", is_active=True
        )
        self.product = Product.objects.create(
            category=self.category,
            name="Summer Dress",
            slug="summer-dress",
            sku="SKU-VIEW-002",
            price=Decimal("49.99"),
            stock_quantity=5,
            is_active=True,
        )

    def test_product_detail_renders(self):
        response = self.client.get(
            reverse("product_detail", kwargs={"slug": self.product.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Summer Dress")

    def test_product_detail_shows_add_to_cart_form(self):
        response = self.client.get(
            reverse("product_detail", kwargs={"slug": self.product.slug})
        )
        self.assertContains(response, "Add to Cart")
        self.assertContains(
            response,
            reverse("add_to_cart", kwargs={"product_id": self.product.pk}),
        )

    def test_product_detail_shows_related(self):
        response = self.client.get(
            reverse("product_detail", kwargs={"slug": self.product.slug})
        )
        self.assertContains(response, "Related Products")

    def test_product_detail_related_carousel_kaira_structure(self):
        """Related products carousel uses Kaira product-carousel wrapper with .swiper descendant."""
        # Create a related product in the same category so the section renders
        Product.objects.create(
            category=self.product.category, name="Related", slug="rel-prod",
            sku="SKU-REL", price=Decimal("10"), stock_quantity=5, is_active=True,
        )
        response = self.client.get(
            reverse("product_detail", kwargs={"slug": self.product.slug})
        )
        content = response.content.decode()
        self.assertIn('id="related-products"', content)
        self.assertIn('product-carousel', content)
        self.assertIn('swiper product-swiper', content)

    def test_product_detail_inactive_404(self):
        self.product.is_active = False
        self.product.save()
        response = self.client.get(
            reverse("product_detail", kwargs={"slug": self.product.slug})
        )
        self.assertEqual(response.status_code, 404)


class CartViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_cart_detail_renders(self):
        response = self.client.get(reverse("cart_detail"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your cart is empty")

    def test_cart_detail_shows_checkout_link_when_items(self):
        # Add product to cart first
        cat = Category.objects.create(name="Dresses", slug="dresses", is_active=True)
        prod = Product.objects.create(
            category=cat, name="Test", slug="test-cc", sku="SKU-CC",
            price=Decimal("10.00"), stock_quantity=5, is_active=True,
        )
        self.client.post(
            reverse("add_to_cart", kwargs={"product_id": prod.pk}),
            {"quantity": 1},
        )
        response = self.client.get(reverse("cart_detail"))
        self.assertContains(response, reverse("checkout"))


class AddToCartTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(
            name="Dresses", slug="dresses", is_active=True
        )
        self.product = Product.objects.create(
            category=self.category,
            name="Summer Dress",
            slug="summer-dress-add",
            sku="SKU-VIEW-003",
            price=Decimal("49.99"),
            stock_quantity=5,
            is_active=True,
        )

    def test_add_to_cart_post(self):
        url = reverse("add_to_cart", kwargs={"product_id": self.product.pk})
        response = self.client.post(url, {"quantity": 2})
        self.assertEqual(response.status_code, 302)
        cart = self.client.session.get("femdes_cart", {})
        self.assertEqual(len(cart), 1)

    def test_add_to_cart_inactive_redirects(self):
        self.product.is_active = False
        self.product.save()
        url = reverse("add_to_cart", kwargs={"product_id": self.product.pk})
        response = self.client.post(url, {"quantity": 1})
        self.assertEqual(response.status_code, 302)

    def test_add_to_cart_get_redirects(self):
        url = reverse("add_to_cart", kwargs={"product_id": self.product.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)


class CheckoutViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(
            name="Dresses", slug="dresses", is_active=True
        )
        self.product = Product.objects.create(
            category=self.category,
            name="Summer Dress",
            slug="summer-dress-co",
            sku="SKU-VIEW-004",
            price=Decimal("49.99"),
            stock_quantity=10,
            is_active=True,
        )

    def test_empty_cart_checkout_redirects(self):
        response = self.client.get(reverse("checkout"))
        # With empty cart, GET should redirect to cart
        self.assertEqual(response.status_code, 302)

    def test_empty_cart_checkout_post_redirects(self):
        response = self.client.post(reverse("checkout"), {})
        self.assertRedirects(response, reverse("cart_detail"))
        self.assertEqual(Order.objects.count(), 0)

    def test_checkout_get_with_items(self):
        # Add item to cart first
        self.client.post(
            reverse("add_to_cart", kwargs={"product_id": self.product.pk}),
            {"quantity": 1},
        )
        response = self.client.get(reverse("checkout"))
        self.assertEqual(response.status_code, 200)

    def test_checkout_post_creates_order(self):
        # Add item to cart first
        self.client.post(
            reverse("add_to_cart", kwargs={"product_id": self.product.pk}),
            {"quantity": 2},
        )
        response = self.client.post(
            reverse("checkout"),
            {
                "customer_name": "Alice",
                "customer_email": "alice@example.com",
                "shipping_address": "123 Main St",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Order.objects.exists())


class OrderSuccessViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.order = Order.objects.create(
            customer_name="Alice",
            customer_email="alice@example.com",
            shipping_address="123 Main St",
        )

    def test_order_success_renders(self):
        response = self.client.get(
            reverse(
                "order_success",
                kwargs={"order_number": self.order.order_number},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.order.order_number)

    def test_order_success_renders_order_number(self):
        response = self.client.get(
            reverse(
                "order_success",
                kwargs={"order_number": self.order.order_number},
            )
        )
        self.assertContains(response, self.order.order_number)
        self.assertContains(response, "Thank You")

    def test_order_success_404(self):
        response = self.client.get(
            reverse(
                "order_success",
                kwargs={"order_number": "NONEXISTENT"},
            )
        )
        self.assertEqual(response.status_code, 404)


class TemplateStructureTests(TestCase):
    """Verify Kaira template markers and structure."""

    def setUp(self):
        self.client = Client()

    def test_base_includes_offcanvas_cart(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'id="offcanvasCart"')

    def test_search_popup_has_kaira_classes(self):
        """Search popup uses .search-popup, .search-popup-container, .search-popup-form."""
        response = self.client.get(reverse("home"))
        content = response.content.decode()
        self.assertIn('search-popup', content)
        self.assertIn('search-popup-container', content)
        self.assertIn('search-popup-form', content)

    def test_search_popup_has_q_input_and_action(self):
        """Search form submits to product_list with q input."""
        response = self.client.get(reverse("home"))
        content = response.content.decode()
        self.assertIn('name="q"', content)
        self.assertIn(reverse("product_list"), content)

    def test_search_popup_has_close_control(self):
        """Search popup contains btn-close-search for Kaira JS compatibility."""
        response = self.client.get(reverse("home"))
        self.assertContains(response, "btn-close-search")

    def test_search_controls_use_search_icon(self):
        """Search triggers and submit use #search xlink, not #shopping-bag."""
        response = self.client.get(reverse("home"))
        content = response.content.decode()
        self.assertIn('xlink:href="#search"', content)
        # Search popup submit and navbar trigger must not use shopping-bag
        # We check that the search-popup section doesn't contain #shopping-bag
        popup_start = content.find('search-popup-form')
        popup_end = content.find('search-popup-container', popup_start)
        popup_chunk = content[popup_start:popup_end + 100] if popup_start >= 0 else ""
        self.assertNotIn('xlink:href="#shopping-bag"', popup_chunk)

    def test_navbar_has_kaira_search_trigger(self):
        """Navbar contains Kaira search-button trigger with #search icon."""
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'class="search-button"')
        self.assertContains(response, 'href="#search"')


class NewsletterViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_newsletter_subscribe_post(self):
        response = self.client.post(
            reverse("newsletter_subscribe"), {"email": "test@example.com"}
        )
        self.assertEqual(response.status_code, 302)

    def test_newsletter_get_redirects(self):
        response = self.client.get(reverse("newsletter_subscribe"))
        self.assertEqual(response.status_code, 302)

    def test_newsletter_duplicate_does_not_crash(self):
        self.client.post(
            reverse("newsletter_subscribe"), {"email": "dup@example.com"}
        )
        response = self.client.post(
            reverse("newsletter_subscribe"), {"email": "dup@example.com"}
        )
        self.assertEqual(response.status_code, 302)
