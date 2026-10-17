"""Online-orders API consumed by the Feminine Designer billing app."""
import json
from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from store.models import Category, Order, OrderItem, Product

AUTH = {"HTTP_AUTHORIZATION": "Bearer test-token"}


@override_settings(WEBSTORE_API_TOKEN="test-token")
class OnlineOrdersApiTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(name="Silk", slug="silk-api", is_active=True)
        self.product = Product.objects.create(category=cat, name="Zari Blouse", slug="zari-api", sku="API-1",
                                              price=Decimal("2000"), stock_quantity=5, is_active=True)
        self.order = Order.objects.create(customer_name="Asha Rao", customer_email="asha@example.com",
                                          customer_phone="9876543210", shipping_address="12 MG Road, Pune",
                                          subtotal=Decimal("2400"), total=Decimal("2400"), status="pending")
        OrderItem.objects.create(order=self.order, product=self.product, product_name="Zari Blouse", sku="API-1",
                                 unit_price=Decimal("2400"), quantity=1, line_total=Decimal("2400"),
                                 size="Made to measure",
                                 customization={"measurements": {"chest": "36.00", "length": "15.00"}, "sleeve_style": "cap", "notes": "padded"})
        self.other = Order.objects.create(customer_name="Meera", customer_email="m@example.com", shipping_address="x",
                                          total=Decimal("500"), status="shipped")

    def test_requires_token(self):
        self.assertEqual(self.client.get(reverse("api_online_orders")).status_code, 401)
        self.assertEqual(self.client.get(reverse("api_online_orders"), HTTP_AUTHORIZATION="Bearer wrong").status_code, 401)
        with override_settings(WEBSTORE_API_TOKEN=""):
            self.assertEqual(self.client.get(reverse("api_online_orders"), **AUTH).status_code, 503)

    def test_list_serializes_orders_with_items_and_measurements(self):
        data = self.client.get(reverse("api_online_orders"), **AUTH).json()
        self.assertEqual([o["order_number"] for o in data["orders"]], [self.other.order_number, self.order.order_number])
        order = data["orders"][1]
        self.assertEqual(order["customer"], {"name": "Asha Rao", "email": "asha@example.com", "phone": "9876543210", "account_id": None})
        self.assertEqual(order["total"], "2400.00")
        self.assertTrue(order["has_made_to_measure"])
        item = order["items"][0]
        self.assertEqual(item["customization"]["measurements"]["chest"], "36.00")
        self.assertIn({"label": "Chest", "value": "36 in"}, item["customization_summary"])
        self.assertIn({"label": "Sleeves", "value": "Cap sleeve"}, item["customization_summary"])
        self.assertTrue(order["links"]["staff"].endswith(f"/staff/orders/{self.order.order_number}/"))
        self.assertEqual([s["value"] for s in data["statuses"]][:2], ["pending", "confirmed"])

    def test_filters(self):
        api = reverse("api_online_orders")
        self.assertEqual(len(self.client.get(api, {"status": "shipped"}, **AUTH).json()["orders"]), 1)
        self.assertEqual(len(self.client.get(api, {"status": "bogus"}, **AUTH).json()["orders"]), 0)
        self.assertEqual(len(self.client.get(api, {"q": "asha"}, **AUTH).json()["orders"]), 1)
        self.assertEqual(self.client.get(api, {"since": "not-a-date"}, **AUTH).status_code, 400)
        self.assertEqual(len(self.client.get(api, {"since": "2000-01-01T00:00:00Z"}, **AUTH).json()["orders"]), 2)
        self.assertEqual(len(self.client.get(api, {"since": "2999-01-01T00:00:00Z"}, **AUTH).json()["orders"]), 0)
        page = self.client.get(api, {"limit": 1}, **AUTH).json()
        self.assertEqual(len(page["orders"]), 1)
        self.assertTrue(page["has_more"])

    def test_detail_and_status_update(self):
        url = reverse("api_online_order_detail", args=[self.order.order_number.lower()])
        self.assertEqual(self.client.get(url, **AUTH).json()["order"]["status"], "pending")
        response = self.client.post(url, json.dumps({"status": "confirmed", "payment_status": "paid", "payment_notes": "UPI ref 123"}),
                                    content_type="application/json", **AUTH)
        self.assertEqual(response.status_code, 200, response.content)
        self.order.refresh_from_db()
        self.assertEqual((self.order.status, self.order.payment_status, self.order.payment_notes), ("confirmed", "paid", "UPI ref 123"))
        self.assertIsNotNone(self.order.paid_at)
        self.assertEqual(response.json()["order"]["status_label"], "Confirmed")

    def test_update_validation(self):
        url = reverse("api_online_order_detail", args=[self.order.order_number])
        self.assertEqual(self.client.post(url, json.dumps({"status": "teleported"}), content_type="application/json", **AUTH).status_code, 400)
        self.assertEqual(self.client.post(url, "{", content_type="application/json", **AUTH).status_code, 400)
        self.assertEqual(self.client.post(url, json.dumps({}), content_type="application/json", **AUTH).status_code, 400)
        self.assertEqual(self.client.get(reverse("api_online_order_detail", args=["FD-NOPE"]), **AUTH).status_code, 404)
        self.assertEqual(self.client.post(url, json.dumps({"status": "confirmed"}), content_type="application/json").status_code, 401)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "pending")

    def test_robots_blocks_api(self):
        self.assertIn("Disallow: /api/", self.client.get("/robots.txt").content.decode())
