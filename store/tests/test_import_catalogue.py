import io
import json
import shutil
import tempfile
from decimal import Decimal
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from PIL import Image

from store.models import Category, Occasion, Product

MEDIA = tempfile.mkdtemp()


def _write_catalogue(root, products, **shared):
    spec = {"category": "Blouses", "price": "2200.00", "stock": 10, "sku_prefix": "FD-BL-", "sku_start": 101,
            "new_arrival": True, "care": {"sequin": "Dry clean only."}, "products": products, **shared}
    (root / "catalogue.json").write_text(json.dumps(spec))
    for p in products:
        folder = root / p["folder"]
        folder.mkdir(exist_ok=True)
        for i in range(1, 5):
            Image.new("RGB", (20, 20), (i * 40, 0, 0)).save(folder / f"{i}.jpg")


def _item(name, folder, **extra):
    return {"folder": folder, "name": name, "colour": "Black", "fabric": "Sequin", "care": "sequin",
            "occasions": ["Party"], "short": f"{name} short.", "description": f"{name} long.", **extra}


@override_settings(MEDIA_ROOT=MEDIA)
class ImportCatalogueTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)

    def run_cmd(self, *args):
        out = io.StringIO()
        call_command("import_catalogue", str(self.root), *args, stdout=out)
        return out.getvalue()

    def test_creates_products_with_photos_price_stock_and_text(self):
        _write_catalogue(self.root, [_item("Black Sequin Blouse", "a"), _item("Gold Sequin Blouse", "b")])
        self.run_cmd()
        p = Product.objects.get(slug="black-sequin-blouse")
        self.assertEqual(p.price, Decimal("2200.00"))
        self.assertEqual(p.stock_quantity, 10)
        self.assertEqual(p.category.name, "Blouses")
        self.assertEqual(p.sku, "FD-BL-101")
        self.assertEqual(Product.objects.get(slug="gold-sequin-blouse").sku, "FD-BL-102")
        self.assertTrue(p.is_new_arrival and p.is_active and p.allow_customization)
        self.assertEqual((p.short_description, p.description, p.color_options, p.fabric, p.care_instructions),
                         ("Black Sequin Blouse short.", "Black Sequin Blouse long.", "Black", "Sequin", "Dry clean only."))
        imgs = list(p.images.all())
        self.assertEqual(len(imgs), 4)
        self.assertEqual([i.is_primary for i in imgs], [True, False, False, False])
        self.assertEqual(imgs[1].alt_text, "Black Sequin Blouse (back)")
        self.assertEqual(p.primary_image, imgs[0])
        self.assertEqual(list(p.occasions.values_list("name", flat=True)), ["Party"])

    def test_reuses_existing_category_and_occasion(self):
        Category.objects.create(name="Blouses", slug="blouses")
        Occasion.objects.create(name="Party", slug="party")
        _write_catalogue(self.root, [_item("One", "a")])
        self.run_cmd()
        self.assertEqual(Category.objects.count(), 1)
        self.assertEqual(Occasion.objects.count(), 1)

    def test_running_twice_skips_existing_products(self):
        _write_catalogue(self.root, [_item("One", "a")])
        self.run_cmd()
        out = self.run_cmd()
        self.assertIn("skipped 1", out)
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(Product.objects.get().images.count(), 4)

    def test_skips_taken_skus(self):
        Product.objects.create(name="Old", slug="old", sku="FD-BL-101", price=Decimal("1"))
        _write_catalogue(self.root, [_item("One", "a")])
        self.run_cmd()
        self.assertEqual(Product.objects.get(slug="one").sku, "FD-BL-102")

    def test_dry_run_changes_nothing(self):
        _write_catalogue(self.root, [_item("One", "a")])
        out = self.run_cmd("--dry-run")
        self.assertIn("Would add 1", out)
        self.assertFalse(Product.objects.exists())

    def test_rejects_missing_photos_or_fields_before_creating_anything(self):
        _write_catalogue(self.root, [_item("One", "a"), _item("Two", "b")])
        shutil.rmtree(self.root / "b")
        with self.assertRaises(CommandError):
            self.run_cmd()
        self.assertFalse(Product.objects.exists())

    def test_shipped_catalogue_is_valid(self):
        repo = Path(__file__).resolve().parents[2] / "catalogue" / "2026-10-blouses"
        if not repo.is_dir():
            self.skipTest("catalogue folder not present")
        out = io.StringIO()
        call_command("import_catalogue", str(repo), "--dry-run", stdout=out)
        self.assertIn("Would add 22", out.getvalue())
