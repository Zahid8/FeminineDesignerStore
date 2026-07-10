"""Tests for the seed_demo_store management command."""

import tempfile
from decimal import Decimal
from pathlib import Path

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from store.models import (
    Category,
    Discount,
    Product,
    ProductImage,
    SiteSettings,
)


class SeedCommandTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._temp_media = tempfile.TemporaryDirectory()
        cls.media_root = cls._temp_media.name

    @classmethod
    def tearDownClass(cls):
        cls._temp_media.cleanup()
        super().tearDownClass()

    def _call_seed(self):
        with override_settings(MEDIA_ROOT=self.media_root):
            call_command("seed_demo_store")

    def _list_media_files(self):
        """Return sorted relative paths of all files under the temp media root."""
        root = Path(self.media_root)
        if not root.exists():
            return []
        return sorted(
            str(p.relative_to(root))
            for p in root.rglob("*")
            if p.is_file()
        )

    def test_seed_command_creates_core_records(self):
        self._call_seed()
        self.assertEqual(SiteSettings.objects.count(), 1)
        self.assertEqual(Category.objects.filter(is_active=True).count(), 1)
        self.assertEqual(Category.objects.filter(slug="blouses", is_active=True).count(), 1)
        self.assertGreaterEqual(Product.objects.filter(is_active=True).count(), 15)
        self.assertGreaterEqual(Discount.objects.filter(is_active=True).count(), 1)

    def test_each_seeded_blouse_has_four_images(self):
        self._call_seed()
        for product in Product.objects.filter(sku__startswith="FD-BLOUSE-"):
            self.assertEqual(
                ProductImage.objects.filter(product=product).count(), 4,
                f"{product.name} should have exactly 4 images",
            )

    def test_seeded_measurement_defaults_are_ten(self):
        self._call_seed()
        for product in Product.objects.filter(sku__startswith="FD-BLOUSE-"):
            self.assertEqual(product.default_length, Decimal("10.00"))
            self.assertEqual(product.default_chest, Decimal("10.00"))

    def test_exactly_15_active_blouses_and_60_images(self):
        self._call_seed()
        self.assertEqual(
            Product.objects.filter(sku__startswith="FD-BLOUSE-", is_active=True).count(),
            15,
        )
        self.assertEqual(
            ProductImage.objects.filter(product__sku__startswith="FD-BLOUSE-").count(),
            60,
        )

    def test_all_seeded_images_share_same_placeholder_content(self):
        """All 60 seeded images originate from the same placeholder source."""
        self._call_seed()
        imgs = list(
            ProductImage.objects.filter(
                product__sku__startswith="FD-BLOUSE-"
            ).order_by("id")
        )
        self.assertEqual(len(imgs), 60)
        # Collect unique media file hashes to prove same visual content.
        import hashlib
        hashes = set()
        for img in imgs:
            path = Path(self.media_root) / img.image.name
            if path.exists():
                hashes.add(hashlib.md5(path.read_bytes()).hexdigest())
        # All images share the same placeholder source → exactly one unique hash.
        self.assertEqual(
            len(hashes), 1,
            f"Expected 1 unique image hash (shared placeholder), got {len(hashes)}",
        )

    def test_seed_command_is_idempotent(self):
        self._call_seed()
        cats1 = Category.objects.count()
        prods1 = Product.objects.count()
        imgs1 = ProductImage.objects.count()
        discs1 = Discount.objects.count()
        ss1 = SiteSettings.objects.count()

        self._call_seed()
        self.assertEqual(Category.objects.count(), cats1)
        self.assertEqual(Product.objects.count(), prods1)
        self.assertEqual(ProductImage.objects.count(), imgs1)
        self.assertEqual(Discount.objects.count(), discs1)
        self.assertEqual(SiteSettings.objects.count(), ss1)

    def test_product_images_under_demo_path(self):
        """Every seeded product image.name starts with products/demo/."""
        self._call_seed()
        for img in ProductImage.objects.all():
            self.assertTrue(
                img.image.name.startswith("products/demo/"),
                f"Expected image under products/demo/, got: {img.image.name}",
            )

    def test_no_duplicate_image_files_after_repeat(self):
        """Repeated seed runs do not create duplicate or suffixed image files."""
        self._call_seed()
        files1 = self._list_media_files()
        self._call_seed()
        files2 = self._list_media_files()
        self.assertEqual(
            files1, files2,
            "Media files changed after second seed run",
        )
        # No file should have generated suffixes
        for path in files2:
            self.assertNotIn("_", Path(path).stem[-6:],
                             f"Suspicious suffix in: {path}")

    def test_seed_command_attaches_primary_images(self):
        self._call_seed()
        for product in Product.objects.all():
            imgs = ProductImage.objects.filter(product=product, is_primary=True)
            self.assertEqual(
                imgs.count(), 1,
                f"Product {product.name} should have exactly 1 primary image",
            )

    def test_seed_command_populates_homepage_sections(self):
        self._call_seed()
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('id="new-arrival"', content)
        self.assertIn('id="best-sellers"', content)
        self.assertIn('id="related-products"', content)

    def test_seed_deactivates_old_skus(self):
        """Old seed prefixes become inactive; exactly 15 FD-BLOUSE- remain."""
        cat = Category.objects.create(name="Old", slug="old", is_active=True)
        Product.objects.create(
            category=cat, name="Old Dress", slug="old-dress",
            sku="FD-DRESS-01", price=Decimal("50"), is_active=True, stock_quantity=1,
        )
        Product.objects.create(
            category=cat, name="Old Shirt", slug="old-shirt",
            sku="FD-SHIRT-01", price=Decimal("50"), is_active=True, stock_quantity=1,
        )
        self._call_seed()
        self.assertFalse(
            Product.objects.filter(sku="FD-DRESS-01").first().is_active
        )
        self.assertFalse(
            Product.objects.filter(sku="FD-SHIRT-01").first().is_active
        )
        self.assertEqual(
            Product.objects.filter(sku__startswith="FD-BLOUSE-", is_active=True).count(),
            15,
        )

    def test_seed_preserves_admin_created_products(self):
        """Products outside old seed prefixes stay active."""
        cat = Category.objects.create(name="Custom", slug="custom", is_active=True)
        Product.objects.create(
            category=cat, name="Admin Product", slug="admin-prod",
            sku="ADMIN-001", price=Decimal("99"), is_active=True, stock_quantity=1,
        )
        self._call_seed()
        self.assertTrue(
            Product.objects.filter(sku="ADMIN-001").first().is_active
        )

    def test_seed_command_errors_when_required_image_missing(self):
        static_images = (
            Path(__file__).resolve().parent.parent.parent
            / "static" / "store" / "images"
        )
        target = static_images / "product-item-1.jpg"
        renamed = static_images / "product-item-1.jpg.tmp"
        try:
            if target.exists():
                target.rename(renamed)
            with override_settings(MEDIA_ROOT=self.media_root):
                with self.assertRaises(CommandError) as ctx:
                    call_command("seed_demo_store")
                self.assertIn("product-item-1.jpg", str(ctx.exception))
        finally:
            if renamed.exists():
                renamed.rename(target)
