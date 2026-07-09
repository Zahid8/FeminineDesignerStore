"""Tests for blouse customization model, admin, views, and forms."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from store.models import (
    Category,
    CustomizationRequest,
    Product,
    SiteSettings,
)


class ProductMeasurementTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Blouses", slug="blouses")

    def test_measurement_defaults_are_10(self):
        p = Product.objects.create(
            category=self.category, name="Test", slug="test-m",
            sku="SKU-M-001", price=Decimal("50"),
        )
        self.assertEqual(p.default_length, Decimal("10.00"))
        self.assertEqual(p.default_chest, Decimal("10.00"))
        self.assertEqual(p.default_waist, Decimal("10.00"))

    def test_negative_measurement_fails_validation(self):
        p = Product(
            category=self.category, name="Test", slug="test-neg",
            sku="SKU-M-002", price=Decimal("50"), default_length=Decimal("-1"),
        )
        with self.assertRaises(ValidationError):
            p.full_clean()

    def test_zero_measurement_fails_validation(self):
        p = Product(
            category=self.category, name="Test", slug="test-zero",
            sku="SKU-M-003", price=Decimal("50"), default_chest=Decimal("0"),
        )
        with self.assertRaises(ValidationError):
            p.full_clean()


class CustomizationRequestTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Blouses", slug="blouses")
        self.product = Product.objects.create(
            category=self.category, name="Test Blouse", slug="test-blouse",
            sku="SKU-CR-001", price=Decimal("70"), stock_quantity=5,
        )

    def test_create_customization_request(self):
        cr = CustomizationRequest.objects.create(
            product=self.product,
            customer_name="Alice",
            customer_phone="+1234567890",
            length=Decimal("24"),
            chest=Decimal("36"),
            waist=Decimal("30"),
            armhole=Decimal("12"),
            opening=Decimal("10"),
            bicep=Decimal("14"),
        )
        self.assertIsNotNone(cr.token)
        self.assertIn("Alice", str(cr))

    def test_token_is_unique(self):
        cr1 = CustomizationRequest.objects.create(
            product=self.product, customer_name="A", customer_phone="1",
            length=1, chest=1, waist=1, armhole=1, opening=1, bicep=1,
        )
        cr2 = CustomizationRequest.objects.create(
            product=self.product, customer_name="B", customer_phone="2",
            length=2, chest=2, waist=2, armhole=2, opening=2, bicep=2,
        )
        self.assertNotEqual(cr1.token, cr2.token)


class CustomizationViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="Blouses", slug="blouses")
        self.product = Product.objects.create(
            category=self.category, name="Silk Blouse", slug="silk-blouse",
            sku="SKU-CV-001", price=Decimal("70"), stock_quantity=5,
        )

    def test_product_detail_has_measurement_fields(self):
        response = self.client.get(
            reverse("product_detail", kwargs={"slug": self.product.slug})
        )
        content = response.content.decode()
        self.assertIn("Length (in)", content)
        self.assertIn("Chest (in)", content)
        self.assertIn("Waist (in)", content)
        self.assertIn("Buy Now", content)
        self.assertIn("Customize", content)
        self.assertIn("Disclaimer", content)

    def test_product_detail_has_measurement_guide(self):
        response = self.client.get(
            reverse("product_detail", kwargs={"slug": self.product.slug})
        )
        self.assertContains(response, "Measurement Guide")

    def test_buy_now_post_adds_to_cart_and_redirects(self):
        response = self.client.post(
            reverse("buy_now", kwargs={"product_id": self.product.pk})
        )
        self.assertRedirects(response, reverse("checkout"))
        cart = self.client.session.get("femdes_cart", {})
        self.assertEqual(len(cart), 1)

    def test_customization_create(self):
        response = self.client.post(
            reverse("customization_create", kwargs={"slug": self.product.slug}),
            {
                "customer_name": "Alice",
                "customer_phone": "1234567890",
                "length": "24", "chest": "36", "waist": "30",
                "armhole": "12", "opening": "10", "bicep": "14",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CustomizationRequest.objects.count(), 1)
        cr = CustomizationRequest.objects.first()
        self.assertContains(response, str(cr.token))

    def test_customization_detail_renders(self):
        cr = CustomizationRequest.objects.create(
            product=self.product, customer_name="Bob", customer_phone="111",
            length=25, chest=37, waist=31, armhole=13, opening=11, bicep=15,
        )
        response = self.client.get(
            reverse("customization_detail", kwargs={"token": cr.token})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bob")
        self.assertContains(response, "Disclaimer")

    def test_customization_detail_invalid_token_404(self):
        response = self.client.get(
            reverse("customization_detail", kwargs={
                "token": "00000000-0000-0000-0000-000000000000",
            })
        )
        self.assertEqual(response.status_code, 404)
