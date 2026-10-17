import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from store.models import Order, OrderEvent, OrderItem, OrderRequest, Product
from store.orders import request_options, timeline
from store.payments import order_access_key


@override_settings(STORE_NOTIFY_EMAIL="shop@example.com")
class _Base(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("asha", email="asha@example.com", password="pw")
        self.client.force_login(self.user)
        self.p = Product.objects.create(name="Blouse", slug="b", price=Decimal("2200"), stock_quantity=5)
        self.order = Order.objects.create(customer_name="Asha", customer_email="asha@example.com", shipping_address="X",
                                          customer_user=self.user, total=Decimal("2200"), subtotal=Decimal("2200"))
        self.item = OrderItem.objects.create(order=self.order, product=self.p, product_name="Blouse", unit_price=Decimal("2200"),
                                             line_total=Decimal("2200"), quantity=1, size="M")
        self.mtm = None

    def detail(self):
        return self.client.get(reverse("account_order_detail", kwargs={"order_number": self.order.order_number}))


class TimelineTests(_Base):
    def test_events_logged_with_dates_and_stamps(self):
        for s in ("confirmed", "processing", "shipped", "delivered"):
            self.order.status = s
            self.order.save()
        self.order.refresh_from_db()
        self.assertEqual(list(self.order.events.values_list("status", flat=True)), ["pending", "confirmed", "processing", "shipped", "delivered"])
        self.assertIsNotNone(self.order.shipped_at)
        self.assertIsNotNone(self.order.delivered_at)
        steps = timeline(self.order)
        self.assertTrue(all(st["done"] and st["at"] for st in steps))

    def test_update_fields_save_still_stamps(self):
        self.order.status = "shipped"
        self.order.save(update_fields=["status"])
        self.order.refresh_from_db()
        self.assertIsNotNone(self.order.shipped_at)

    def test_courier_shown_once_shipped(self):
        Order.objects.filter(pk=self.order.pk).update(courier_name="Delhivery", tracking_number="AWB123", tracking_url="https://track.example/AWB123")
        self.order.refresh_from_db(); self.order.status = "shipped"; self.order.save()
        r = self.detail()
        self.assertContains(r, "AWB123")
        self.assertContains(r, "https://track.example/AWB123")
        self.assertContains(r, "On the way")

    def test_thumbnails_and_price_details(self):
        r = self.detail()
        self.assertContains(r, 'class="fd-order-thumb"')
        self.assertContains(r, "Price details")
        self.assertContains(self.client.get(reverse("account_orders")), 'class="fd-order-thumbs"')


class CancelTests(_Base):
    def test_customer_cancels_restocks_and_emails(self):
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(reverse("order_cancel", kwargs={"order_number": self.order.order_number}), {"reason": "changed_mind"})
        self.assertEqual(r.status_code, 302)
        self.order.refresh_from_db(); self.p.refresh_from_db()
        self.assertEqual((self.order.status, self.order.cancelled_by, self.p.stock_quantity), ("cancelled", "customer", 6))
        self.assertEqual(self.order.cancel_reason, "I changed my mind")
        self.assertEqual(self.order.events.last().status, "cancelled")
        self.assertEqual(len(mail.outbox), 2)

    def test_paid_order_flags_refund(self):
        Order.objects.filter(pk=self.order.pk).update(payment_status="paid", status="confirmed")
        self.client.post(reverse("order_cancel", kwargs={"order_number": self.order.order_number}), {"reason": "other"})
        self.order.refresh_from_db()
        self.assertIn("REFUND DUE", self.order.payment_notes)
        self.assertContains(self.detail(), "refund")

    def test_cannot_cancel_once_processing_or_without_reason(self):
        self.client.post(reverse("order_cancel", kwargs={"order_number": self.order.order_number}), {"reason": ""})
        self.order.refresh_from_db(); self.assertEqual(self.order.status, "pending")
        Order.objects.filter(pk=self.order.pk).update(status="processing")
        self.client.post(reverse("order_cancel", kwargs={"order_number": self.order.order_number}), {"reason": "other"})
        self.order.refresh_from_db(); self.assertEqual(self.order.status, "processing")
        self.assertNotContains(self.detail(), "Cancel this order")

    def test_stranger_cannot_cancel(self):
        c = Client()
        r = c.post(reverse("order_cancel", kwargs={"order_number": self.order.order_number}), {"reason": "other"})
        self.assertEqual(r.status_code, 404)

    def test_guest_with_signed_link_can_cancel(self):
        c = Client()
        c.post(reverse("order_cancel", kwargs={"order_number": self.order.order_number}) + f"?k={order_access_key(self.order.order_number)}", {"reason": "other"})
        self.order.refresh_from_db(); self.assertEqual(self.order.status, "cancelled")

    def test_staff_cancel_via_api_restocks(self):
        with override_settings(WEBSTORE_API_TOKEN="t"):
            r = Client().post(reverse("api_online_order_detail", args=[self.order.order_number]), json.dumps({"status": "cancelled"}),
                              content_type="application/json", HTTP_AUTHORIZATION="Bearer t")
        self.assertEqual(r.status_code, 200)
        self.p.refresh_from_db(); self.assertEqual(self.p.stock_quantity, 6)
        self.assertEqual(r.json()["order"]["cancellation"]["by"], "staff")


class RequestTests(_Base):
    def deliver(self, days_ago=1):
        self.order.status = "delivered"; self.order.save()
        Order.objects.filter(pk=self.order.pk).update(delivered_at=timezone.now() - timedelta(days=days_ago))
        self.order.refresh_from_db()

    def test_windows(self):
        self.assertEqual(request_options(self.order), [])
        self.deliver(1)
        self.assertEqual([k for k, _ in request_options(self.order)], ["exchange", "problem"])
        self.deliver(5)
        self.assertEqual([k for k, _ in request_options(self.order)], ["exchange"])
        self.deliver(9)
        self.assertEqual(request_options(self.order), [])

    def test_alteration_for_made_to_measure(self):
        OrderItem.objects.filter(pk=self.item.pk).update(customization={"measurements": {"chest": "36"}})
        self.deliver(20)
        self.assertEqual([k for k, _ in request_options(self.order)], ["alteration"])

    def test_exchange_request_flow(self):
        self.deliver(1)
        url = reverse("order_request", kwargs={"order_number": self.order.order_number})
        self.assertContains(self.client.get(url), "Size you would like instead")
        r = self.client.post(url, {"kind": "exchange", "reason": "size", "items": [self.item.pk], "preferred_size": "L", "details": "too tight"})
        self.assertEqual(r.status_code, 302)
        req = OrderRequest.objects.get()
        self.assertEqual((req.kind, req.preferred_size, list(req.items.all())), ("exchange", "L", [self.item]))
        self.assertEqual(len(mail.outbox), 1)
        self.assertContains(self.detail(), "Your requests")
        again = self.client.post(url, {"kind": "exchange", "reason": "size", "items": [self.item.pk]})
        self.assertContains(again, "already have an open request")

    def test_request_needs_item_and_reason(self):
        self.deliver(1)
        url = reverse("order_request", kwargs={"order_number": self.order.order_number})
        self.assertContains(self.client.post(url, {"kind": "exchange", "reason": "size"}), "Choose at least one item")
        self.assertFalse(OrderRequest.objects.exists())

    def test_not_delivered_redirects(self):
        r = self.client.get(reverse("order_request", kwargs={"order_number": self.order.order_number}))
        self.assertEqual(r.status_code, 302)


class BuyAgainTests(_Base):
    def test_adds_to_cart(self):
        r = self.client.post(reverse("order_buy_again", kwargs={"order_number": self.order.order_number}))
        self.assertRedirects(r, reverse("cart_detail"), fetch_redirect_response=False)
        self.assertEqual(sum(l["quantity"] for l in self.client.session["femdes_cart"].values()), 1)

    def test_unavailable_skipped(self):
        Product.objects.filter(pk=self.p.pk).update(is_active=False)
        r = self.client.post(reverse("order_buy_again", kwargs={"order_number": self.order.order_number}))
        self.assertNotEqual(r.url, reverse("cart_detail"))


class TrackPageTests(_Base):
    def test_guest_track_then_manage(self):
        c = Client()
        r = c.post(reverse("order_track"), {"order_number": self.order.order_number, "contact": "asha@example.com"})
        self.assertContains(r, "Manage this order")
        self.assertEqual(c.get(reverse("order_success", kwargs={"order_number": self.order.order_number})).status_code, 200)
