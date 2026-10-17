"""T30 checkout: shipping, totals consistency, payment methods, order emails."""
from decimal import Decimal
from unittest import mock

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from store import services
from store.models import Category, Discount, Order, Product, SiteSettings

CHECKOUT = {
    "customer_name": "Asha", "customer_email": "asha@example.com",
    "customer_phone": "9876543210", "shipping_address": "12 MG Road, Pune",
}


class ComputeTotalsTests(TestCase):
    def settings_row(self, **kw):
        return SiteSettings(store_name="T", **kw)

    def test_no_shipping_configured_keeps_totals_unchanged(self):
        t = services.compute_totals(Decimal("100"), Decimal("0"), self.settings_row())
        self.assertEqual((t["subtotal"], t["shipping"], t["total"]), (Decimal("100.00"), Decimal("0.00"), Decimal("100.00")))
        self.assertIsNone(t["free_shipping_progress"])

    def test_flat_fee_below_threshold_and_free_at_threshold(self):
        row = self.settings_row(shipping_fee=Decimal("99"), free_shipping_threshold=Decimal("2000"))
        below = services.compute_totals(Decimal("1999.99"), Decimal("0"), row)
        self.assertEqual(below["shipping"], Decimal("99.00"))
        self.assertEqual(below["total"], Decimal("2098.99"))
        self.assertEqual(below["free_shipping_remaining"], Decimal("0.01"))
        at = services.compute_totals(Decimal("2000"), Decimal("0"), row)
        self.assertEqual(at["shipping"], Decimal("0.00"))
        self.assertEqual(at["free_shipping_progress"], 100)

    def test_threshold_uses_discounted_value(self):
        row = self.settings_row(shipping_fee=Decimal("50"), free_shipping_threshold=Decimal("1000"))
        t = services.compute_totals(Decimal("1100"), Decimal("200"), row)
        self.assertEqual(t["shipping"], Decimal("50.00"))
        self.assertEqual(t["total"], Decimal("950.00"))

    def test_empty_cart_has_no_shipping(self):
        row = self.settings_row(shipping_fee=Decimal("50"))
        self.assertEqual(services.compute_totals(Decimal("0"), Decimal("0"), row)["shipping"], Decimal("0.00"))


