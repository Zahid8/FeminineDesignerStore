from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from store import coupons
from store.models import Coupon, Order, Product, WishlistItem


class _Base(TestCase):
    def setUp(self):
        self.p = Product.objects.create(name="Blouse", slug="b", price=Decimal("2200"), compare_at_price=Decimal("2800"), stock_quantity=5)
        self.q = Product.objects.create(name="Top", slug="t", price=Decimal("1500"), stock_quantity=5)
        self.c10 = Coupon.objects.create(code="festive10", description="10% off", discount_type="percent", value=Decimal("10"),
                                         max_discount=Decimal("300"), min_order_amount=Decimal("3000"))
        self.flat = Coupon.objects.create(code="FLAT200", discount_type="fixed", value=Decimal("200"), per_customer_limit=1)

    def add(self, product, qty=1):
        self.client.post(reverse("add_to_cart", kwargs={"product_id": product.pk}), {"quantity": qty})

    def checkout(self, email="a@example.com"):
        return self.client.post(reverse("checkout"), {"customer_name": "A", "customer_email": email, "customer_phone": "9876543210",
                                                      "shipping_address": "Addr", "payment_method": "manual_upi"})


class CouponRuleTests(_Base):
    def test_code_saved_uppercase_and_case_insensitive(self):
        self.assertEqual(self.c10.code, "FESTIVE10")
        self.assertEqual(coupons.check("Festive10", Decimal("3700"))[1], Decimal("300.00"))  # capped

    def test_percent_and_fixed_maths(self):
        self.assertEqual(coupons.check("FESTIVE10", Decimal("3000"))[1], Decimal("300.00"))
        self.assertEqual(coupons.check("FLAT200", Decimal("150"))[1], Decimal("150.00"))  # never more than the order

    def test_rejections(self):
        with self.assertRaisesMessage(coupons.CouponError, "Add ₹500.00 more"):
            coupons.check("FESTIVE10", Decimal("2500"))
        with self.assertRaisesMessage(coupons.CouponError, "not a valid coupon"):
            coupons.check("NOPE", Decimal("5000"))
        Coupon.objects.filter(pk=self.flat.pk).update(ends_at=timezone.now() - timedelta(days=1))
        with self.assertRaisesMessage(coupons.CouponError, "expired"):
            coupons.check("FLAT200", Decimal("5000"))
        Coupon.objects.filter(pk=self.flat.pk).update(ends_at=None, starts_at=timezone.now() + timedelta(days=1))
        with self.assertRaisesMessage(coupons.CouponError, "not a valid"):
            coupons.check("FLAT200", Decimal("5000"))

    def test_usage_limits_and_first_order(self):
        Order.objects.create(customer_name="A", customer_email="a@example.com", shipping_address="x", coupon_code="FLAT200")
        with self.assertRaisesMessage(coupons.CouponError, "already used"):
            coupons.check("FLAT200", Decimal("5000"), email="A@example.com")
        coupons.check("FLAT200", Decimal("5000"), email="b@example.com")
        Coupon.objects.filter(pk=self.flat.pk).update(usage_limit=1)
        with self.assertRaisesMessage(coupons.CouponError, "fully used"):
            coupons.check("FLAT200", Decimal("5000"), email="b@example.com")
        first = Coupon.objects.create(code="WELCOME", discount_type="fixed", value=Decimal("100"), first_order_only=True)
        with self.assertRaisesMessage(coupons.CouponError, "first order"):
            coupons.check("WELCOME", Decimal("5000"), email="a@example.com")
        self.assertEqual(coupons.check(first.code, Decimal("5000"), email="new@example.com")[1], Decimal("100.00"))


