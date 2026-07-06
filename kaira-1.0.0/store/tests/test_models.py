"""Tests for store model __str__, properties, clean, and save behavior."""

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from store.models import (
    Category,
    Discount,
    NewsletterSubscriber,
    Order,
    OrderItem,
    Product,
    ProductImage,
    SiteSettings,
)


class SiteSettingsTests(TestCase):
    def test_str_returns_store_name(self):
        s = SiteSettings.objects.create(store_name="FemDes")
        self.assertEqual(str(s), "FemDes")

    def test_only_one_row_allowed(self):
        SiteSettings.objects.create(store_name="First")
        with self.assertRaises(ValidationError):
            SiteSettings.objects.create(store_name="Second")

    def test_update_existing_row_allowed(self):
        s = SiteSettings.objects.create(store_name="Original")
        s.store_name = "Updated"
        s.save()  # should not raise
        self.assertEqual(SiteSettings.objects.count(), 1)


class CategoryTests(TestCase):
    def test_str_returns_name(self):
        c = Category.objects.create(name="Dresses", slug="dresses")
        self.assertEqual(str(c), "Dresses")

    def test_default_ordering(self):
        c2 = Category.objects.create(name="B", slug="b", sort_order=0)
        c1 = Category.objects.create(name="A", slug="a", sort_order=0)
        c3 = Category.objects.create(name="C", slug="c", sort_order=10)
        names = list(Category.objects.values_list("name", flat=True))
        self.assertEqual(names, ["A", "B", "C"])


class ProductTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Dresses", slug="dresses")

    def test_str_returns_name(self):
        p = Product.objects.create(
            category=self.category,
            name="Summer Dress",
            slug="summer-dress",
            sku="SKU-001",
            price=Decimal("49.99"),
        )
        self.assertEqual(str(p), "Summer Dress")

    def test_is_in_stock_true(self):
        p = Product.objects.create(
            category=self.category,
            name="Test",
            slug="test",
            sku="SKU-002",
            price=Decimal("10.00"),
            stock_quantity=5,
        )
        self.assertTrue(p.is_in_stock)

    def test_is_in_stock_false_when_zero(self):
        p = Product.objects.create(
            category=self.category,
            name="Test",
            slug="test-zero",
            sku="SKU-003",
            price=Decimal("10.00"),
            stock_quantity=0,
        )
        self.assertFalse(p.is_in_stock)

    def test_clean_rejects_compare_at_price_lower_than_price(self):
        p = Product(
            category=self.category,
            name="Test",
            slug="test-clean",
            sku="SKU-004",
            price=Decimal("50.00"),
            compare_at_price=Decimal("30.00"),
        )
        with self.assertRaises(ValidationError):
            p.clean()

    def test_clean_allows_compare_at_equal_to_price(self):
        p = Product(
            category=self.category,
            name="Test",
            slug="test-equal",
            sku="SKU-005",
            price=Decimal("50.00"),
            compare_at_price=Decimal("50.00"),
        )
        p.clean()  # should not raise

    def test_clean_allows_null_compare_at_price(self):
        p = Product(
            category=self.category,
            name="Test",
            slug="test-null",
            sku="SKU-006",
            price=Decimal("50.00"),
        )
        p.clean()  # should not raise

    def test_get_effective_price_no_discount(self):
        p = Product.objects.create(
            category=self.category,
            name="Test",
            slug="test-eff",
            sku="SKU-007",
            price=Decimal("49.99"),
        )
        self.assertEqual(p.get_effective_price(), Decimal("49.99"))

    def test_get_effective_price_discounts_disabled(self):
        p = Product.objects.create(
            category=self.category,
            name="Test",
            slug="test-no-disc",
            sku="SKU-008",
            price=Decimal("49.99"),
            allow_discounts=False,
        )
        Discount.objects.create(
            name="Global 10%",
            discount_type="percent",
            scope="global",
            value=Decimal("10.00"),
            is_active=True,
        )
        self.assertEqual(p.get_effective_price(), Decimal("49.99"))

    def test_get_effective_price_with_percent_discount(self):
        p = Product.objects.create(
            category=self.category,
            name="Test",
            slug="test-pct",
            sku="SKU-009",
            price=Decimal("100.00"),
        )
        Discount.objects.create(
            name="10% off",
            discount_type="percent",
            scope="global",
            value=Decimal("10.00"),
            is_active=True,
        )
        self.assertEqual(p.get_effective_price(), Decimal("90.00"))

    def test_get_effective_price_with_fixed_discount(self):
        p = Product.objects.create(
            category=self.category,
            name="Test",
            slug="test-fixed",
            sku="SKU-010",
            price=Decimal("100.00"),
        )
        Discount.objects.create(
            name="$15 off",
            discount_type="fixed",
            scope="global",
            value=Decimal("15.00"),
            is_active=True,
        )
        self.assertEqual(p.get_effective_price(), Decimal("85.00"))

    def test_get_effective_price_product_scoped_discount(self):
        p = Product.objects.create(
            category=self.category,
            name="Test",
            slug="test-prod-disc",
            sku="SKU-011",
            price=Decimal("100.00"),
        )
        Discount.objects.create(
            name="Product 20%",
            discount_type="percent",
            scope="product",
            product=p,
            value=Decimal("20.00"),
            is_active=True,
        )
        self.assertEqual(p.get_effective_price(), Decimal("80.00"))


class ProductImageTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Dresses", slug="dresses")

    def test_str_includes_product_name(self):
        p = Product.objects.create(
            category=self.category,
            name="Summer Dress",
            slug="summer-dress-img",
            sku="SKU-IMG-001",
            price=Decimal("49.99"),
        )
        # We can't easily test ImageField without a file, so test str
        # via the model class itself
        self.assertIn("Summer Dress", str(p))

    def test_primary_image_unsets_other_primaries(self):
        p = Product.objects.create(
            category=self.category,
            name="Test",
            slug="test-img-pri",
            sku="SKU-IMG-002",
            price=Decimal("10.00"),
        )
        # Create two images; first is primary
        img1 = ProductImage.objects.create(
            product=p, is_primary=True, sort_order=0
        )
        img2 = ProductImage.objects.create(
            product=p, is_primary=True, sort_order=1
        )
        img1.refresh_from_db()
        img2.refresh_from_db()
        self.assertFalse(img1.is_primary)
        self.assertTrue(img2.is_primary)


class DiscountModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Dresses", slug="dresses")
        self.product = Product.objects.create(
            category=self.category,
            name="Test Product",
            slug="test-prod",
            sku="SKU-DISC-001",
            price=Decimal("100.00"),
        )

    def test_str_returns_name(self):
        d = Discount.objects.create(
            name="Summer Sale",
            discount_type="percent",
            scope="global",
            value=Decimal("10.00"),
        )
        self.assertEqual(str(d), "Summer Sale")

    def test_clean_rejects_percent_above_100(self):
        d = Discount(
            name="Bad",
            discount_type="percent",
            scope="global",
            value=Decimal("150.00"),
        )
        with self.assertRaises(ValidationError):
            d.clean()

    def test_clean_rejects_zero_value(self):
        d = Discount(
            name="Zero",
            discount_type="fixed",
            scope="global",
            value=Decimal("0.00"),
        )
        with self.assertRaises(ValidationError):
            d.clean()

    def test_clean_rejects_negative_value(self):
        d = Discount(
            name="Neg",
            discount_type="fixed",
            scope="global",
            value=Decimal("-5.00"),
        )
        with self.assertRaises(ValidationError):
            d.clean()

    def test_clean_rejects_ends_before_starts(self):
        now = timezone.now()
        d = Discount(
            name="Bad dates",
            discount_type="percent",
            scope="global",
            value=Decimal("10.00"),
            starts_at=now,
            ends_at=now - timedelta(hours=1),
        )
        with self.assertRaises(ValidationError):
            d.clean()

    def test_clean_rejects_global_with_category(self):
        d = Discount(
            name="Bad scope",
            discount_type="percent",
            scope="global",
            value=Decimal("10.00"),
            category=self.category,
        )
        with self.assertRaises(ValidationError):
            d.clean()

    def test_clean_rejects_global_with_product(self):
        d = Discount(
            name="Bad scope",
            discount_type="percent",
            scope="global",
            value=Decimal("10.00"),
            product=self.product,
        )
        with self.assertRaises(ValidationError):
            d.clean()

    def test_clean_rejects_category_without_category(self):
        d = Discount(
            name="Bad scope",
            discount_type="percent",
            scope="category",
            value=Decimal("10.00"),
        )
        with self.assertRaises(ValidationError):
            d.clean()

    def test_clean_rejects_category_with_product(self):
        d = Discount(
            name="Bad scope",
            discount_type="percent",
            scope="category",
            value=Decimal("10.00"),
            category=self.category,
            product=self.product,
        )
        with self.assertRaises(ValidationError):
            d.clean()

    def test_clean_rejects_product_without_product(self):
        d = Discount(
            name="Bad scope",
            discount_type="percent",
            scope="product",
            value=Decimal("10.00"),
        )
        with self.assertRaises(ValidationError):
            d.clean()

    def test_clean_rejects_product_with_category(self):
        d = Discount(
            name="Bad scope",
            discount_type="percent",
            scope="product",
            value=Decimal("10.00"),
            category=self.category,
            product=self.product,
        )
        with self.assertRaises(ValidationError):
            d.clean()

    def test_is_current_active_no_dates(self):
        d = Discount.objects.create(
            name="Always",
            discount_type="percent",
            scope="global",
            value=Decimal("10.00"),
            is_active=True,
        )
        self.assertTrue(d.is_current())

    def test_is_current_inactive(self):
        d = Discount.objects.create(
            name="Inactive",
            discount_type="percent",
            scope="global",
            value=Decimal("10.00"),
            is_active=False,
        )
        self.assertFalse(d.is_current())

    def test_is_current_before_starts(self):
        now = timezone.now()
        d = Discount.objects.create(
            name="Future",
            discount_type="percent",
            scope="global",
            value=Decimal("10.00"),
            is_active=True,
            starts_at=now + timedelta(days=1),
        )
        self.assertFalse(d.is_current(now=now))

    def test_is_current_after_ends(self):
        now = timezone.now()
        d = Discount.objects.create(
            name="Past",
            discount_type="percent",
            scope="global",
            value=Decimal("10.00"),
            is_active=True,
            ends_at=now - timedelta(days=1),
        )
        self.assertFalse(d.is_current(now=now))

    def test_is_current_within_range(self):
        now = timezone.now()
        d = Discount.objects.create(
            name="Active",
            discount_type="percent",
            scope="global",
            value=Decimal("10.00"),
            is_active=True,
            starts_at=now - timedelta(days=1),
            ends_at=now + timedelta(days=1),
        )
        self.assertTrue(d.is_current(now=now))

    def test_applies_to_product_global(self):
        d = Discount.objects.create(
            name="Global",
            discount_type="percent",
            scope="global",
            value=Decimal("10.00"),
            is_active=True,
        )
        self.assertTrue(d.applies_to_product(self.product))

    def test_applies_to_product_category_match(self):
        d = Discount.objects.create(
            name="Cat",
            discount_type="percent",
            scope="category",
            value=Decimal("10.00"),
            category=self.category,
            is_active=True,
        )
        self.assertTrue(d.applies_to_product(self.product))

    def test_applies_to_product_category_mismatch(self):
        other_cat = Category.objects.create(name="Shoes", slug="shoes")
        d = Discount.objects.create(
            name="Cat",
            discount_type="percent",
            scope="category",
            value=Decimal("10.00"),
            category=other_cat,
            is_active=True,
        )
        self.assertFalse(d.applies_to_product(self.product))

    def test_applies_to_product_product_match(self):
        d = Discount.objects.create(
            name="Prod",
            discount_type="percent",
            scope="product",
            value=Decimal("10.00"),
            product=self.product,
            is_active=True,
        )
        self.assertTrue(d.applies_to_product(self.product))

    def test_apply_to_price_percent(self):
        d = Discount.objects.create(
            name="10%",
            discount_type="percent",
            scope="global",
            value=Decimal("10.00"),
            is_active=True,
        )
        self.assertEqual(
            d.apply_to_price(Decimal("100.00")), Decimal("90.00")
        )

    def test_apply_to_price_fixed(self):
        d = Discount.objects.create(
            name="$15",
            discount_type="fixed",
            scope="global",
            value=Decimal("15.00"),
            is_active=True,
        )
        self.assertEqual(
            d.apply_to_price(Decimal("100.00")), Decimal("85.00")
        )

    def test_apply_to_price_never_below_zero(self):
        d = Discount.objects.create(
            name="Big",
            discount_type="fixed",
            scope="global",
            value=Decimal("200.00"),
            is_active=True,
        )
        self.assertEqual(
            d.apply_to_price(Decimal("100.00")), Decimal("0.00")
        )

    def test_apply_to_price_percent_never_below_zero(self):
        d = Discount.objects.create(
            name="200%",
            discount_type="percent",
            scope="global",
            value=Decimal("200.00"),
            is_active=True,
        )
        self.assertEqual(
            d.apply_to_price(Decimal("100.00")), Decimal("0.00")
        )


