"""Tests for storefront views and URL routing."""

from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from store.models import Category, Order, Product, SiteSettings


class HomeViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_home_renders(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "FemDes")


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

    def test_order_success_404(self):
        response = self.client.get(
            reverse(
                "order_success",
                kwargs={"order_number": "NONEXISTENT"},
            )
        )
        self.assertEqual(response.status_code, 404)


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
