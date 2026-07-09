"""Tests for customer account registration, login, logout, and order history."""

from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from store.models import Category, Order, Product


class RegistrationTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_register_page_renders(self):
        response = self.client.get(reverse("account_register"))
        self.assertEqual(response.status_code, 200)

    def test_register_creates_user_and_redirects(self):
        response = self.client.post(reverse("account_register"), {
            "username": "newuser",
            "email": "new@example.com",
            "password1": "TestPass123!",
            "password2": "TestPass123!",
        })
        self.assertRedirects(response, reverse("account_profile"))
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_register_duplicate_email_rejected(self):
        User.objects.create_user(username="existing", email="dup@example.com", password="pass")
        response = self.client.post(reverse("account_register"), {
            "username": "another",
            "email": "dup@example.com",
            "password1": "TestPass123!",
            "password2": "TestPass123!",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="another").exists())

    def test_register_authenticated_redirects(self):
        User.objects.create_user(username="logged", password="pass")
        self.client.login(username="logged", password="pass")
        response = self.client.get(reverse("account_register"))
        self.assertRedirects(response, reverse("account_profile"))


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )

    def test_login_page_renders(self):
        response = self.client.get(reverse("account_login"))
        self.assertEqual(response.status_code, 200)

    def test_login_with_valid_credentials(self):
        response = self.client.post(reverse("account_login"), {
            "username": "testuser",
            "password": "TestPass123!",
        })
        self.assertRedirects(response, reverse("account_profile"))

    def test_login_with_invalid_credentials(self):
        response = self.client.post(reverse("account_login"), {
            "username": "testuser",
            "password": "wrong",
        })
        self.assertEqual(response.status_code, 200)

    def test_logout(self):
        self.client.login(username="testuser", password="TestPass123!")
        response = self.client.post(reverse("account_logout"))
        self.assertRedirects(response, reverse("home"))

    def test_profile_requires_login(self):
        response = self.client.get(reverse("account_profile"))
        self.assertEqual(response.status_code, 302)

    def test_orders_requires_login(self):
        response = self.client.get(reverse("account_orders"))
        self.assertEqual(response.status_code, 302)


class AuthenticatedCheckoutTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="buyer", email="buyer@example.com", password="TestPass123!"
        )
        self.category = Category.objects.create(name="Blouses", slug="blouses")
        self.product = Product.objects.create(
            category=self.category, name="Test Blouse", slug="test-bl",
            sku="SKU-ACC-001", price=Decimal("70"), stock_quantity=10,
        )

    def test_authenticated_checkout_links_order(self):
        self.client.login(username="buyer", password="TestPass123!")
        # Add to cart
        self.client.post(
            reverse("add_to_cart", kwargs={"product_id": self.product.pk}),
            {"quantity": 1},
        )
        # Checkout
        response = self.client.post(reverse("checkout"), {
            "customer_name": "Buyer",
            "customer_email": "buyer@example.com",
            "shipping_address": "123 St",
        })
        self.assertEqual(response.status_code, 302)
        order = Order.objects.first()
        self.assertEqual(order.customer_user, self.user)

    def test_guest_checkout_preserved(self):
        # Add to cart without login
        self.client.post(
            reverse("add_to_cart", kwargs={"product_id": self.product.pk}),
            {"quantity": 1},
        )
        response = self.client.post(reverse("checkout"), {
            "customer_name": "Guest",
            "customer_email": "guest@example.com",
            "shipping_address": "456 Ave",
        })
        self.assertEqual(response.status_code, 302)
        order = Order.objects.first()
        self.assertIsNone(order.customer_user)

    def test_order_history_scoped_to_user(self):
        # Create an order for buyer
        order_a = Order.objects.create(
            customer_name="Buyer", customer_email="buyer@example.com",
            shipping_address="A", customer_user=self.user,
        )
        # Create an order for another user
        other = User.objects.create_user(username="other", password="pass")
        Order.objects.create(
            customer_name="Other", customer_email="other@example.com",
            shipping_address="B", customer_user=other,
        )
        self.client.login(username="buyer", password="TestPass123!")
        response = self.client.get(reverse("account_orders"))
        self.assertContains(response, order_a.order_number)
        self.assertNotContains(response, "Other")
