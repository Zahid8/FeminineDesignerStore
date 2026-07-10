"""Tests for blouse customization model, admin, views, and forms."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from store.models import (
    Category,
    CustomizationRequest,
    Product,
)


class ProductMeasurementTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Blouses", slug="blouses")

    def test_measurement_defaults_are_none(self):
        p = Product.objects.create(
            category=self.category, name="Test", slug="test-m",
            sku="SKU-M-001", price=Decimal("50"),
        )
        self.assertIsNone(p.default_length)
        self.assertIsNone(p.default_chest)
        self.assertIsNone(p.default_waist)

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


class CustomizationRequestModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Blouses", slug="blouses")
        self.product = Product.objects.create(
            category=self.category, name="Test", slug="test-cr",
            sku="SKU-CR-M", price=Decimal("70"), stock_quantity=5,
        )

    def test_create_customization_request(self):
        cr = CustomizationRequest.objects.create(
            product=self.product,
            customer_name="Alice", customer_phone="+1234567890",
            length=Decimal("24"), chest=Decimal("36"), waist=Decimal("30"),
            armhole=Decimal("12"), opening=Decimal("10"), bicep=Decimal("14"),
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

    def test_negative_measurement_fails_full_clean(self):
        cr = CustomizationRequest(
            product=self.product, customer_name="A", customer_phone="1",
            length=Decimal("-1"), chest=1, waist=1, armhole=1, opening=1, bicep=1,
        )
        with self.assertRaises(ValidationError):
            cr.full_clean()

    def test_zero_measurement_fails_full_clean(self):
        cr = CustomizationRequest(
            product=self.product, customer_name="A", customer_phone="1",
            length=Decimal("0"), chest=1, waist=1, armhole=1, opening=1, bicep=1,
        )
        with self.assertRaises(ValidationError):
            cr.full_clean()


class CustomizationViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="Blouses", slug="blouses")
        self.product = Product.objects.create(
            category=self.category, name="Silk Blouse", slug="silk-blouse",
            sku="SKU-CV-001", price=Decimal("70"), stock_quantity=5,
        )
        self.valid_data = {
            "customer_name": "Alice", "customer_phone": "1234567890",
            "length": "24", "chest": "36", "waist": "30",
            "armhole": "12", "opening": "10", "bicep": "14",
        }

    def test_product_detail_has_all_six_measurement_labels(self):
        response = self.client.get(
            reverse("product_detail", kwargs={"slug": self.product.slug})
        )
        content = response.content.decode()
        for label in ("Length (in)", "Chest (in)", "Waist (in)",
                       "Armhole (in)", "Opening (in)", "Bicep (in)"):
            self.assertIn(label, content, f"Missing measurement label: {label}")

    def test_product_detail_has_gallery_container(self):
        """Gallery uses Bootstrap carousel with prev/next controls."""
        from django.core.management import call_command
        with self.settings(MEDIA_ROOT="/tmp/test-media-gallery"):
            call_command("seed_demo_store")
        p = Product.objects.filter(sku__startswith="FD-BLOUSE-").first()
        response = self.client.get(
            reverse("product_detail", kwargs={"slug": p.slug})
        )
        self.assertContains(response, "product-gallery")
        self.assertContains(response, 'aria-label="Previous image"')
        self.assertContains(response, 'aria-label="Next image"')

    def test_product_detail_ready_made_specs(self):
        """Product detail shows only non-blank measurement labels and values."""
        # Set some measurements to prove they render, leave others blank.
        self.product.default_length = Decimal("12.50")
        self.product.default_chest = Decimal("14.00")
        self.product.save()
        response = self.client.get(
            reverse("product_detail", kwargs={"slug": self.product.slug})
        )
        content = response.content.decode()
        self.assertIn("Ready-Made Specifications", content)
        self.assertIn("Length", content)
        self.assertIn("12.50 in", content)
        # Chest is set, should appear
        self.assertIn("Chest", content)
        # Waist is blank (None), should not appear
        self.assertNotIn("Waist</strong>", content)

    def test_multi_image_carousel_has_one_active_item(self):
        """Carousel with 4 images has exactly one .carousel-item.active."""
        from django.core.management import call_command
        with self.settings(MEDIA_ROOT="/tmp/test-media-carousel"):
            call_command("seed_demo_store")
        p = Product.objects.filter(sku__startswith="FD-BLOUSE-").first()
        response = self.client.get(
            reverse("product_detail", kwargs={"slug": p.slug})
        )
        content = response.content.decode()
        # Exactly one active carousel item
        self.assertEqual(content.count("carousel-item active"), 1)

    def test_multi_image_carousel_has_prev_next_controls(self):
        """Multi-image product renders prev/next controls."""
        from django.core.management import call_command
        with self.settings(MEDIA_ROOT="/tmp/test-media-carousel-2"):
            call_command("seed_demo_store")
        p = Product.objects.filter(sku__startswith="FD-BLOUSE-").first()
        response = self.client.get(
            reverse("product_detail", kwargs={"slug": p.slug})
        )
        content = response.content.decode()
        self.assertIn('aria-label="Previous image"', content)
        self.assertIn('aria-label="Next image"', content)
        # Old thumbnail grid must be gone.
        self.assertNotIn("product-gallery-scroll", content)

    def test_single_image_no_broken_controls(self):
        """Product with 1 image has no prev/next controls."""
        from store.models import ProductImage
        ProductImage.objects.create(
            product=self.product, is_primary=True, sort_order=0,
        )
        # Set image path directly
        from pathlib import Path
        import shutil
        dest = Path("/tmp/test-media-single/products/demo")
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(
            Path(__file__).resolve().parent.parent.parent
            / "static/store/images/product-item-1.jpg",
            dest / "single.jpg",
        )
        img = ProductImage.objects.filter(product=self.product).first()
        img.image.name = "products/demo/single.jpg"
        img.save()

        self.product.refresh_from_db()
        self.assertEqual(self.product.images.count(), 1)
        response = self.client.get(
            reverse("product_detail", kwargs={"slug": self.product.slug})
        )
        content = response.content.decode()
        self.assertIn("product-gallery", content)
        self.assertIn("carousel-item active", content)
        # No prev/next controls for single image
        self.assertNotIn('aria-label="Previous image"', content)
        self.assertNotIn('aria-label="Next image"', content)

class OptionalSkuTests(TestCase):
    """Multiple products can have blank SKU; non-blank SKUs remain unique."""

    def setUp(self):
        self.category = Category.objects.create(name="Blouses", slug="blouses")

    def test_two_blank_sku_products_allowed(self):
        p1 = Product.objects.create(
            category=self.category, name="A", slug="sku-a",
            sku="", price=Decimal("50"),
        )
        p2 = Product.objects.create(
            category=self.category, name="B", slug="sku-b",
            sku="", price=Decimal("50"),
        )
        self.assertIsNone(p1.sku)
        self.assertIsNone(p2.sku)

    def test_duplicate_non_blank_sku_rejected(self):
        Product.objects.create(
            category=self.category, name="A", slug="sku-c",
            sku="DUP-001", price=Decimal("50"),
        )
        with self.assertRaises(Exception):
            Product.objects.create(
                category=self.category, name="B", slug="sku-d",
                sku="DUP-001", price=Decimal("50"),
            )

    def test_blank_sku_label_hidden(self):
        p = Product.objects.create(
            category=self.category, name="NoSKU", slug="nosku",
            sku="", price=Decimal("50"),
        )
        response = self.client.get(
            reverse("product_detail", kwargs={"slug": "nosku"})
        )
        self.assertNotContains(response, "SKU:")

    def test_non_blank_sku_label_shown(self):
        p = Product.objects.create(
            category=self.category, name="WithSKU", slug="withsku",
            sku="SHOW-001", price=Decimal("50"),
        )
        response = self.client.get(
            reverse("product_detail", kwargs={"slug": "withsku"})
        )
        self.assertContains(response, "SKU: SHOW-001")


class OptionalMeasurementDisplayTests(TestCase):
    """Blank measurements hidden; non-blank measurements shown."""

    def setUp(self):
        self.category = Category.objects.create(name="Blouses", slug="blouses")

    def test_blank_measurement_absent_and_present_measurement_shown(self):
        p = Product.objects.create(
            category=self.category, name="M", slug="mtest",
            sku="SKU-MTEST", price=Decimal("50"),
            default_length=Decimal("20"),  # set
            default_chest=None,            # blank
        )
        response = self.client.get(
            reverse("product_detail", kwargs={"slug": "mtest"})
        )
        content = response.content.decode()
        self.assertIn("Length", content)
        self.assertNotIn("Chest</strong>", content)


# Continue CustomizationViewTests below — methods that were in this class originally.

class CustomizationViewMoreTests(TestCase):
    """Additional customization view tests (continuation of CustomizationViewTests)."""
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="Blouses", slug="blouses")
        self.product = Product.objects.create(
            category=self.category, name="Silk Blouse 2", slug="silk-blouse2",
            sku="SKU-CV-002", price=Decimal("70"), stock_quantity=5,
        )
        self.valid_data = {
            "customer_name": "Alice", "customer_phone": "1234567890",
            "length": "24", "chest": "36", "waist": "30",
            "armhole": "12", "opening": "10", "bicep": "14",
        }

    def test_no_images_renders_placeholder(self):
        """Product with 0 images renders static fallback without error or controls."""
        response = self.client.get(
            reverse("product_detail", kwargs={"slug": self.product.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "product-item-1.jpg")
        self.assertNotIn('aria-label="Previous image"', response.content.decode())
        self.assertNotIn('aria-label="Next image"', response.content.decode())

    def test_admin_edited_measurement_in_customization_defaults(self):
        """Admin-edited measurement value appears in both ready-made specs and customization form."""
        self.product.default_chest = Decimal("14.50")
        self.product.save()
        response = self.client.get(
            reverse("product_detail", kwargs={"slug": self.product.slug})
        )
        content = response.content.decode()
        # Ready-made specs section
        self.assertIn("14.50 in", content)
        # Customization form input default
        self.assertIn('name="chest"', content)
        self.assertIn('value="14.50"', content)

    def test_ready_made_specs_before_buy_now(self):
        """Ready-Made Specifications appear before Buy Now / Qty / Add to Cart."""
        response = self.client.get(
            reverse("product_detail", kwargs={"slug": self.product.slug})
        )
        content = response.content.decode()
        specs_pos = content.find("Ready-Made Specifications")
        buy_now_pos = content.find("Buy Now")
        self.assertGreater(buy_now_pos, specs_pos,
                           "Ready-Made Specifications must appear before Buy Now")

    def test_product_detail_has_buy_now_and_customize(self):
        response = self.client.get(
            reverse("product_detail", kwargs={"slug": self.product.slug})
        )
        self.assertContains(response, "Buy Now")
        self.assertContains(response, "Customize")

    def test_product_detail_has_disclaimer(self):
        response = self.client.get(
            reverse("product_detail", kwargs={"slug": self.product.slug})
        )
        self.assertContains(response, "Disclaimer")

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

    def test_customization_create_redirects(self):
        response = self.client.post(
            reverse("customization_create", kwargs={"slug": self.product.slug}),
            self.valid_data,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CustomizationRequest.objects.count(), 1)

    def test_customization_success_page_shows_details(self):
        response = self.client.post(
            reverse("customization_create", kwargs={"slug": self.product.slug}),
            self.valid_data,
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        cr = CustomizationRequest.objects.first()
        self.assertContains(response, str(cr.token))
        self.assertContains(response, "Alice")
        self.assertContains(response, "1234567890")
        self.assertContains(response, "24")
        self.assertContains(response, "/customizations/")
        self.assertContains(response, "Share Your Customization")

    def test_customization_created_unknown_token_404(self):
        response = self.client.get(
            reverse("customization_created", kwargs={
                "token": "00000000-0000-0000-0000-000000000000",
            })
        )
        self.assertEqual(response.status_code, 404)

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
