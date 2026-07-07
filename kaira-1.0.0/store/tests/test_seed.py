"""Tests for the seed_demo_store management command."""

import tempfile
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
        self.assertEqual(Category.objects.filter(is_active=True).count(), 5)
        self.assertGreaterEqual(Product.objects.filter(is_active=True).count(), 7)
        self.assertGreaterEqual(Discount.objects.filter(is_active=True).count(), 1)

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