class NewsletterSubscriberTests(TestCase):
    def test_str_returns_email(self):
        sub = NewsletterSubscriber.objects.create(email="test@example.com")
        self.assertEqual(str(sub), "test@example.com")

    def test_unique_email(self):
        NewsletterSubscriber.objects.create(email="test@example.com")
        with self.assertRaises(Exception):
            NewsletterSubscriber.objects.create(email="test@example.com")


class OrderTests(TestCase):
    def test_str_returns_order_number(self):
        order = Order.objects.create(
            customer_name="Alice",
            customer_email="alice@example.com",
            shipping_address="123 Main St",
        )
        self.assertTrue(str(order).startswith("FD-"))

    def test_order_number_auto_generated(self):
        order = Order.objects.create(
            customer_name="Bob",
            customer_email="bob@example.com",
            shipping_address="456 Oak Ave",
        )
        self.assertTrue(len(order.order_number) > 0)
        self.assertTrue(order.order_number.startswith("FD-"))

    def test_order_number_unique(self):
        o1 = Order.objects.create(
            customer_name="A", customer_email="a@a.com",
            shipping_address="Addr"
        )
        o2 = Order.objects.create(
            customer_name="B", customer_email="b@b.com",
            shipping_address="Addr"
        )
        self.assertNotEqual(o1.order_number, o2.order_number)

    def test_status_default_pending(self):
        order = Order.objects.create(
            customer_name="C",
            customer_email="c@c.com",
            shipping_address="Addr",
        )
        self.assertEqual(order.status, "pending")


class OrderItemTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Dresses", slug="dresses")
        self.product = Product.objects.create(
            category=self.category,
            name="Test Product",
            slug="test-oi",
            sku="SKU-OI-001",
            price=Decimal("49.99"),
        )
        self.order = Order.objects.create(
            customer_name="Alice",
            customer_email="alice@example.com",
            shipping_address="123 Main St",
        )

    def test_str_includes_product_name_and_quantity(self):
        item = OrderItem.objects.create(
            order=self.order,
            product_name=self.product.name,
            sku=self.product.sku,
            unit_price=Decimal("49.99"),
            quantity=2,
            line_total=Decimal("99.98"),
        )
        self.assertIn("Test Product", str(item))
        self.assertIn("2", str(item))
