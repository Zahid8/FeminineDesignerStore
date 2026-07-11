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
        self.detail_url = reverse(
            "account_order_detail",
            kwargs={"order_number": self.order.order_number},
        )

    def test_order_detail_requires_login(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 302)

    def test_customer_can_view_own_order(self):
        self.client.login(username="buyer", password="pass")
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.order.order_number)

    def test_customer_cannot_view_others_order(self):
        self.client.login(username="hacker", password="pass")
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 404)

    def test_timeline_covers_all_statuses(self):
        """Timeline renders every supported status label."""
        self.client.login(username="buyer", password="pass")
        response = self.client.get(self.detail_url)
        for label in ("Order Placed", "Confirmed", "Processing", "Shipped", "Completed", "Cancelled"):
            self.assertContains(response, label, msg_prefix=f"Timeline missing: {label}")

    def test_account_orders_links_to_detail(self):
        """Account orders list links to account_order_detail, not order_success."""
        self.client.login(username="buyer", password="pass")
        response = self.client.get(reverse("account_orders"))
        self.assertContains(response, reverse("account_order_detail",
                            kwargs={"order_number": self.order.order_number}))


class TimelineActiveStatusTests(TestCase):
    """Every Order.STATUS_CHOICES value can be the active/current status."""

    TIMELINE_LABELS = {
        "pending": "Order Placed",
        "confirmed": "Confirmed",
        "processing": "Processing",
        "shipped": "Shipped",
        "completed": "Completed",
        "cancelled": "Cancelled",
    }

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="buyer", password="pass")

    def test_each_status_is_active(self):
        """For each status value the matching badge is active (bg-dark)
        and non-current badges are inactive (bg-light text-muted)."""
        self.client.login(username="buyer", password="pass")
        for status_val, _ in Order.STATUS_CHOICES:
            order = Order.objects.create(
                customer_name="A", customer_email="a@t.com",
                shipping_address="Addr", customer_user=self.user,
                status=status_val,
            )
            url = reverse("account_order_detail",
                          kwargs={"order_number": order.order_number})
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200,
                             msg=f"Detail failed for status={status_val}")
            content = response.content.decode()

            for tv, tl in self.TIMELINE_LABELS.items():
                if tv == status_val:
                    # The active badge must have bg-dark, not bg-light
                    self.assertIn(
                        f'bg-dark rounded-pill px-3 py-2">{tl}</span>',
                        content,
                        msg=f"Active status '{tl}' should have bg-dark badge",
                    )
                else:
                    # Non-current badges must have bg-light text-muted
                    self.assertIn(
                        f'bg-light text-muted rounded-pill px-3 py-2">{tl}</span>',
                        content,
                        msg=f"Inactive status '{tl}' should have bg-light text-muted badge",
                    )
            order.delete()


