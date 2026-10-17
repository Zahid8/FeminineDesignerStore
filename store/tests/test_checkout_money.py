"""T30 checkout: shipping, totals consistency, payment methods, order emails."""
from decimal import Decimal
from unittest import mock

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from store import services
from store.models import Category, Discount, Order, Product, SiteSettings

CHECKOUT = {
    "customer_name": "Asha", "customer_email": "asha@example.com", "customer_phone": "9876543210",
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

    def test_customization_terms_editable_in_settings(self):
        self.site.customization_terms = "Custom pieces are final sale."
        self.site.save()
        content = self.client.get(reverse("product_detail", args=[self.product.slug])).content.decode()
        self.assertIn("Custom pieces are final sale.", content)
        self.assertNotIn("advance payment", content)


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


class DeliveryLocationLinkTests(TestCase):
    """Optional Google Maps link on delivery details."""

    def test_clean_maps_link(self):
        from django.core.exceptions import ValidationError

        from store.locations import clean_maps_link

        self.assertEqual(clean_maps_link(""), "")
        self.assertEqual(clean_maps_link("  https://maps.app.goo.gl/AbC123  "), "https://maps.app.goo.gl/AbC123")
        self.assertEqual(clean_maps_link("Home 📍 https://maps.app.goo.gl/AbC123, see you"), "https://maps.app.goo.gl/AbC123")
        self.assertEqual(clean_maps_link("http://www.google.com/maps?q=18.52,73.85"), "https://www.google.com/maps?q=18.52,73.85")
        self.assertEqual(clean_maps_link("https://www.google.co.in/maps/place/Pune"), "https://www.google.co.in/maps/place/Pune")
        self.assertEqual(clean_maps_link("https://maps.google.com/?q=1,2"), "https://maps.google.com/?q=1,2")
        for bad in ("my house near temple", "https://evil.example.com/maps", "https://www.google.com/search?q=x", "javascript:alert(1)"):
            with self.assertRaises(ValidationError, msg=bad):
                clean_maps_link(bad)


class CheckoutLocationTests(TestCase):
    def setUp(self):
        from store.models import Category, Product

        cat = Category.objects.create(name="Silk", slug="silk-loc", is_active=True)
        self.p = Product.objects.create(category=cat, name="Rose", slug="rose-loc", sku="LOC-1", price=Decimal("500"),
                                        stock_quantity=5, is_active=True)
        self.client.post(reverse("add_to_cart", args=[self.p.pk]), {"quantity": "1"})

    def checkout(self, **extra):
        data = {"customer_name": "Asha", "customer_email": "asha@example.com", "customer_phone": "9876543210", "shipping_address": "Pune", **extra}
        return self.client.post(reverse("checkout"), data)

    def test_location_is_optional(self):
        self.checkout()
        self.assertEqual(Order.objects.get().location_url, "")

    def test_pasted_share_text_is_saved_as_link_and_remembered(self):
        from django.contrib.auth.models import User

        user = User.objects.create_user("asha", "asha@example.com", "pw")
        self.client.force_login(user)
        self.client.post(reverse("add_to_cart", args=[self.p.pk]), {"quantity": "1"})
        self.checkout(location_url="Home: https://maps.app.goo.gl/AbC123")
        self.assertEqual(Order.objects.get().location_url, "https://maps.app.goo.gl/AbC123")
        user.refresh_from_db()
        self.assertEqual(user.profile.location_url, "https://maps.app.goo.gl/AbC123")
        edit = self.client.get(reverse("account_profile_edit")).content.decode()
        self.assertIn('value="https://maps.app.goo.gl/AbC123"', edit)

    def test_non_maps_link_is_rejected_with_message(self):
        response = self.checkout(location_url="https://example.com/my-house")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Paste a Google Maps link")
        self.assertEqual(Order.objects.count(), 0)


class CheckoutKeepsInputOnErrorTests(TestCase):
    def test_notes_survive_a_validation_error(self):
        from store.models import Category, Product

        cat = Category.objects.create(name="Silk", slug="silk-keep", is_active=True)
        p = Product.objects.create(category=cat, name="Rose", slug="rose-keep", sku="K-1", price=Decimal("500"), stock_quantity=5, is_active=True)
        self.client.post(reverse("add_to_cart", args=[p.pk]), {"quantity": "1"})
        response = self.client.post(reverse("checkout"), {"customer_name": "A", "customer_email": "a@example.com", "customer_phone": "9876543210", "shipping_address": "Pune",
                                                          "notes": "Gate code 2244", "location_url": "not a link"})
        self.assertContains(response, ">Gate code 2244</textarea>")
        self.assertContains(response, 'value="not a link"')


class StructuredAddressTests(TestCase):
    """Checkout collects an Indian postal address (two lines, city, state, PIN) and a 10-digit mobile."""

    def setUp(self):
        from store.models import Category, Product

        cat = Category.objects.create(name="Silk", slug="silk-addr", is_active=True)
        self.p = Product.objects.create(category=cat, name="Rose", slug="rose-addr", sku="ADDR-1", price=Decimal("500"),
                                        stock_quantity=5, is_active=True)
        self.client.post(reverse("add_to_cart", args=[self.p.pk]), {"quantity": "1"})
        self.base = {"customer_name": "Asha", "customer_email": "asha@example.com", "customer_phone": "+91 98765 43210",
                     "address_line1": "Flat 4B, Lotus Residency", "address_line2": "Baner Road", "city": "Pune",
                     "state": "Maharashtra", "pincode": "411045"}

    def test_structured_address_is_saved_and_composed(self):
        self.client.post(reverse("checkout"), self.base)
        order = Order.objects.get()
        self.assertEqual((order.address_line1, order.address_line2, order.city, order.state, order.pincode, order.country),
                         ("Flat 4B, Lotus Residency", "Baner Road", "Pune", "Maharashtra", "411045", "India"))
        self.assertEqual(order.shipping_address, "Flat 4B, Lotus Residency\nBaner Road\nPune, Maharashtra 411045\nIndia")
        self.assertEqual(order.customer_phone, "9876543210")

    def test_missing_parts_and_bad_pincode_are_rejected(self):
        data = {**self.base, "city": "", "pincode": "4110"}
        response = self.client.post(reverse("checkout"), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "City is required.")
        self.assertContains(response, "Enter a valid 6-digit PIN code.")
        self.assertEqual(Order.objects.count(), 0)
        bad_phone = self.client.post(reverse("checkout"), {**self.base, "customer_phone": "12345"})
        self.assertContains(bad_phone, "Enter a valid 10-digit mobile number.")

    def test_state_dropdown_and_autocomplete_hints_render(self):
        content = self.client.get(reverse("checkout")).content.decode()
        self.assertIn('<option value="Maharashtra"', content)
        self.assertIn('autocomplete="postal-code"', content)
        self.assertIn('autocomplete="address-line1"', content)
        self.assertIn('type="tel"', content)

    def test_logged_in_customer_gets_address_remembered_and_prefilled(self):
        from django.contrib.auth.models import User

        user = User.objects.create_user("asha", "asha@example.com", "pw")
        self.client.force_login(user)
        self.client.post(reverse("add_to_cart", args=[self.p.pk]), {"quantity": "1"})
        self.client.post(reverse("checkout"), self.base)
        user.refresh_from_db()
        self.assertEqual((user.profile.city, user.profile.pincode, user.profile.phone), ("Pune", "411045", "9876543210"))
        self.client.post(reverse("add_to_cart", args=[self.p.pk]), {"quantity": "1"})
        page = self.client.get(reverse("checkout")).content.decode()
        self.assertIn('value="Flat 4B, Lotus Residency"', page)
        self.assertIn('<option value="Maharashtra" selected>', page)

    def test_api_exposes_structured_shipping(self):
        from django.test import override_settings

        self.client.post(reverse("checkout"), self.base)
        order = Order.objects.get()
        with override_settings(WEBSTORE_API_TOKEN="t"):
            data = self.client.get(reverse("api_online_order_detail", args=[order.order_number]), HTTP_AUTHORIZATION="Bearer t").json()
        self.assertEqual(data["order"]["shipping"], {"line1": "Flat 4B, Lotus Residency", "line2": "Baner Road", "city": "Pune",
                                                     "state": "Maharashtra", "pincode": "411045", "country": "India"})
