"""Tests for Razorpay payment gateway integration."""

from decimal import Decimal
from unittest import mock

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from store.models import Category, Order, Product

RAZORPAY_SETTINGS = {"RAZORPAY_KEY_ID": "key", "RAZORPAY_KEY_SECRET": "secret"}


class RazorpayOffTests(TestCase):
    """When Razorpay keys are empty, manual UPI flow is used."""

    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="Blouses", slug="blouses")
        self.product = Product.objects.create(
            category=self.category, name="Test", slug="rz-off",
            sku="SKU-RZ", price=Decimal("100"), stock_quantity=5, is_active=True,
        )

    def test_checkout_redirects_to_order_success_when_razorpay_off(self):
        self.client.post(
            reverse("add_to_cart", kwargs={"product_id": self.product.pk}),
            {"quantity": 1},
        )
        response = self.client.post(reverse("checkout"), {
            "customer_name": "A", "customer_email": "a@a.com",
            "shipping_address": "Addr",
        })
        self.assertRedirects(response, reverse(
            "order_success", kwargs={"order_number": Order.objects.first().order_number}
        ))


class RazorpayEnabledTests(TestCase):
    """Razorpay payment flow with mocked SDK."""

    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="Blouses", slug="blouses")
        self.product = Product.objects.create(
            category=self.category, name="Test", slug="rz-on",
            sku="SKU-RZ2", price=Decimal("100"), stock_quantity=5, is_active=True,
        )

    def _create_order(self, **kwargs):
        return Order.objects.create(
            customer_name="A", customer_email="a@a.com",
            shipping_address="Addr", total=Decimal("100"), **kwargs,
        )

    @mock.patch("store.views._get_razorpay_client")
    def test_razorpay_payment_creates_order_with_paise(self, mock_fn):
        mock_client = mock.MagicMock()
        mock_client.order.create.return_value = {"id": "order_test123"}
        mock_fn.return_value = mock_client

        with override_settings(**RAZORPAY_SETTINGS):
            order = self._create_order()
            self.client.get(reverse("razorpay_payment", kwargs={
                "order_number": order.order_number,
            }))

        call_args = mock_client.order.create.call_args[0][0]
        self.assertEqual(call_args["amount"], 10000)
        self.assertEqual(call_args["currency"], "INR")
        self.assertEqual(call_args["receipt"], order.order_number)

    @mock.patch("store.views._get_razorpay_client")
    def test_repeated_load_reuses_gateway_order_id(self, mock_fn):
        mock_client = mock.MagicMock()
        mock_client.order.create.return_value = {"id": "order_test456"}
        mock_fn.return_value = mock_client

        with override_settings(**RAZORPAY_SETTINGS):
            order = self._create_order()
            self.client.get(reverse("razorpay_payment", kwargs={
                "order_number": order.order_number,
            }))
            order.refresh_from_db()
            self.assertEqual(order.gateway_order_id, "order_test456")

            # Second load should reuse
            mock_client.order.create.reset_mock()
            self.client.get(reverse("razorpay_payment", kwargs={
                "order_number": order.order_number,
            }))
            mock_client.order.create.assert_not_called()

    @mock.patch("store.views._get_razorpay_client")
    def test_valid_verification_marks_paid(self, mock_fn):
        mock_client = mock.MagicMock()
        mock_client.utility.verify_payment_signature.return_value = True
        mock_fn.return_value = mock_client

        with override_settings(**RAZORPAY_SETTINGS):
            order = self._create_order(gateway_order_id="order_789")
            response = self.client.post(
                reverse("razorpay_verify", kwargs={"order_number": order.order_number}),
                {
                    "razorpay_order_id": "order_789",
                    "razorpay_payment_id": "pay_ABC",
                    "razorpay_signature": "sig",
                },
            )
            self.assertRedirects(response, reverse(
                "order_success", kwargs={"order_number": order.order_number}
            ))
            order.refresh_from_db()
            self.assertEqual(order.payment_status, "paid")
            self.assertEqual(order.payment_method, "razorpay")
            self.assertEqual(order.gateway_payment_id, "pay_ABC")

    @mock.patch("store.views._get_razorpay_client")
    def test_mismatched_order_id_does_not_mark_paid(self, mock_fn):
        mock_client = mock.MagicMock()
        mock_fn.return_value = mock_client

        with override_settings(**RAZORPAY_SETTINGS):
            order = self._create_order(gateway_order_id="order_real")
            self.client.post(
                reverse("razorpay_verify", kwargs={"order_number": order.order_number}),
                {
                    "razorpay_order_id": "order_wrong",
                    "razorpay_payment_id": "pay_XYZ",
                    "razorpay_signature": "sig",
                },
            )
            order.refresh_from_db()
            self.assertNotEqual(order.payment_status, "paid")

    def test_missing_payment_data_does_not_500(self):
        with override_settings(**RAZORPAY_SETTINGS):
            order = self._create_order()
            response = self.client.post(
                reverse("razorpay_verify", kwargs={"order_number": order.order_number}),
                {},
            )
            self.assertNotEqual(response.status_code, 500)

    @mock.patch("store.views._get_razorpay_client")
    def test_get_verify_does_not_redirect_to_success(self, mock_fn):
        mock_client = mock.MagicMock()
        mock_client.order.create.return_value = {"id": "order_z"}
        mock_fn.return_value = mock_client
        with override_settings(**RAZORPAY_SETTINGS):
            order = self._create_order()
            response = self.client.get(
                reverse("razorpay_verify", kwargs={"order_number": order.order_number}),
            )
            self.assertEqual(response.status_code, 302)
            self.assertIn("razorpay", response.url)
            self.assertIn(order.order_number, response.url)
