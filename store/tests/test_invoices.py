"""Tests for order detail/tracking and invoice download."""

from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from store.models import Category, Order, OrderItem, Product


class OrderDetailTrackingTests(TestCase):
    """Order detail/tracking page for authenticated customers."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="buyer", password="pass")
        self.other = User.objects.create_user(username="hacker", password="pass")
        self.order = Order.objects.create(
            customer_name="Alice", customer_email="a@t.com",
            shipping_address="Addr", customer_user=self.user,
        )

    def test_order_detail_requires_login(self):
        url = reverse("account_order_detail", kwargs={"order_number": self.order.order_number})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_customer_can_view_own_order(self):
        self.client.login(username="buyer", password="pass")
        url = reverse("account_order_detail", kwargs={"order_number": self.order.order_number})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.order.order_number)

    def test_customer_cannot_view_others_order(self):
        self.client.login(username="hacker", password="pass")
        url = reverse("account_order_detail", kwargs={"order_number": self.order.order_number})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_timeline_covers_statuses(self):
        self.client.login(username="buyer", password="pass")
        url = reverse("account_order_detail", kwargs={"order_number": self.order.order_number})
        response = self.client.get(url)
        self.assertContains(response, "Order Placed")
        self.assertContains(response, "Shipped")


class InvoiceTests(TestCase):
    """Invoice download for authenticated customers."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="buyer", password="pass")
        self.other = User.objects.create_user(username="other", password="pass")
        self.order = Order.objects.create(
            customer_name="Alice", customer_email="a@t.com",
            shipping_address="Addr", customer_user=self.user,
            payment_status="paid", payment_reference="REF123",
        )

    def test_invoice_requires_login(self):
        url = reverse("account_order_invoice", kwargs={"order_number": self.order.order_number})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_customer_can_view_own_invoice(self):
        self.client.login(username="buyer", password="pass")
        url = reverse("account_order_invoice", kwargs={"order_number": self.order.order_number})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.order.order_number)
        self.assertContains(response, "REF123")
        self.assertContains(response, "Invoice")

    def test_customer_cannot_view_others_invoice(self):
        self.client.login(username="other", password="pass")
        url = reverse("account_order_invoice", kwargs={"order_number": self.order.order_number})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_invoice_has_store_identity_and_totals(self):
        self.client.login(username="buyer", password="pass")
        url = reverse("account_order_invoice", kwargs={"order_number": self.order.order_number})
        response = self.client.get(url)
        content = response.content.decode()
        self.assertIn("Invoice", content)
        self.assertIn(self.order.order_number, content)
        self.assertIn("Bill To", content)
        self.assertIn("Total", content)
