"""Dedicated tests for discount calculation, stacking, and edge cases."""

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from store.models import Category, Discount, Product


class DiscountEdgeCaseTests(TestCase):
    """Edge-case coverage for discount rules from the implementation plan."""

    def setUp(self):
        self.category = Category.objects.create(name="Dresses", slug="dresses")
        self.product = Product.objects.create(
            category=self.category,
            name="Test Product",
            slug="test-edge",
            sku="SKU-EDGE-001",
            price=Decimal("100.00"),
        )

    def test_percent_discount_above_100_fails_validation(self):
        """Percent discounts above 100 must fail validation."""
        d = Discount(
            name="Too much",
            discount_type="percent",
            scope="global",
            value=Decimal("150.00"),
        )
        with self.assertRaises(ValidationError):
            d.clean()

    def test_fixed_discount_cannot_reduce_effective_price_below_zero(self):
        """Fixed discount cannot reduce effective price below zero."""
        d = Discount.objects.create(
            name="Big cut",
            discount_type="fixed",
            scope="global",
            value=Decimal("999.00"),
            is_active=True,
        )
        result = d.apply_to_price(Decimal("50.00"))
        self.assertEqual(result, Decimal("0.00"))

    def test_percent_discount_cannot_reduce_effective_price_below_zero(self):
        """Percent discount above 100 cannot reduce effective price below zero."""
        d = Discount.objects.create(
            name="Huge %",
            discount_type="percent",
            scope="global",
            value=Decimal("150.00"),
            is_active=True,
        )
        result = d.apply_to_price(Decimal("50.00"))
        self.assertEqual(result, Decimal("0.00"))

    def test_product_scoped_discount_requires_product_and_no_category(self):
        """Product-scoped discounts require a product and no category."""
        d = Discount(
            name="Bad product scope",
            discount_type="percent",
            scope="product",
            value=Decimal("10.00"),
        )
        with self.assertRaises(ValidationError):
            d.clean()

        d2 = Discount(
            name="Bad product scope 2",
            discount_type="percent",
            scope="product",
            value=Decimal("10.00"),
            product=self.product,
            category=self.category,
        )
        with self.assertRaises(ValidationError):
            d2.clean()

        # Valid product discount
        d3 = Discount(
            name="Good product scope",
            discount_type="percent",
            scope="product",
            value=Decimal("10.00"),
            product=self.product,
        )
        d3.clean()  # should not raise

    def test_category_scoped_discount_requires_category_and_no_product(self):
        """Category-scoped discounts require a category and no product."""
        d = Discount(
            name="Bad cat scope",
            discount_type="percent",
            scope="category",
            value=Decimal("10.00"),
        )
        with self.assertRaises(ValidationError):
            d.clean()

        d2 = Discount(
            name="Bad cat scope 2",
            discount_type="percent",
            scope="category",
            value=Decimal("10.00"),
            category=self.category,
            product=self.product,
        )
        with self.assertRaises(ValidationError):
            d2.clean()

        # Valid category discount
        d3 = Discount(
            name="Good cat scope",
            discount_type="percent",
            scope="category",
            value=Decimal("10.00"),
            category=self.category,
        )
        d3.clean()  # should not raise

    def test_global_discount_requires_no_product_or_category(self):
        """Global discounts require no product/category."""
        d = Discount(
            name="Bad global",
            discount_type="percent",
            scope="global",
            value=Decimal("10.00"),
            category=self.category,
        )
        with self.assertRaises(ValidationError):
            d.clean()

        d2 = Discount(
            name="Bad global 2",
            discount_type="percent",
            scope="global",
            value=Decimal("10.00"),
            product=self.product,
        )
        with self.assertRaises(ValidationError):
            d2.clean()

        # Valid global discount
        d3 = Discount(
            name="Good global",
            discount_type="percent",
            scope="global",
            value=Decimal("10.00"),
        )
        d3.clean()  # should not raise

    def test_compare_at_price_must_be_empty_or_gte_price(self):
        """compare_at_price must be empty or >= price."""
        p = Product(
            category=self.category,
            name="Bad compare",
            slug="bad-compare",
            sku="SKU-COMP-001",
            price=Decimal("50.00"),
            compare_at_price=Decimal("30.00"),
        )
        with self.assertRaises(ValidationError):
            p.clean()

        # Valid: equal
        p2 = Product(
            category=self.category,
            name="Good compare",
            slug="good-compare",
            sku="SKU-COMP-002",
            price=Decimal("50.00"),
            compare_at_price=Decimal("50.00"),
        )
        p2.clean()  # should not raise

        # Valid: null
        p3 = Product(
            category=self.category,
            name="Null compare",
            slug="null-compare",
            sku="SKU-COMP-003",
            price=Decimal("50.00"),
        )
        p3.clean()  # should not raise

    def test_only_one_primary_image_per_product(self):
        """Only one primary image should remain per product."""
        from store.models import ProductImage

        img1 = ProductImage.objects.create(
            product=self.product, is_primary=True
        )
        self.assertTrue(
            ProductImage.objects.filter(
                product=self.product, is_primary=True
            ).exists()
        )
        img2 = ProductImage.objects.create(
            product=self.product, is_primary=True
        )
        img1.refresh_from_db()
        self.assertFalse(img1.is_primary)
        self.assertTrue(img2.is_primary)

    def test_effective_price_deterministic_and_decimal_based(self):
        """Effective price calculation is deterministic and Decimal-based."""
        result = self.product.get_effective_price()
        self.assertIsInstance(result, Decimal)
        self.assertEqual(result, Decimal("100.00"))
        # Verify two decimal places
        self.assertEqual(str(result), "100.00")

    def test_effective_price_with_fractional_percent(self):
        """Effective price with fractional discount rounds correctly."""
        Discount.objects.create(
            name="33% off",
            discount_type="percent",
            scope="global",
            value=Decimal("33.33"),
            is_active=True,
        )
        # 100 * 33.33% = 33.33 discount, result = 66.67
        self.assertEqual(
            self.product.get_effective_price(), Decimal("66.67")
        )

    def test_discounts_do_not_stack_highest_priority_wins(self):
        """Discounts do not stack. Pick first by highest priority, then lowest id."""
        d1 = Discount.objects.create(
            name="Low priority 10%",
            discount_type="percent",
            scope="global",
            value=Decimal("10.00"),
            priority=0,
            is_active=True,
        )
        d2 = Discount.objects.create(
            name="High priority 50%",
            discount_type="percent",
            scope="global",
            value=Decimal("50.00"),
            priority=10,
            is_active=True,
        )
        self.assertEqual(
            self.product.get_effective_price(), Decimal("50.00")
        )

    def test_inactive_discount_not_applied(self):
        """Inactive discounts should not be applied."""
        Discount.objects.create(
            name="Inactive 50%",
            discount_type="percent",
            scope="global",
            value=Decimal("50.00"),
            is_active=False,
        )
        self.assertEqual(
            self.product.get_effective_price(), Decimal("100.00")
        )

    def test_expired_discount_not_applied(self):
        """Expired discount should not be applied."""
        now = timezone.now()
        Discount.objects.create(
            name="Expired",
            discount_type="percent",
            scope="global",
            value=Decimal("50.00"),
            is_active=True,
            starts_at=now - timedelta(days=10),
            ends_at=now - timedelta(days=1),
        )
        self.assertEqual(
            self.product.get_effective_price(now=now), Decimal("100.00")
        )

    def test_future_discount_not_applied(self):
        """Future discount should not be applied yet."""
        now = timezone.now()
        Discount.objects.create(
            name="Future",
            discount_type="percent",
            scope="global",
            value=Decimal("50.00"),
            is_active=True,
            starts_at=now + timedelta(days=1),
        )
        self.assertEqual(
            self.product.get_effective_price(now=now), Decimal("100.00")
        )

    def test_apply_to_price_returns_two_decimal_places(self):
        """apply_to_price always returns a 2-decimal Decimal."""
        d = Discount.objects.create(
            name="Exact",
            discount_type="percent",
            scope="global",
            value=Decimal("10.00"),
            is_active=True,
        )
        result = d.apply_to_price(Decimal("29.99"))
        self.assertIsInstance(result, Decimal)
        self.assertEqual(str(result), "26.99")
