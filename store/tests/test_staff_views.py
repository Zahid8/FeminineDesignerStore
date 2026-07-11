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
        self.urls = [
            "staff_dashboard", "staff_order_list", "staff_customer_list",
        ]

    def test_anonymous_redirected(self):
        for name in self.urls:
            with self.subTest(url=name):
                response = self.client.get(reverse(name))
                self.assertIn(response.status_code, (302, 403))

    def test_non_staff_rejected(self):
        User.objects.create_user(username="normal", password="pass")
        self.client.login(username="normal", password="pass")
        for name in self.urls:
            with self.subTest(url=name):
                response = self.client.get(reverse(name))
                self.assertIn(response.status_code, (302, 403))


class StaffDashboardTests(TestCase):
    """Staff dashboard renders correct counts."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(username="admin", password="pass")
        self.client.login(username="admin", password="pass")
        self.cat = Category.objects.create(name="Blouses", slug="blouses")
        Product.objects.create(
            category=self.cat, name="P", slug="p", sku="SKU", price=50, is_active=True,
        )
        Order.objects.create(customer_name="A", customer_email="a@t.com", shipping_address="A")

    def test_dashboard_renders(self):
        response = self.client.get(reverse("staff_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Staff Dashboard")

    def test_dashboard_has_counts(self):
        response = self.client.get(reverse("staff_dashboard"))
        self.assertContains(response, ">1<")  # order count
        self.assertContains(response, ">1<")  # product count


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
