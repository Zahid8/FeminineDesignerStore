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

    def test_login_safe_next_redirect(self):
        response = self.client.post(
            reverse("account_login") + "?next=/cart/",
            {"username": "testuser", "password": "TestPass123!"},
        )
        self.assertRedirects(response, "/cart/")

    def test_login_ignores_external_next(self):
        response = self.client.post(
            reverse("account_login") + "?next=https://evil.example/path",
            {"username": "testuser", "password": "TestPass123!"},
        )
        self.assertRedirects(response, reverse("account_profile"))

    def test_login_no_next_redirects_to_profile(self):
        response = self.client.post(reverse("account_login"), {
            "username": "testuser", "password": "TestPass123!",
        })
        self.assertRedirects(response, reverse("account_profile"))


class NavbarAuthStateTests(TestCase):
    """Navbar renders correctly for anonymous and authenticated users."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="navuser", password="TestPass123!"
        )

    def test_anonymous_navbar_shows_login_register(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Login")
        self.assertContains(response, "Register")

    def test_authenticated_navbar_shows_account_orders_logout(self):
        self.client.login(username="navuser", password="TestPass123!")
        response = self.client.get(reverse("home"))
        content = response.content.decode()
        self.assertIn("Account", content)
        self.assertIn("Orders", content)
        self.assertIn('action="/accounts/logout/"', content)
        self.assertNotIn('href="/accounts/login/"', content)
        self.assertNotIn('href="/accounts/register/"', content)


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


class CustomerProfileTests(TestCase):
    """CustomerProfile model, views, and admin."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="profileuser", email="profile@test.com", password="Pass123!"
        )

    def test_profile_created_on_edit_page_access(self):
        from store.models import CustomerProfile
        self.client.login(username="profileuser", password="Pass123!")
        self.client.get(reverse("account_profile_edit"))
        self.assertTrue(CustomerProfile.objects.filter(user=self.user).exists())

    def test_profile_edit_page_renders(self):
        self.client.login(username="profileuser", password="Pass123!")
        response = self.client.get(reverse("account_profile_edit"))
        self.assertEqual(response.status_code, 200)

    def test_profile_edit_post_updates_fields(self):
        from store.models import CustomerProfile
        self.client.login(username="profileuser", password="Pass123!")
        response = self.client.post(reverse("account_profile_edit"), {
            "first_name": "Jane", "last_name": "Doe",
            "email": "jane@test.com", "phone": "1234567890",
            "shipping_address": "456 Oak St",
        })
        self.assertRedirects(response, reverse("account_profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Jane")
        self.assertEqual(self.user.email, "jane@test.com")
        profile = CustomerProfile.objects.get(user=self.user)
        self.assertEqual(profile.phone, "1234567890")

    def test_checkout_prefill_for_authenticated_user(self):
        from store.models import Category, CustomerProfile, Product
        self.client.login(username="profileuser", password="Pass123!")
        CustomerProfile.objects.create(
            user=self.user, phone="999", shipping_address="Home"
        )
        self.user.first_name = "Alice"
        self.user.save()
        cat = Category.objects.create(name="Blouses", slug="blouses", is_active=True)
        p = Product.objects.create(
            category=cat, name="Blouse", slug="blouse", sku="SKU-PRE",
            price=Decimal("50"), stock_quantity=5, is_active=True,
        )
        self.client.post(
            reverse("add_to_cart", kwargs={"product_id": p.pk}), {"quantity": 1}
        )
        response = self.client.get(reverse("checkout"))
        self.assertContains(response, 'value="999"')
        self.assertContains(response, "Home")

    def test_guest_checkout_unchanged(self):
        from store.models import Category, Product
        cat = Category.objects.create(name="Blouses", slug="blouses", is_active=True)
        p = Product.objects.create(
            category=cat, name="Blouse", slug="blouse-g", sku="SKU-GP",
            price=Decimal("50"), stock_quantity=5, is_active=True,
        )
        self.client.post(
            reverse("add_to_cart", kwargs={"product_id": p.pk}), {"quantity": 1}
        )
        response = self.client.get(reverse("checkout"))
        self.assertEqual(response.status_code, 200)


class ProfileValidationTests(TestCase):
    """Profile creation at registration, email uniqueness, auth gating."""

    def setUp(self):
        self.client = Client()

    def test_registration_creates_profile(self):
        from store.models import CustomerProfile
        self.client.post(reverse("account_register"), {
            "username": "withprofile", "email": "wp@test.com",
            "password1": "TestPass123!", "password2": "TestPass123!",
        })
        user = User.objects.get(username="withprofile")
        self.assertTrue(CustomerProfile.objects.filter(user=user).exists())

    def test_profile_edit_rejects_duplicate_email(self):
        User.objects.create_user(username="other", email="dup@test.com", password="p")
        u = User.objects.create_user(username="me", email="me@test.com", password="p")
        self.client.login(username="me", password="p")
        response = self.client.post(reverse("account_profile_edit"), {
            "first_name": "", "last_name": "",
            "email": "dup@test.com",
            "phone": "", "shipping_address": "",
        })
        self.assertEqual(response.status_code, 200)
        u.refresh_from_db()
        self.assertEqual(u.email, "me@test.com")  # unchanged

    def test_profile_edit_allows_own_email(self):
        u = User.objects.create_user(username="self", email="s@test.com", password="p")
        self.client.login(username="self", password="p")
        response = self.client.post(reverse("account_profile_edit"), {
            "first_name": "", "last_name": "",
            "email": "s@test.com",
            "phone": "", "shipping_address": "",
        })
        self.assertRedirects(response, reverse("account_profile"))
        u.refresh_from_db()
        self.assertEqual(u.email, "s@test.com")

    def test_profile_edit_requires_login(self):
        response = self.client.get(reverse("account_profile_edit"))
        self.assertEqual(response.status_code, 302)
