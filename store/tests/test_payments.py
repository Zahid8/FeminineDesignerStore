import hashlib
import hmac
import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from store.models import Order, OrderItem, Product
from store.payments import mark_paid, order_access_key, release_unpaid_orders

SECRET = "whsec_test"


def _sign(body):
    return hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


class _Base(TestCase):
    def setUp(self):
        self.product = Product.objects.create(name="P", slug="p", price=Decimal("1000"), stock_quantity=3)
        self.order = Order.objects.create(
            customer_name="A", customer_email="a@example.com", shipping_address="X",
            total=Decimal("1000.00"), payment_method="razorpay", gateway_order_id="order_1",
        )
        OrderItem.objects.create(order=self.order, product=self.product, product_name="P", unit_price=Decimal("1000"),
                                 line_total=Decimal("1000"), quantity=2)


@override_settings(RAZORPAY_WEBHOOK_SECRET=SECRET, STORE_NOTIFY_EMAIL="")
class WebhookTests(_Base):
    def post(self, event, amount=100000, sign=True, order_id="order_1"):
        body = json.dumps({"event": event, "payload": {"payment": {"entity": {
            "id": "pay_9", "order_id": order_id, "amount": amount, "currency": "INR", "error_description": "Bank declined"}}}}).encode()
        headers = {"HTTP_X_RAZORPAY_SIGNATURE": _sign(body) if sign else "bad"}
        return Client().post(reverse("razorpay_webhook"), body, content_type="application/json", **headers)

    def test_bad_signature_rejected(self):
        self.assertEqual(self.post("payment.captured", sign=False).status_code, 400)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "pending")

    def test_captured_marks_paid_once_and_emails_once(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.post("payment.captured").status_code, 200)
        with self.captureOnCommitCallbacks(execute=True):
            self.post("order.paid")
        self.order.refresh_from_db()
        self.assertEqual((self.order.payment_status, self.order.status, self.order.gateway_payment_id), ("paid", "confirmed", "pay_9"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("payment received", mail.outbox[0].subject)

    def test_amount_mismatch_not_paid(self):
        self.post("payment.captured", amount=100)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "pending")

    def test_unknown_order_ignored(self):
        self.assertEqual(self.post("payment.captured", order_id="order_x").status_code, 200)

    def test_failed_event(self):
        self.post("payment.failed")
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "failed")
        self.assertIn("Bank declined", self.order.payment_notes)

    def test_webhook_url_not_swallowed_by_order_route(self):
        self.assertEqual(reverse("razorpay_webhook"), "/razorpay/webhook/")

    def test_get_not_allowed(self):
        self.assertEqual(Client().get(reverse("razorpay_webhook")).status_code, 405)


@override_settings(STORE_NOTIFY_EMAIL="")
class ReleaseUnpaidTests(_Base):
    def setUp(self):
        super().setUp()
        Order.objects.filter(pk=self.order.pk).update(created_at=timezone.now() - timedelta(minutes=90))
        self.product.stock_quantity = 1  # 2 already taken by the order
        self.product.save()

    def test_old_unpaid_order_cancelled_and_restocked(self):
        self.assertEqual(release_unpaid_orders(60), [self.order.order_number])
        self.order.refresh_from_db(); self.product.refresh_from_db()
        self.assertEqual((self.order.status, self.product.stock_quantity), ("cancelled", 3))
        self.assertEqual(release_unpaid_orders(60), [])  # idempotent

    def test_recent_or_paid_or_manual_orders_untouched(self):
        self.assertEqual(release_unpaid_orders(120), [])
        Order.objects.filter(pk=self.order.pk).update(payment_status="paid")
        self.assertEqual(release_unpaid_orders(60), [])
        Order.objects.filter(pk=self.order.pk).update(payment_status="pending", payment_method="manual_upi")
        self.assertEqual(release_unpaid_orders(60), [])

    def test_late_payment_revives_order_and_retakes_stock(self):
        release_unpaid_orders(60)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertTrue(mark_paid(self.order.pk, "pay_late", source="webhook"))
        self.order.refresh_from_db(); self.product.refresh_from_db()
        self.assertEqual((self.order.status, self.order.payment_status, self.product.stock_quantity), ("confirmed", "paid", 1))
        self.assertIn("auto-cancelled", self.order.payment_notes)
        self.assertFalse(mark_paid(self.order.pk, "pay_late"))

    def test_command(self):
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command("release_unpaid_orders", stdout=out)
        self.assertIn("Released 1", out.getvalue())


