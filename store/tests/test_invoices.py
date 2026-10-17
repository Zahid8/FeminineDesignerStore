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


class OrderDetailAriaTests(TestCase):
    """Order detail status badges have aria-current on the active status."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="buyer", password="pass")

    def test_active_status_has_aria_current(self):
        self.client.login(username="buyer", password="pass")
        for status_val in ("pending", "shipped"):
            order = Order.objects.create(
                customer_name="A", customer_email="a@t.com",
                shipping_address="Addr", customer_user=self.user,
                status=status_val,
            )
            url = reverse("account_order_detail", kwargs={"order_number": order.order_number})
            response = self.client.get(url)
            # Only one aria-current="step"
            self.assertEqual(response.content.decode().count('aria-current="step"'), 1)
            order.delete()


class TimelineActiveStatusTests(TestCase):
    """Every Order.STATUS_CHOICES value can be the active/current status."""

    TIMELINE_LABELS = {
        "pending": "Order Placed",
        "confirmed": "Confirmed",
        "processing": "Processing",
        "shipped": "Shipped",
        "delivered": "Delivered",
        "completed": "Completed",
        "cancelled": "Cancelled",
    }

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="buyer", password="pass")

    def test_each_status_is_active(self):
        """For each status value exactly that step is current (is-current +
        aria-current="step") and every other step is rendered as a plain step."""
        import re

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
            timeline = re.search(
                r'<ol class="fd-steps-track[^"]*" aria-label="Order status timeline">(.*?)</ol>',
                content, re.S,
            )
            self.assertIsNotNone(timeline, "Order status timeline <ol> missing")
            steps = re.findall(r'<li class="([^"]*)"([^>]*)>([^<]+)</li>', timeline.group(1))
            self.assertEqual([label for _, _, label in steps],
                             list(self.TIMELINE_LABELS.values()))
            for classes, attrs, label in steps:
                is_current = label == self.TIMELINE_LABELS[status_val]
                self.assertEqual("is-current" in classes.split(), is_current,
                                 msg=f"Step '{label}' current-class mismatch for {status_val}")
                self.assertEqual('aria-current="step"' in attrs, is_current,
                                 msg=f"Step '{label}' aria-current mismatch for {status_val}")
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
        self.assertContains(response, "Online Order Bill")

    def test_customer_cannot_view_others_invoice(self):
        self.client.login(username="other", password="pass")
        response = self.client.get(self.invoice_url)
        self.assertEqual(response.status_code, 404)

    def test_invoice_has_store_identity_and_totals_section(self):
        """Invoice renders the header, Bill To area, totals section, and order number."""
        content = self._get_invoice_content()
        self.assertIn("Online Order Bill", content)
        self.assertIn(self.order.order_number, content)
        self.assertIn("Customer", content)
        self.assertIn("Delivery address", content)
        self.assertIn("Payment summary", content)
        self.assertIn("Status", content)

    def test_invoice_renders_order_item_snapshots(self):
        """Invoice renders product name, SKU, qty, unit price, line total, variants as table cells."""
        self.client.login(username="buyer", password="pass")
        response = self.client.get(self.invoice_url)
        # Product identity and variants
        self.assertContains(response, "Test Blouse")
        self.assertContains(response, "SKU-INV")
        self.assertContains(response, "Red")
        self.assertContains(response, "M")
        # Quantity, unit price and line total, in the item row
        self.assertContains(response, "2 × Test Blouse")
        self.assertContains(response, "Qty 2 | Size M | Red | SKU SKU-INV | ₹123.45 each")
        self.assertContains(response, '<span class="amount">₹246.90</span>', html=True)

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
        self.assertIn('<span>Items</span><span>₹246.90</span>', content)
        self.assertIn('<span>− Discount</span><span>₹10.00</span>', content)
        self.assertIn('<b>Total</b><strong>₹236.90</strong>', content)

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


class BillingLinkTests(TestCase):
    """The shop signs bill links exactly like the billing app (shared test vector)."""

    def test_matches_billing_app_signature(self):
        from django.test import override_settings

        from store.billing_links import online_bill_signature, online_bill_url

        self.assertEqual(online_bill_signature("FD-20261017-ABC123", secret="test-secret"), "fLHSYKgw00GrNOvRClHfhL")
        self.assertEqual(online_bill_signature("fd-20261017-abc123", secret="test-secret"), "fLHSYKgw00GrNOvRClHfhL")
        with override_settings(BILLING_APP_URL="https://billing.example.com/", BILL_LINK_SECRET="test-secret"):
            self.assertEqual(online_bill_url("FD-20261017-ABC123"),
                             "https://billing.example.com/bill/online/FD-20261017-ABC123/fLHSYKgw00GrNOvRClHfhL")
        with override_settings(BILLING_APP_URL="", BILL_LINK_SECRET="test-secret"):
            self.assertEqual(online_bill_url("FD-20261017-ABC123"), "")
        self.assertEqual(online_bill_signature("FD-1", secret=""), "")


class InvoicePageTests(TestCase):
    """The customer bill mirrors the billing app's receipt and works on phones."""

    def setUp(self):
        from decimal import Decimal

        from store.models import Category, OrderItem, Product, SiteSettings

        SiteSettings.objects.create(store_name="Feminine Designer by Sajida", gstin="06AYWPB8525D1ZB", contact_phone="9718926185",
                                    address="Shop 222, Gurugram", returns_summary="Delivery date is approximate.", currency_symbol="₹")
        self.user = User.objects.create_user(username="asha", email="asha@example.com", password="pw-12345!")
        cat = Category.objects.create(name="Silk", slug="silk-inv", is_active=True)
        product = Product.objects.create(category=cat, name="Zari Blouse", slug="zari-inv", sku="INV-1", price=Decimal("2000"), stock_quantity=5, is_active=True)
        self.order = Order.objects.create(customer_name="Asha Rao", customer_email="asha@example.com", customer_phone="9876543210",
                                          shipping_address="12 MG Road\nPune", location_url="https://maps.app.goo.gl/AbC123", notes="Ring the bell",
                                          subtotal=Decimal("2400"), total=Decimal("2400"), customer_user=self.user, payment_status="paid")
        OrderItem.objects.create(order=self.order, product=product, product_name="Zari Blouse", sku="INV-1", unit_price=Decimal("2400"), quantity=1,
                                 line_total=Decimal("2400"), size="Made to measure",
                                 customization={"measurements": {"chest": "36.00"}, "sleeve_style": "elbow", "notes": "deep back"})
        self.client.login(username="asha", password="pw-12345!")

    def test_bill_layout_matches_billing_receipt(self):
        response = self.client.get(reverse("account_order_invoice", args=[self.order.order_number]))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn("fd-header", content)  # standalone sheet, no store chrome
        self.assertIn('name="viewport"', content)
        for text in ("Online Order Bill", self.order.order_number, "Feminine Designer by Sajida", "GSTIN 06AYWPB8525D1ZB",
                     "Item summary", "Zari Blouse", "Custom size", "Chest 36 in", "Elbow length", "deep back",
                     "Delivery address", "12 MG Road", "Google Maps location", "Customer notes: Ring the bell",
                     "Payment summary", "₹2400.00", "Balance", "This bill is for an order placed on our online store.", "within 48 hours", "Authorized Signatory",
                     "Thank you for choosing Feminine Designer by Sajida", "Save as PDF"):
            self.assertIn(text, content, text)

    def test_download_pdf_links_to_billing_app_when_configured(self):
        from django.test import override_settings

        with override_settings(BILLING_APP_URL="https://billing.example.com", BILL_LINK_SECRET="test-secret"):
            content = self.client.get(reverse("account_order_invoice", args=[self.order.order_number])).content.decode()
            self.assertIn(f"https://billing.example.com/bill/online/{self.order.order_number}/", content)
            self.assertIn("Download PDF", content)
            self.assertNotIn("Save as PDF", content)
            success = self.client.get(reverse("order_success", args=[self.order.order_number])).content.decode()
            self.assertIn("Download Bill (PDF)", success)

    def test_other_customers_cannot_open_it(self):
        User.objects.create_user(username="other", password="pw-12345!")
        self.client.logout(); self.client.login(username="other", password="pw-12345!")
        self.assertEqual(self.client.get(reverse("account_order_invoice", args=[self.order.order_number])).status_code, 404)
