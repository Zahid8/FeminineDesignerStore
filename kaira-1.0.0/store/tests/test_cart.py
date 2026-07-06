"""Tests for session-backed cart services."""

from decimal import Decimal

from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase

from store.models import Category, Product
from store.services import (
    CART_SESSION_KEY,
    add_to_cart,
    create_order_from_cart,
    get_cart,
    get_cart_summary,
    remove_cart_item,
    subscribe_newsletter,
    update_cart_item,
)


def _make_request():
    factory = RequestFactory()
    request = factory.get("/")
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    request.session.save()
    return request


class CartAddTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Dresses", slug="dresses")
        self.product = Product.objects.create(
            category=self.category,
            name="Test Dress",
            slug="test-dress",
            sku="SKU-CART-001",
            price=Decimal("50.00"),
            stock_quantity=10,
            is_active=True,
        )

    def test_add_to_cart(self):
        request = _make_request()
        add_to_cart(request, self.product, quantity=2)
        cart = get_cart(request)
        self.assertEqual(len(cart), 1)
        key = list(cart.keys())[0]
        self.assertEqual(cart[key]["quantity"], 2)
        self.assertEqual(cart[key]["product_id"], self.product.pk)

    def test_add_inactive_product_fails(self):
        self.product.is_active = False
        self.product.save()
        request = _make_request()
        with self.assertRaises(ValueError):
            add_to_cart(request, self.product)

    def test_add_out_of_stock_product_fails(self):
        self.product.stock_quantity = 0
        self.product.save()
        request = _make_request()
        with self.assertRaises(ValueError):
            add_to_cart(request, self.product)

    def test_add_exceeds_stock_fails(self):
        request = _make_request()
        with self.assertRaises(ValueError):
            add_to_cart(request, self.product, quantity=999)

    def test_add_multiple_times_accumulates(self):
        request = _make_request()
        add_to_cart(request, self.product, quantity=2)
        add_to_cart(request, self.product, quantity=3)
        cart = get_cart(request)
        key = list(cart.keys())[0]
        self.assertEqual(cart[key]["quantity"], 5)

    def test_different_variants_get_separate_keys(self):
        request = _make_request()
        add_to_cart(request, self.product, quantity=1, color="Red", size="M")
        add_to_cart(request, self.product, quantity=1, color="Blue", size="L")
        cart = get_cart(request)
        self.assertEqual(len(cart), 2)


class CartUpdateTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Dresses", slug="dresses")
        self.product = Product.objects.create(
            category=self.category,
            name="Test Dress",
            slug="test-dress-up",
            sku="SKU-CART-002",
            price=Decimal("50.00"),
            stock_quantity=10,
            is_active=True,
        )

    def test_update_quantity(self):
        request = _make_request()
        add_to_cart(request, self.product, quantity=2)
        cart = get_cart(request)
        key = list(cart.keys())[0]
        update_cart_item(request, key, 5)
        cart = get_cart(request)
        self.assertEqual(cart[key]["quantity"], 5)

    def test_update_quantity_zero_removes(self):
        request = _make_request()
        add_to_cart(request, self.product, quantity=2)
        cart = get_cart(request)
        key = list(cart.keys())[0]
        update_cart_item(request, key, 0)
        cart = get_cart(request)
        self.assertNotIn(key, cart)

    def test_update_missing_key_does_not_crash(self):
        request = _make_request()
        update_cart_item(request, "nonexistent_key", 5)  # should not raise

    def test_update_exceeding_stock_fails(self):
        request = _make_request()
        add_to_cart(request, self.product, quantity=2)
        cart = get_cart(request)
        key = list(cart.keys())[0]
        with self.assertRaises(ValueError):
            update_cart_item(request, key, 999)


class CartRemoveTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Dresses", slug="dresses")
        self.product = Product.objects.create(
            category=self.category,
            name="Test Dress",
            slug="test-dress-rm",
            sku="SKU-CART-003",
            price=Decimal("50.00"),
            stock_quantity=10,
            is_active=True,
        )

    def test_remove_item(self):
        request = _make_request()
        add_to_cart(request, self.product, quantity=2)
        cart = get_cart(request)
        key = list(cart.keys())[0]
        remove_cart_item(request, key)
        cart = get_cart(request)
        self.assertNotIn(key, cart)

    def test_remove_missing_key_does_not_crash(self):
        request = _make_request()
        remove_cart_item(request, "nonexistent")  # should not raise


class CartSummaryTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Dresses", slug="dresses")
        self.product = Product.objects.create(
            category=self.category,
            name="Test Dress",
            slug="test-dress-sum",
            sku="SKU-CART-004",
            price=Decimal("50.00"),
            stock_quantity=10,
            is_active=True,
        )

    def test_empty_cart(self):
        request = _make_request()
        summary = get_cart_summary(request)
        self.assertEqual(summary["item_count"], 0)
        self.assertEqual(summary["total"], Decimal("0.00"))

    def test_cart_with_items(self):
        request = _make_request()
        add_to_cart(request, self.product, quantity=2)
        summary = get_cart_summary(request)
        self.assertEqual(summary["item_count"], 2)
        self.assertEqual(summary["total"], Decimal("100.00"))

    def test_stale_product_skipped(self):
        request = _make_request()
        add_to_cart(request, self.product, quantity=1)
        # Deactivate product
        self.product.is_active = False
        self.product.save()
        summary = get_cart_summary(request)
        self.assertEqual(summary["item_count"], 0)
        self.assertEqual(summary["total"], Decimal("0.00"))


class CheckoutTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Dresses", slug="dresses")
        self.product = Product.objects.create(
            category=self.category,
            name="Test Dress",
            slug="test-dress-co",
            sku="SKU-CART-005",
            price=Decimal("50.00"),
            stock_quantity=10,
            is_active=True,
        )

    def test_create_order_decrements_stock(self):
        request = _make_request()
        add_to_cart(request, self.product, quantity=3)
        checkout_data = {
            "customer_name": "Alice",
            "customer_email": "alice@example.com",
            "customer_phone": "",
            "shipping_address": "123 Main St",
            "notes": "",
        }
        order = create_order_from_cart(request, checkout_data)
        self.assertIsNotNone(order.order_number)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 7)
        # Cart should be cleared
        self.assertEqual(len(get_cart(request)), 0)

    def test_checkout_empty_cart_fails(self):
        request = _make_request()
        checkout_data = {
            "customer_name": "Alice",
            "customer_email": "alice@example.com",
            "shipping_address": "123 Main St",
        }
        with self.assertRaises(ValueError):
            create_order_from_cart(request, checkout_data)

    def test_checkout_insufficient_stock_fails(self):
        request = _make_request()
        add_to_cart(request, self.product, quantity=5)
        # Reduce stock after adding to cart
        self.product.stock_quantity = 2
        self.product.save()
        checkout_data = {
            "customer_name": "Alice",
            "customer_email": "alice@example.com",
            "shipping_address": "123 Main St",
        }
        with self.assertRaises(ValueError):
            create_order_from_cart(request, checkout_data)
        # Cart should still be intact
        cart = get_cart(request)
        self.assertEqual(len(cart), 1)

    def test_order_item_snapshots(self):
        request = _make_request()
        add_to_cart(request, self.product, quantity=2)
        checkout_data = {
            "customer_name": "Bob",
            "customer_email": "bob@example.com",
            "shipping_address": "456 Oak Ave",
        }
        order = create_order_from_cart(request, checkout_data)
        item = order.items.first()
        self.assertEqual(item.product_name, self.product.name)
        self.assertEqual(item.sku, self.product.sku)
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.unit_price, Decimal("50.00"))
        self.assertEqual(item.line_total, Decimal("100.00"))


class NewsletterTests(TestCase):
    def test_subscribe_new(self):
        sub = subscribe_newsletter("test@example.com")
        self.assertTrue(sub.is_active)

    def test_subscribe_duplicate_does_not_crash(self):
        subscribe_newsletter("dup@example.com")
        sub2 = subscribe_newsletter("dup@example.com")
        self.assertTrue(sub2.is_active)

    def test_subscribe_reactivates_inactive(self):
        sub = subscribe_newsletter("react@example.com")
        sub.is_active = False
        sub.save()
        sub2 = subscribe_newsletter("react@example.com")
        self.assertTrue(sub2.is_active)
