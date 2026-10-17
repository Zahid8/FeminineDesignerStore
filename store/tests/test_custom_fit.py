"""T33 made-to-measure: form validation, cart/order plumbing, product page builder."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from store import measurements as mspec
from store.forms import CustomFitForm
from store.models import Category, CustomerProfile, CustomizationRequest, Order, Product, SiteSettings

MEASURES = {"length": "15", "chest": "36", "waist": "30", "armhole": "16", "opening": "11", "bicep": "13"}
CHECKOUT = {"customer_name": "Asha", "customer_email": "asha@example.com", "shipping_address": "Pune"}


class CustomFitFormTests(TestCase):
    def test_valid_inches_round_trip(self):
        form = CustomFitForm({**MEASURES, "unit": "in", "sleeve_style": "elbow", "notes": " deep back "})
        self.assertTrue(form.is_valid(), form.errors)
        custom = form.as_custom()
        self.assertEqual(custom["measurements"]["chest"], "36.00")
        self.assertEqual(custom["sleeve_style"], "elbow")
        self.assertEqual(custom["notes"], "deep back")
        self.assertNotIn("sleeve_length", custom["measurements"])

    def test_cm_converted_to_inches(self):
        form = CustomFitForm({**{k: str(Decimal(v) * Decimal("2.54")) for k, v in MEASURES.items()}, "unit": "cm"})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.as_custom()["measurements"]["chest"], "36.00")

    def test_out_of_range_and_missing_rejected(self):
        form = CustomFitForm({**MEASURES, "chest": "90"})
        self.assertFalse(form.is_valid())
        self.assertIn("between 20–70 in", form.errors["chest"][0])
        form = CustomFitForm({**MEASURES, "waist": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("waist", form.errors)
        in_cm = {k: str(Decimal(v) * Decimal("2.54")) for k, v in MEASURES.items()}
        form = CustomFitForm({**in_cm, "chest": "90", "unit": "cm"})
        self.assertTrue(form.is_valid(), form.errors)  # 90 cm = 35.43 in

    def test_optional_measurements_validated_when_given(self):
        form = CustomFitForm({**MEASURES, "front_neck": "40"})
        self.assertFalse(form.is_valid())
        self.assertIn("front_neck", form.errors)

    def test_summary_rows(self):
        rows = mspec.summary({"measurements": {"chest": "36.00", "length": "15.50"}, "sleeve_style": "full"})
        self.assertEqual(rows, [("Length", "15.5 in"), ("Chest", "36 in"), ("Sleeves", "Full sleeve")])
        self.assertEqual(mspec.summary(None), [])


class CustomCartTests(TestCase):
    def setUp(self):
        self.site = SiteSettings.objects.create(store_name="FemDes", currency_symbol="₹",
                                                customization_fee=Decimal("400"), customization_lead_time="3 weeks")
        cat = Category.objects.create(name="Silk", slug="silk-cf", is_active=True)
        self.p = Product.objects.create(category=cat, name="Zari Blouse", slug="zari-cf", sku="CF-1",
                                        price=Decimal("2000"), stock_quantity=5, is_active=True, size_options="S, M")

    def add_custom(self, **extra):
        return self.client.post(reverse("add_to_cart", args=[self.p.pk]), {"custom": "1", "quantity": 1, **MEASURES, **extra})

    def test_custom_line_carries_fee_and_summary(self):
        response = self.add_custom(sleeve_style="full", notes="padded")
        self.assertEqual(response.status_code, 302)
        cart = self.client.get(reverse("cart_detail")).context["cart"]
        line = cart["lines"][0]
        self.assertEqual(line["size"], "Made to measure")
        self.assertEqual(line["unit_price"], Decimal("2400.00"))
        self.assertEqual(line["custom_fee"], Decimal("400"))
        self.assertEqual(line["lead_time"], "3 weeks")
        self.assertIn(("Chest", "36 in"), line["custom_summary"])
        self.assertEqual(cart["subtotal"], Decimal("2400.00"))
        page = self.client.get(reverse("cart_detail")).content.decode()
        self.assertIn("Made to measure", page)
        self.assertIn("“padded”", page)

    def test_product_fee_overrides_store_fee(self):
        self.p.customization_fee = Decimal("150")
        self.p.save()
        self.add_custom()
        self.assertEqual(self.client.get(reverse("cart_detail")).context["cart"]["lines"][0]["unit_price"], Decimal("2150.00"))

    def test_different_measurements_are_separate_lines(self):
        self.add_custom()
        self.add_custom(chest="38")
        self.add_custom()
        lines = self.client.get(reverse("cart_detail")).context["cart"]["lines"]
        self.assertEqual(len(lines), 2)
        self.assertEqual(sorted(l["quantity"] for l in lines), [1, 2])

    def test_invalid_measurements_rerender_builder_with_errors(self):
        response = self.add_custom(chest="")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required")
        self.assertTrue(response.context["custom_open"])
        self.assertEqual(self.client.get(reverse("cart_detail")).context["cart"]["item_count"], 0)

    def test_customization_disabled_product_rejects(self):
        self.p.allow_customization = False
        self.p.save()
        self.add_custom()
        self.assertEqual(self.client.get(reverse("cart_detail")).context["cart"]["item_count"], 0)
        self.assertNotIn("Made to measure", self.client.get(reverse("product_detail", args=[self.p.slug])).content.decode().split("fd-fit-switch")[0][-500:])

    def test_order_snapshots_measurements_and_saves_to_profile(self):
        user = User.objects.create_user("asha", "asha@example.com", "pw-12345!")
        self.client.force_login(user)
        self.add_custom(sleeve_style="cap")
        self.client.post(reverse("checkout"), CHECKOUT)
        order = Order.objects.get()
        item = order.items.get()
        self.assertEqual(item.customization["measurements"]["chest"], "36.00")
        self.assertEqual(item.customization["sleeve_style"], "cap")
        self.assertEqual(item.unit_price, Decimal("2400.00"))
        self.assertEqual(order.total, Decimal("2400.00"))
        self.assertEqual(CustomerProfile.objects.get(user=user).saved_measurements["chest"], "36.00")
        self.assertIn("made to measure: Length 15 in", mail.outbox[0].body)
        detail = self.client.get(reverse("account_order_detail", args=[order.order_number])).content.decode()
        self.assertIn("Cap sleeve", detail)
        success = self.client.get(reverse("order_success", args=[order.order_number])).content.decode()
        self.assertIn("Made to measure", success)

    def test_saved_measurements_prefill_builder(self):
        user = User.objects.create_user("meera", "m@example.com", "pw-12345!")
        CustomerProfile.objects.create(user=user, saved_measurements={"chest": "38.00", "length": "16.00"})
        self.client.force_login(user)
        content = self.client.get(reverse("product_detail", args=[self.p.slug])).content.decode()
        self.assertIn('name="chest" id="id_chest" value="38.00"', content)
        self.assertIn("Prefilled with your saved measurements", content)


class BuilderPageTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(name="Silk", slug="silk-bp", is_active=True)
        self.p = Product.objects.create(category=cat, name="Rose Blouse", slug="rose-bp", sku="BP-1",
                                        price=Decimal("1500"), stock_quantity=0, is_active=True, default_chest=Decimal("34"))

    def test_builder_present_even_when_sold_out(self):
        content = self.client.get(reverse("product_detail", args=[self.p.slug])).content.decode()
        for text in ("fd-fit-switch", 'id="customize-section"', 'name="custom" value="1"', "Add Made-to-Measure to Bag",
                     "Request a Fitting Call", 'value="34.00"', "Dispatch in <strong>3–4 weeks</strong>"):
            self.assertIn(text, content, text)

    def test_fit_param_opens_builder(self):
        response = self.client.get(reverse("product_detail", args=[self.p.slug]), {"fit": "custom"})
        self.assertTrue(response.context["custom_open"])

    def test_share_request_still_works_with_extras(self):
        response = self.client.post(reverse("customization_create", args=[self.p.slug]),
                                    {**MEASURES, "customer_name": "Asha", "customer_phone": "9876543210",
                                     "sleeve_style": "elbow", "notes": "lining please", "front_neck": "7"})
        cr = CustomizationRequest.objects.get()
        self.assertRedirects(response, reverse("customization_created", args=[cr.token]))
        self.assertEqual(cr.sleeve_style, "elbow")
        self.assertEqual(cr.details, {"front_neck": "7.00"})
        page = self.client.get(reverse("customization_detail", args=[cr.token])).content.decode()
        self.assertIn("lining please", page)
        self.assertIn("Elbow", page)

    def test_share_request_without_contact_rerenders_errors(self):
        response = self.client.post(reverse("customization_create", args=[self.p.slug]), MEASURES)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required")
        self.assertEqual(CustomizationRequest.objects.count(), 0)


class FittingRequestFlowTests(TestCase):
    def setUp(self):
        SiteSettings.objects.create(store_name="FemDes", whatsapp_url="https://wa.me/919800000000")
        cat = Category.objects.create(name="Silk", slug="silk-fr", is_active=True)
        self.p = Product.objects.create(category=cat, name="Rose Blouse", slug="rose-fr", sku="FR-1",
                                        price=Decimal("1500"), stock_quantity=2, is_active=True)

    def request_call(self):
        return self.client.post(reverse("customization_create", args=[self.p.slug]),
                                {**MEASURES, "customer_name": "Asha", "customer_phone": "9876543210", "notes": "deep back"}, follow=True)

    def test_confirmation_page_has_next_steps_and_one_tap_whatsapp(self):
        from django.test import override_settings
        with override_settings(STORE_NOTIFY_EMAIL="owner@example.com"):
            response = self.request_call()
        cr = CustomizationRequest.objects.get()
        content = response.content.decode()
        self.assertIn(cr.reference, content)
        self.assertIn("What happens next", content)
        self.assertIn("Add to Bag with These Measurements", content)
        self.assertIn("https://wa.me/919800000000?text=", content)
        self.assertIn(cr.reference, content.split("wa.me/919800000000?text=")[1][:300])
        self.assertNotIn("advance payment", content)
        self.assertNotIn("Copy", content)
        self.assertEqual(mail.outbox[0].to, ["owner@example.com"])
        self.assertIn("Chest: 36 in", mail.outbox[0].body)

    def test_request_prefills_builder_for_add_to_bag(self):
        self.request_call()
        content = self.client.get(self.p.get_absolute_url(), {"fit": "custom"}).content.decode()
        self.assertIn("Prefilled from your fitting request", content)
        self.assertIn('name="chest" id="id_chest" value="36.00"', content)
        self.assertIn("deep back", content)


class MadeToMeasureStockTests(TestCase):
    """Made-to-measure is stitched to order: it ignores and does not consume stock."""

    def setUp(self):
        cat = Category.objects.create(name="Silk", slug="silk-st", is_active=True)
        self.p = Product.objects.create(category=cat, name="Rose Blouse", slug="rose-st", sku="ST-1",
                                        price=Decimal("1500"), stock_quantity=0, is_active=True)

    def add_custom(self, qty="1"):
        return self.client.post(reverse("add_to_cart", args=[self.p.pk]), {**MEASURES, "custom": "1", "quantity": qty})

    def test_sold_out_product_can_be_added_made_to_measure(self):
        self.add_custom()
        cart = self.client.session["femdes_cart"]
        self.assertEqual(len(cart), 1)
        self.assertEqual(next(iter(cart.values()))["size"], "Made to measure")

    def test_ready_made_still_blocked_when_sold_out(self):
        self.client.post(reverse("add_to_cart", args=[self.p.pk]), {"quantity": "1", "size": "M"})
        self.assertFalse(self.client.session.get("femdes_cart"))

    def test_custom_quantity_can_exceed_stock_and_order_keeps_stock(self):
        self.add_custom()
        key = next(iter(self.client.session["femdes_cart"]))
        self.client.post(reverse("update_cart", args=[key]), {"quantity": "3"})
        self.assertEqual(self.client.session["femdes_cart"][key]["quantity"], 3)
        self.client.post(reverse("checkout"), CHECKOUT)
        order = Order.objects.get()
        self.assertEqual(order.items.get().quantity, 3)
        self.p.refresh_from_db()
        self.assertEqual(self.p.stock_quantity, 0)

    def test_mixed_cart_only_ready_made_consumes_stock(self):
        Product.objects.filter(pk=self.p.pk).update(stock_quantity=2)
        self.add_custom()
        self.client.post(reverse("add_to_cart", args=[self.p.pk]), {"quantity": "2"})
        self.client.post(reverse("checkout"), CHECKOUT)
        self.assertEqual(Order.objects.count(), 1)
        self.p.refresh_from_db()
        self.assertEqual(self.p.stock_quantity, 0)


class BuilderPrefillAndTermsTests(TestCase):
    """Alpine state must carry server-prefilled values; checkout terms show for mixed carts."""

    def setUp(self):
        SiteSettings.objects.create(store_name="FemDes", customization_terms="Custom pieces are final sale.")
        cat = Category.objects.create(name="Silk", slug="silk-pf", is_active=True)
        self.p = Product.objects.create(category=cat, name="Rose Blouse", slug="rose-pf", sku="PF-1",
                                        price=Decimal("1500"), stock_quantity=3, is_active=True,
                                        default_chest=Decimal("34"))

    def test_alpine_state_seeded_with_prefill(self):
        content = self.client.get(self.p.get_absolute_url(), {"fit": "custom"}).content.decode()
        self.assertIn("chest: '34.00'", content)  # x-model would otherwise blank the input

    def test_alpine_state_keeps_values_after_validation_error(self):
        response = self.client.post(reverse("add_to_cart", args=[self.p.pk]),
                                    {**MEASURES, "chest": "90", "custom": "1", "quantity": "1", "notes": "deep back"})
        content = response.content.decode()
        self.assertIn("waist: '30'", content)
        self.assertIn("notes: 'deep back'", content)
        self.assertIn("scrollIntoView", content)

    def test_terms_shown_for_mixed_cart(self):
        self.client.post(reverse("add_to_cart", args=[self.p.pk]), {"quantity": "1"})
        self.client.post(reverse("add_to_cart", args=[self.p.pk]), {**MEASURES, "custom": "1", "quantity": "1"})
        self.assertContains(self.client.get(reverse("checkout")), "Custom pieces are final sale.")

    def test_terms_hidden_for_ready_made_only(self):
        self.client.post(reverse("add_to_cart", args=[self.p.pk]), {"quantity": "1"})
        self.assertNotContains(self.client.get(reverse("checkout")), "Made-to-measure terms")
