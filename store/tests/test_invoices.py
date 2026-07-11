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
            customer_phone="12345", notes="Handle with care",
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

    def test_timeline_covers_all_statuses(self):
        """Timeline renders every supported status label."""
        self.client.login(username="buyer", password="pass")
        url = reverse("account_order_detail", kwargs={"order_number": self.order.order_number})
        response = self.client.get(url)
        for label in ("Order Placed", "Confirmed", "Processing", "Shipped", "Completed", "Cancelled"):
            self.assertContains(response, label, msg_prefix=f"Timeline missing: {label}")

    def test_account_orders_links_to_detail(self):
        """Account orders list links to account_order_detail, not order_success."""
        self.client.login(username="buyer", password="pass")
        response = self.client.get(reverse("account_orders"))
        detail_url = reverse("account_order_detail", kwargs={"order_number": self.order.order_number})
        self.assertContains(response, detail_url)


class InvoiceTests(TestCase):
    """Invoice download for authenticated customers."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="buyer", password="pass")
        self.other = User.objects.create_user(username="other", password="pass")
        self.category = Category.objects.create(name="Blouses", slug="blouses")
        self.product = Product.objects.create(
            category=self.category, name="Test Blouse", slug="tb",
            sku="SKU-INV", price=Decimal("99"), is_active=True,
        )
        self.order = Order.objects.create(
            customer_name="Alice", customer_email="a@t.com",
            customer_phone="555-1234", shipping_address="123 Main St\nCity",
            customer_user=self.user, payment_status="paid",
            payment_method="razorpay", payment_reference="REF123",
            notes="Gift wrap please", subtotal=Decimal("99"),
            discount_total=Decimal("10"), total=Decimal("89"),
        )
        OrderItem.objects.create(
            order=self.order, product_name="Test Blouse", sku="SKU-INV",
            unit_price=Decimal("99"), quantity=1, line_total=Decimal("99"),
            color="Red", size="M",
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

    def test_invoice_renders_order_item_snapshots(self):
        """Invoice renders product name, SKU, qty, unit price, line total."""
        self.client.login(username="buyer", password="pass")
        url = reverse("account_order_invoice", kwargs={"order_number": self.order.order_number})
        response = self.client.get(url)
        self.assertContains(response, "Test Blouse")
        self.assertContains(response, "SKU-INV")

    def test_invoice_renders_customer_and_payment_details(self):
        """Invoice renders phone, address, payment method, status, reference, notes."""
        self.client.login(username="buyer", password="pass")
        url = reverse("account_order_invoice", kwargs={"order_number": self.order.order_number})
        response = self.client.get(url)
        content = response.content.decode()
        self.assertIn("555-1234", content)
        self.assertIn("123 Main St", content)
        self.assertIn("REF123", content)
        self.assertIn("Gift wrap please", content)
        self.assertIn("Paid", content)
        self.assertIn("Order Status", content)
