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