@override_settings(RAZORPAY_KEY_ID="k", RAZORPAY_KEY_SECRET="s")
class OrderAccessTests(_Base):
    def url(self, name="order_success", key=None):
        u = reverse(name, kwargs={"order_number": self.order.order_number})
        return u + (f"?k={key}" if key else "")

    def test_stranger_gets_404(self):
        self.assertEqual(Client().get(self.url()).status_code, 404)
        self.assertEqual(Client().get(self.url(key="wrong")).status_code, 404)
        self.assertEqual(Client().get(self.url("razorpay_payment")).status_code, 404)

    def test_signed_link_owner_and_staff_allowed(self):
        self.assertEqual(Client().get(self.url(key=order_access_key(self.order.order_number))).status_code, 200)
        owner = User.objects.create_user("o", password="x")
        Order.objects.filter(pk=self.order.pk).update(customer_user=owner)
        c = Client(); c.force_login(owner)
        self.assertEqual(c.get(self.url()).status_code, 200)
        staff = User.objects.create_user("s", password="x", is_staff=True)
        c = Client(); c.force_login(staff)
        self.assertEqual(c.get(self.url()).status_code, 200)

    def test_unpaid_online_order_shows_pay_now(self):
        r = Client().get(self.url(key=order_access_key(self.order.order_number)))
        self.assertContains(r, "Almost there")
        self.assertContains(r, reverse("razorpay_payment", kwargs={"order_number": self.order.order_number}))

    def test_cancelled_order_says_so_and_cannot_pay(self):
        Order.objects.filter(pk=self.order.pk).update(status="cancelled")
        key = order_access_key(self.order.order_number)
        self.assertContains(Client().get(self.url(key=key)), "Order cancelled")
        r = Client().get(self.url("razorpay_payment", key=key))
        self.assertEqual(r.status_code, 302)

    def test_checkout_remembers_order_in_session(self):
        p = Product.objects.create(name="Q", slug="q", price=Decimal("10"), stock_quantity=2)
        c = Client()
        c.post(reverse("add_to_cart", kwargs={"product_id": p.pk}), {"quantity": 1})
        c.post(reverse("checkout"), {"customer_name": "A", "customer_email": "a@a.com", "customer_phone": "9876543210",
                                     "shipping_address": "Addr", "payment_method": "manual_upi"})
        order = Order.objects.exclude(pk=self.order.pk).get()
        self.assertEqual(c.get(reverse("order_success", kwargs={"order_number": order.order_number})).status_code, 200)


@override_settings(STORE_NOTIFY_EMAIL="")
class LatePaymentCouponTests(_Base):
    def test_single_use_coupon_not_counted_twice(self):
        from store.models import Coupon
        from store import coupons

        Coupon.objects.create(code="ONCE", discount_type="fixed", value=Decimal("100"), usage_limit=1, per_customer_limit=0)
        Order.objects.filter(pk=self.order.pk).update(coupon_code="ONCE", coupon_discount=Decimal("100"), discount_total=Decimal("100"),
                                                     subtotal=Decimal("1100"), created_at=timezone.now() - timedelta(minutes=90))
        release_unpaid_orders(60)
        # Someone else uses the freed-up coupon...
        Order.objects.create(customer_name="B", customer_email="b@example.com", shipping_address="y", coupon_code="ONCE")
        # ...then the late payment for the first order arrives.
        with self.captureOnCommitCallbacks(execute=True):
            mark_paid(self.order.pk, "pay_late", source="webhook")
        self.order.refresh_from_db()
        self.assertEqual((self.order.status, self.order.coupon_code, self.order.total), ("confirmed", "", Decimal("1000.00")))
        self.assertIn("discount was honoured", self.order.payment_notes)
        self.assertEqual(coupons._uses(Coupon.objects.get(code="ONCE")).count(), 1)