class BagCouponFlowTests(_Base):
    def test_apply_shows_in_totals_and_order_records_it(self):
        self.add(self.p); self.add(self.q)
        self.client.post(reverse("cart_coupon"), {"code": "festive10"})
        r = self.client.get(reverse("cart_detail"))
        cart = r.context["cart"]
        self.assertEqual((cart["coupon_code"], cart["coupon_discount"]), ("FESTIVE10", Decimal("300.00")))
        self.assertEqual(cart["mrp_total"], Decimal("4300.00"))
        self.assertEqual(cart["you_save"], Decimal("900.00"))
        self.assertContains(r, "Coupon (FESTIVE10)")
        self.checkout()
        o = Order.objects.get()
        self.assertEqual((o.coupon_code, o.coupon_discount, o.discount_total, o.total), ("FESTIVE10", Decimal("300.00"), Decimal("300.00"), Decimal("3400.00")))
        self.assertEqual(o.subtotal - o.discount_total + o.shipping_total, o.total)
        self.assertNotIn("coupon_code", self.client.session)

    def test_invalid_coupon_message_and_not_stored(self):
        self.add(self.q)
        r = self.client.post(reverse("cart_coupon"), {"code": "FESTIVE10"}, follow=True)
        self.assertContains(r, "Add ₹1500.00 more")
        self.assertNotIn("coupon_code", self.client.session)

    def test_coupon_that_stops_qualifying_blocks_checkout_with_reason(self):
        self.add(self.p); self.add(self.q)
        self.client.post(reverse("cart_coupon"), {"code": "FLAT200"})
        Order.objects.create(customer_name="A", customer_email="a@example.com", shipping_address="x", coupon_code="FLAT200")
        r = self.checkout("a@example.com")
        self.assertEqual(Order.objects.filter(coupon_code="FLAT200").count(), 1)
        self.assertContains(r, "already used", status_code=200)

    def test_remove(self):
        self.add(self.p); self.add(self.q)
        self.client.post(reverse("cart_coupon"), {"code": "FESTIVE10"})
        self.client.post(reverse("cart_coupon"), {"action": "remove"})
        self.assertNotIn("coupon_code", self.client.session)

    def test_offers_listed(self):
        self.add(self.q)
        self.assertContains(self.client.get(reverse("cart_detail")), "FESTIVE10")


class SaveForLaterTests(_Base):
    def key(self):
        return next(iter(self.client.session["femdes_cart"]))

    def test_save_and_move_back(self):
        self.add(self.p, 2)
        k = self.key()
        self.client.post(reverse("cart_save_for_later", args=[k]))
        self.assertEqual(self.client.session["femdes_cart"], {})
        r = self.client.get(reverse("cart_detail"))
        self.assertContains(r, "Saved for later (1)")
        self.client.post(reverse("saved_move_to_bag", args=[k]))
        self.assertEqual(sum(i["quantity"] for i in self.client.session["femdes_cart"].values()), 2)
        self.assertEqual(self.client.session["saved_for_later"], [])

    def test_out_of_stock_stays_saved(self):
        self.add(self.p)
        k = self.key()
        self.client.post(reverse("cart_save_for_later", args=[k]))
        Product.objects.filter(pk=self.p.pk).update(stock_quantity=0)
        self.client.post(reverse("saved_move_to_bag", args=[k]))
        self.assertEqual(len(self.client.session["saved_for_later"]), 1)

    def test_move_to_wishlist_removes_from_bag_and_never_unsaves(self):
        u = User.objects.create_user("u", password="x"); self.client.force_login(u)
        WishlistItem.objects.create(user=u, product=self.p)
        self.add(self.p)
        self.client.post(reverse("cart_move_to_wishlist", args=[self.key()]))
        self.assertEqual(self.client.session["femdes_cart"], {})
        self.assertTrue(WishlistItem.objects.filter(user=u, product=self.p).exists())


class DeliveryEstimateTests(TestCase):
    @mock.patch("store.delivery.lookup", return_value={"city": "Mumbai", "state": "Maharashtra"})
    def test_endpoint(self, _):
        r = self.client.get(reverse("delivery_estimate", args=["400050"]))
        d = r.json()
        self.assertTrue(d["found"])
        self.assertTrue(d["ready"].startswith("Delivery by "))
        self.assertGreater(d["custom_by"], d["ready_by"])

    @mock.patch("store.delivery.lookup", return_value=None)
    def test_unknown(self, _):
        self.assertEqual(self.client.get(reverse("delivery_estimate", args=["999999"])).status_code, 404)

    def test_lead_parsing(self):
        from store.delivery import _lead_days
        self.assertEqual((_lead_days("3–4 weeks"), _lead_days("10 days"), _lead_days("")), (28, 10, 28))


class CouponAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("boss", "b@example.com", "pw")
        self.client.force_login(self.admin)

    def test_sidebar_lists_coupons_reviews_requests_addresses(self):
        r = self.client.get("/admin/")
        for label in ("Coupon codes", "Exchange / alteration requests", "Reviews", "Addresses", "Generate coupon codes"):
            self.assertContains(r, label)

    def test_generate_unique_codes_and_csv(self):
        url = reverse("admin:store_coupon_generate")
        self.assertContains(self.client.get(url), "How many codes")
        data = {"count": 25, "prefix": "diwali", "length": 6, "discount_type": "fixed", "value": "300",
                "min_order_amount": "1500", "uses_per_code": 1, "description": "₹300 off"}
        r = self.client.post(url, data)
        self.assertEqual(r.status_code, 302)
        codes = list(Coupon.objects.filter(code__startswith="DIWALI-").values_list("code", flat=True))
        self.assertEqual(len(codes), 25); self.assertEqual(len(set(codes)), 25)
        c = Coupon.objects.get(code=codes[0])
        self.assertEqual((c.value, c.usage_limit, c.show_in_bag, len(c.code)), (Decimal("300.00"), 1, False, 13))
        self.assertTrue(set(c.code[7:]) <= set("ABCDEFGHJKLMNPQRSTUVWXYZ23456789"))
        r = self.client.post(url, {**data, "count": 3, "download": "1"})
        self.assertEqual(r["Content-Type"], "text/csv")
        self.assertEqual(r.content.decode().count("DIWALI-"), 3)
        self.assertContains(self.client.get(reverse("admin:store_coupon_changelist")), "Generate many codes")

    def test_generator_validates(self):
        r = self.client.post(reverse("admin:store_coupon_generate"), {"count": 0, "length": 6, "discount_type": "fixed", "uses_per_code": 1})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Coupon.objects.exists())


class PolicySettingsTests(TestCase):
    def test_admin_settings_drive_windows_terms_and_dates(self):
        from datetime import timedelta
        from django.utils import timezone
        from store import policies
        from store.models import OrderItem, SiteSettings
        from store.orders import request_options
        SiteSettings.objects.create(store_name="S", exchange_days=14, problem_report_hours=72, delivery_days_min=2, delivery_days_max=3,
                                    unpaid_order_release_minutes=30)
        self.assertEqual(policies.delivery_days(), (2, 3))
        self.assertEqual(policies.unpaid_release_minutes(), 30)
        self.assertTrue(any("within 14 days" in t for t in policies.online_terms()))
        self.assertTrue(any("within 72 hours" in t for t in policies.online_terms()))
        o = Order.objects.create(customer_name="A", customer_email="a@e.com", shipping_address="x", status="delivered")
        Order.objects.filter(pk=o.pk).update(delivered_at=timezone.now() - timedelta(days=10)); o.refresh_from_db()
        p = Product.objects.create(name="P", slug="pp", price=Decimal("1"))
        OrderItem.objects.create(order=o, product=p, product_name="P", unit_price=Decimal("1"), line_total=Decimal("1"), quantity=1)
        self.assertEqual([k for k, _ in request_options(o)], ["exchange"])  # 10 days < 14
        SiteSettings.objects.update(online_order_terms="Line one\n\nLine two")
        self.assertEqual(policies.online_terms(), ["Line one", "Line two"])


class CustomCouponFormTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser("boss2", "b2@example.com", "pw"))

    def post(self, **extra):
        data = {"code": "meera500", "description": "₹500 off", "is_active": "on", "discount_type": "fixed", "value": "500",
                "min_order_amount": "0", "per_customer_limit": "1",
                "starts_at_0": "2026-10-20", "starts_at_1": "00:00:00", "ends_at_0": "2026-10-31", "ends_at_1": "23:59:00"}
        data.update(extra)
        return self.client.post(reverse("admin:store_coupon_add"), data)

    def test_create_own_code_with_period(self):
        r = self.post()
        self.assertEqual(r.status_code, 302, r.content[:2000])
        c = Coupon.objects.get(code="MEERA500")
        from django.utils.timezone import localtime
        self.assertEqual((c.value, localtime(c.starts_at).strftime("%Y-%m-%d %H:%M"), localtime(c.ends_at).strftime("%Y-%m-%d %H:%M")),
                         (Decimal("500.00"), "2026-10-20 00:00", "2026-10-31 23:59"))

    def test_rejects_bad_period_percent_and_spaces(self):
        self.assertContains(self.post(ends_at_0="2026-10-10"), "Must be after the start.")
        self.assertContains(self.post(discount_type="percent", value="150"), "more than 100")
        self.assertContains(self.post(code="MEERA 500"), "no spaces")
        self.assertFalse(Coupon.objects.exists())
