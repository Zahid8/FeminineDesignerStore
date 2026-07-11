"""Tests for staff dashboard, order list/update, and customer list."""

from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from store.models import Category, CustomerProfile, Order, Product


class StaffDashboardAccessTests(TestCase):
    """Staff views reject anonymous and non-staff users."""

    def setUp(self):
        self.client = Client()
        self.order = Order.objects.create(customer_name="A", customer_email="a@t.com", shipping_address="A")
        self.static_urls = [
            "staff_dashboard", "staff_order_list", "staff_customer_list",
        ]

    def test_anonymous_redirected(self):
        for name in self.static_urls:
            with self.subTest(url=name):
                response = self.client.get(reverse(name))
                self.assertIn(response.status_code, (302, 403))
        # staff_order_update with a real order
        url = reverse("staff_order_update", kwargs={"order_number": self.order.order_number})
        response = self.client.get(url)
        self.assertIn(response.status_code, (302, 403))

    def test_non_staff_rejected(self):
        User.objects.create_user(username="normal", password="pass")
        self.client.login(username="normal", password="pass")
        for name in self.static_urls:
            with self.subTest(url=name):
                response = self.client.get(reverse(name))
                self.assertIn(response.status_code, (302, 403))
        url = reverse("staff_order_update", kwargs={"order_number": self.order.order_number})
        response = self.client.get(url)
        self.assertIn(response.status_code, (302, 403))


class StaffDashboardTests(TestCase):
    """Staff dashboard renders correct counts with distinct values."""

    def setUp(self):
        self.client = Client()
        self.staff = User.objects.create_user(username="admin", password="pass", is_staff=True)
        # Create non-staff customers
        User.objects.create_user(username="cust1", password="pass")
        User.objects.create_user(username="cust2", password="pass")
        self.client.login(username="admin", password="pass")
        self.cat = Category.objects.create(name="Blouses", slug="blouses")
        Product.objects.create(category=self.cat, name="P", slug="p", sku="SKU1", price=50, is_active=True)
        Product.objects.create(category=self.cat, name="Inactive", slug="i", sku="SKU2", price=50, is_active=False)
        Order.objects.create(customer_name="A", customer_email="a@t.com", shipping_address="A", payment_status="paid")
        Order.objects.create(customer_name="B", customer_email="b@t.com", shipping_address="B", payment_status="pending")

    def test_dashboard_renders(self):
        response = self.client.get(reverse("staff_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Staff Dashboard")

    def test_dashboard_has_distinct_counts(self):
        """Each metric card binds its label to the correct value."""
        response = self.client.get(reverse("staff_dashboard"))
        content = response.content.decode()

        import re

        def _metric_value(label, content):
            """Find a dashboard metric value near its label. Returns the number."""
            # Pattern: <div class="fs-3 fw-bold">VALUE</div><small ...>LABEL</small>
            pattern = rf'<div class="fs-3 fw-bold">(\d+)</div>\s*<small class="text-muted">{label}</small>'
            match = re.search(pattern, content)
            if not match:
                return None
            return int(match.group(1))

        self.assertEqual(_metric_value("Customers", content), 2,
                         "Customer count should be 2 (excludes staff)")
        self.assertEqual(_metric_value("Active Products", content), 1,
                         "Active product count should be 1 (excludes inactive)")
        self.assertEqual(_metric_value("Paid", content), 1,
                         "Paid count should be 1")
        self.assertEqual(_metric_value("Non-Paid", content), 1,
                         "Non-paid count should be 1")
        self.assertIsNotNone(_metric_value("Total Orders", content),
                             "Total Orders label missing")
        self.assertIn("Non-Paid", content)


class StaffOrderUpdateTests(TestCase):
    """Staff can update order status without changing payment."""

    def setUp(self):
        self.client = Client()
        self.staff = User.objects.create_user(username="staff", password="pass", is_staff=True)
        self.client.login(username="staff", password="pass")
        self.order = Order.objects.create(
            customer_name="A", customer_email="a@t.com", shipping_address="A",
            payment_status="paid",
        )

    def test_valid_status_update(self):
        url = reverse("staff_order_update", kwargs={"order_number": self.order.order_number})
        response = self.client.post(url, {"status": "shipped"})
        self.assertRedirects(response, reverse("staff_order_list"))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "shipped")

    def test_valid_update_preserves_payment_status(self):
        url = reverse("staff_order_update", kwargs={"order_number": self.order.order_number})
        self.client.post(url, {"status": "completed"})
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "paid")

    def test_invalid_status_rejected(self):
        url = reverse("staff_order_update", kwargs={"order_number": self.order.order_number})
        self.client.post(url, {"status": "bogus"})
        self.order.refresh_from_db()
        self.assertNotEqual(self.order.status, "bogus")


class StaffCustomerListTests(TestCase):
    """Staff customer list shows users and profiles."""

    def setUp(self):
        self.client = Client()
        self.staff = User.objects.create_user(username="staff", password="pass", is_staff=True)
        self.client.login(username="staff", password="pass")
        self.user = User.objects.create_user(username="customer1", password="pass")
        CustomerProfile.objects.create(user=self.user, phone="555")

    def test_customer_list_renders(self):
        response = self.client.get(reverse("staff_customer_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "customer1")
        self.assertContains(response, "555")

    def test_customer_list_has_admin_links(self):
        response = self.client.get(reverse("staff_customer_list"))
        self.assertContains(response, reverse("admin:auth_user_change", args=[self.user.pk]))
        self.assertContains(response, reverse("admin:store_customerprofile_change", args=[self.user.profile.pk]))