class InvoiceTests(TestCase):
    """Invoice download for authenticated customers."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="buyer", password="pass")
        self.other = User.objects.create_user(username="other", password="pass")
        self.category = Category.objects.create(name="Blouses", slug="blouses")
        Product.objects.create(
            category=self.category, name="Test Blouse", slug="tb",
            sku="SKU-INV", price=Decimal("150"), is_active=True,
        )
        self.order = Order.objects.create(
            customer_name="Alice Johnson", customer_email="alice@example.com",
            customer_phone="555-123-4567",
            shipping_address="123 Main St\nApt 4B\nNew York, NY 10001",
            customer_user=self.user, payment_status="paid",
            payment_method="razorpay", payment_reference="PAY-REF-789",
            notes="Gift wrap please, handle with care",
            subtotal=Decimal("246.90"),
            discount_total=Decimal("10.00"),
            total=Decimal("236.90"),
        )
        OrderItem.objects.create(
            order=self.order, product_name="Test Blouse", sku="SKU-INV",
            unit_price=Decimal("123.45"), quantity=2,
            line_total=Decimal("246.90"),
            color="Red", size="M",
        )
        self.invoice_url = reverse(
            "account_order_invoice",
            kwargs={"order_number": self.order.order_number},
        )
        self.detail_url = reverse(
            "account_order_detail",
            kwargs={"order_number": self.order.order_number},
        )

    def _get_invoice_content(self):
        """Helper: login, GET invoice, return decoded content."""
        self.client.login(username="buyer", password="pass")
        response = self.client.get(self.invoice_url)
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_invoice_requires_login(self):
        response = self.client.get(self.invoice_url)
        self.assertEqual(response.status_code, 302)

    def test_customer_can_view_own_invoice(self):
        self.client.login(username="buyer", password="pass")
        response = self.client.get(self.invoice_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.order.order_number)
        self.assertContains(response, "PAY-REF-789")
        self.assertContains(response, "Invoice")

    def test_customer_cannot_view_others_invoice(self):
        self.client.login(username="other", password="pass")
        response = self.client.get(self.invoice_url)
        self.assertEqual(response.status_code, 404)

    def test_invoice_has_store_identity_and_totals_section(self):
        """Invoice renders the header, Bill To area, totals section, and order number."""
        content = self._get_invoice_content()
        self.assertIn("Invoice", content)
        self.assertIn(self.order.order_number, content)
        self.assertIn("Bill To", content)
        self.assertIn("Total", content)
        self.assertIn("Order Status", content)

    def test_invoice_renders_order_item_snapshots(self):
        """Invoice renders product name, SKU, qty, unit price, line total, variants as table cells."""
        self.client.login(username="buyer", password="pass")
        response = self.client.get(self.invoice_url)
        # Product identity and variants
        self.assertContains(response, "Test Blouse")
        self.assertContains(response, "SKU-INV")
        self.assertContains(response, "Red")
        self.assertContains(response, "M")
        # Table-cell specific assertions — failing if cells are dropped
        self.assertContains(response, "<td>2</td>", html=True)
        self.assertContains(response, "<td>$123.45</td>", html=True)
        self.assertContains(response, "<td>$246.90</td>", html=True)

    def test_invoice_renders_customer_and_payment_details(self):
        """Invoice renders phone, address, payment method, status, reference, notes."""
        content = self._get_invoice_content()
        self.assertIn("555-123-4567", content)
        self.assertIn("123 Main St", content)
        self.assertIn("PAY-REF-789", content)
        self.assertIn("Gift wrap please, handle with care", content)
        self.assertIn("Paid", content)
        self.assertIn("Razorpay", content)

    def test_invoice_totals_use_distinct_values(self):
        """Subtotal, discount, and total each appear in their labelled row.

        Using distinct values so that removing any totals row fails a test.
        """
        content = self._get_invoice_content()
        # Subtotal row
        self.assertIn("Subtotal:</span> <strong>$246.90</strong>", content)
        # Discount row (with leading minus sign)
        self.assertIn("Discount:</span> <strong>-$10.00</strong>", content)
        # Total row (fs-5 class distinguishes it)
        self.assertIn("Total:</span> <strong>$236.90</strong>", content)

    def test_invoice_item_variants_render(self):
        """Invoice renders color and size variant details when present."""
        content = self._get_invoice_content()
        self.assertIn("Red", content)
        self.assertIn("M", content)

    def test_invoice_variant_color_only(self):
        """Invoice item renders color when size is absent."""
        OrderItem.objects.create(
            order=self.order, product_name="ColorOnly", sku="SKU-COL",
            unit_price=Decimal("50"), quantity=1, line_total=Decimal("50"),
            color="Blue", size="",
        )
        content = self._get_invoice_content()
        self.assertIn("Blue", content)

    def test_invoice_variant_size_only(self):
        """Invoice item renders size when color is absent."""
        OrderItem.objects.create(
            order=self.order, product_name="SizeOnly", sku="SKU-SZ",
            unit_price=Decimal("50"), quantity=1, line_total=Decimal("50"),
            color="", size="L",
        )
        content = self._get_invoice_content()
        self.assertIn("L", content)