class CheckoutFlowTests(TestCase):
    def setUp(self):
        self.site = SiteSettings.objects.create(store_name="FemDes", currency_symbol="₹",
                                                shipping_fee=Decimal("99"), free_shipping_threshold=Decimal("5000"),
                                                upi_id="shop@okicici")
        cat = Category.objects.create(name="Silk", slug="silk-c", is_active=True)
        self.product = Product.objects.create(category=cat, name="Ruby Blouse", slug="ruby-c", sku="C-1",
                                              price=Decimal("1000"), stock_quantity=10, is_active=True)
        Discount.objects.create(name="Sale", discount_type="percent", scope="product",
                                product=self.product, value=Decimal("10"), is_active=True)

    def add(self, qty=2):
        self.client.post(reverse("add_to_cart", args=[self.product.pk]), {"quantity": qty})

    def test_cart_and_order_agree_on_every_amount(self):
        self.add(2)
        cart = self.client.get(reverse("cart_detail")).context["cart"]
        self.assertEqual((cart["subtotal"], cart["discount_total"], cart["shipping"], cart["total"]),
                         (Decimal("2000.00"), Decimal("200.00"), Decimal("99.00"), Decimal("1899.00")))
        self.client.post(reverse("checkout"), CHECKOUT)
        order = Order.objects.get()
        self.assertEqual((order.subtotal, order.discount_total, order.shipping_total, order.total),
                         (Decimal("2000.00"), Decimal("200.00"), Decimal("99.00"), Decimal("1899.00")))
        self.assertEqual(order.items.get().line_total, Decimal("1800.00"))

    def test_order_pages_show_shipping_and_upi_from_settings(self):
        self.add(1)
        self.client.post(reverse("checkout"), CHECKOUT)
        order = Order.objects.get()
        page = self.client.get(reverse("order_success", args=[order.order_number])).content.decode()
        self.assertIn("shop@okicici", page)
        self.assertIn("Shipping", page)
        self.assertNotIn("+919898989898", page)

    def test_free_shipping_progress_shown_in_cart(self):
        self.add(1)
        self.assertContains(self.client.get(reverse("cart_detail")), "more for free shipping")

    def test_manual_upi_default_when_razorpay_off(self):
        self.add(1)
        response = self.client.post(reverse("checkout"), CHECKOUT)
        order = Order.objects.get()
        self.assertEqual(order.payment_method, "manual_upi")
        self.assertRedirects(response, reverse("order_success", args=[order.order_number]))

    def test_cod_only_when_enabled(self):
        self.add(1)
        response = self.client.post(reverse("checkout"), {**CHECKOUT, "payment_method": "cash_on_delivery"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.count(), 0)
        self.site.cod_enabled = True
        self.site.save()
        self.client.post(reverse("checkout"), {**CHECKOUT, "payment_method": "cash_on_delivery"})
        order = Order.objects.get()
        self.assertEqual(order.payment_method, "cash_on_delivery")
        page = self.client.get(reverse("order_success", args=[order.order_number])).content.decode()
        self.assertIn("cash on delivery", page)

    @override_settings(RAZORPAY_KEY_ID="rzp_test", RAZORPAY_KEY_SECRET="secret")
    def test_razorpay_default_when_configured_and_upi_still_selectable(self):
        self.add(1)
        response = self.client.post(reverse("checkout"), CHECKOUT)
        order = Order.objects.get()
        self.assertEqual(order.payment_method, "razorpay")
        self.assertRedirects(response, reverse("razorpay_payment", args=[order.order_number]), fetch_redirect_response=False)
        self.add(1)
        response = self.client.post(reverse("checkout"), {**CHECKOUT, "payment_method": "manual_upi"})
        order = Order.objects.latest("id")
        self.assertRedirects(response, reverse("order_success", args=[order.order_number]))

    @override_settings(RAZORPAY_KEY_ID="rzp_test", RAZORPAY_KEY_SECRET="secret")
    def test_razorpay_amount_includes_shipping(self):
        self.add(1)
        self.client.post(reverse("checkout"), CHECKOUT)
        order = Order.objects.get()
        fake = mock.MagicMock()
        fake.order.create.return_value = {"id": "order_X"}
        with mock.patch("store.views._get_razorpay_client", return_value=fake):
            self.client.get(reverse("razorpay_payment", args=[order.order_number]))
        self.assertEqual(fake.order.create.call_args[0][0]["amount"], int(order.total * 100))
        self.assertEqual(order.total, Decimal("999.00"))

    @override_settings(STORE_NOTIFY_EMAIL="owner@example.com")
    def test_confirmation_and_staff_emails(self):
        self.add(1)
        self.client.post(reverse("checkout"), CHECKOUT)
        order = Order.objects.get()
        self.assertEqual([m.to for m in mail.outbox], [["asha@example.com"], ["owner@example.com"]])
        self.assertIn(order.order_number, mail.outbox[0].subject)
        self.assertIn("shop@okicici", mail.outbox[0].body)
        self.assertIn("Shipping: ₹99.00", mail.outbox[0].body)

    def test_email_failure_does_not_block_order(self):
        self.add(1)
        with mock.patch("django.core.mail.send_mail", side_effect=OSError("smtp down")):
            response = self.client.post(reverse("checkout"), CHECKOUT)
        order = Order.objects.get()
        self.assertRedirects(response, reverse("order_success", args=[order.order_number]))

    def test_customization_disclaimer_uses_settings(self):
        self.site.customization_advance_amount = Decimal("750")
        self.site.save()
        content = self.client.get(reverse("product_detail", args=[self.product.slug])).content.decode()
        self.assertIn("₹750 advance payment to UPI shop@okicici", content)


class LegacyOrderMigrationTests(TestCase):
    def test_forwards_restates_only_legacy_rows(self):
        import importlib

        from django.apps import apps as global_apps
        mig = importlib.import_module("store.migrations.0021_fix_legacy_order_subtotals")
        legacy = Order.objects.create(customer_name="A", customer_email="a@x.com", shipping_address="x",
                                      subtotal=Decimal("90"), discount_total=Decimal("10"), total=Decimal("90"))
        modern = Order.objects.create(customer_name="B", customer_email="b@x.com", shipping_address="x",
                                      subtotal=Decimal("100"), discount_total=Decimal("10"),
                                      shipping_total=Decimal("10"), total=Decimal("100"))
        plain = Order.objects.create(customer_name="C", customer_email="c@x.com", shipping_address="x",
                                     subtotal=Decimal("50"), total=Decimal("50"))
        mig.forwards(global_apps, None)
        for o in (legacy, modern, plain):
            o.refresh_from_db()
        self.assertEqual((legacy.subtotal, legacy.total), (Decimal("100.00"), Decimal("90.00")))
        self.assertEqual(modern.subtotal, Decimal("100.00"))
        self.assertEqual(plain.subtotal, Decimal("50.00"))
        mig.backwards(global_apps, None)
        legacy.refresh_from_db()
        self.assertEqual(legacy.subtotal, Decimal("90.00"))
