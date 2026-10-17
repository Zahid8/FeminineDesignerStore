"""Import a folder of products (photos + catalogue.json) into the storefront.

    python manage.py import_catalogue catalogue/2026-10-blouses [--dry-run]

catalogue.json holds shared defaults (category, price, stock, SKU prefix, care
texts) and one entry per product: folder (photos 1.jpg, 2.jpg, ... in order:
front, back, worn front, worn back), name, colour, fabric, care key, occasions,
short and long description. Products whose slug already exists are skipped, so
running it twice never duplicates anything.
"""
import json
from decimal import Decimal
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from store.models import Category, Occasion, Product, ProductImage

VIEW_NAMES = ["front", "back", "worn, front", "worn, back"]
PHOTO_TYPES = (".jpg", ".jpeg", ".png", ".webp")


class Command(BaseCommand):
    help = "Create products with photos and descriptions from a catalogue folder."

    def add_arguments(self, parser):
        parser.add_argument("folder")
        parser.add_argument("--dry-run", action="store_true", help="Check everything, change nothing.")

    def handle(self, folder, dry_run=False, **options):
        root = Path(folder)
        spec_path = root / "catalogue.json"
        if not spec_path.is_file():
            raise CommandError(f"{spec_path} not found")
        spec = json.loads(spec_path.read_text())
        items = spec.get("products") or []
        self._check(root, items)

        created = skipped = 0
        sku_no = int(spec.get("sku_start", 1))
        for item in items:
            slug = slugify(item["name"])
            if Product.objects.filter(slug=slug).exists():
                skipped += 1
                self.stdout.write(f"skip   {slug} (already in the store)")
                continue
            sku = None
            if spec.get("sku_prefix"):
                while Product.objects.filter(sku=f"{spec['sku_prefix']}{sku_no}").exists():
                    sku_no += 1
                sku = f"{spec['sku_prefix']}{sku_no}"
                sku_no += 1
            photos = self._photos(root / item["folder"])
            if dry_run:
                created += 1
                self.stdout.write(f"would  {slug} {sku or ''} ({len(photos)} photos)")
                continue
            with transaction.atomic():
                self._create(spec, item, slug, sku, photos)
            created += 1
            self.stdout.write(self.style.SUCCESS(f"added  {slug} {sku or ''} ({len(photos)} photos)"))
        verb = "Would add" if dry_run else "Added"
        self.stdout.write(self.style.SUCCESS(f"{verb} {created} products, skipped {skipped}."))

    def _check(self, root, items):
        problems, names = [], set()
        for n, item in enumerate(items, 1):
            for key in ("folder", "name", "short", "description"):
                if not item.get(key):
                    problems.append(f"product {n}: missing {key}")
            if item.get("name"):
                if slugify(item["name"]) in names:
                    problems.append(f"product {n}: duplicate name {item['name']}")
                names.add(slugify(item["name"]))
            if item.get("folder") and not self._photos(root / item["folder"]):
                problems.append(f"product {n}: no photos in {item['folder']}/")
        if problems:
            raise CommandError("catalogue.json problems:\n  " + "\n  ".join(problems))

    @staticmethod
    def _photos(folder):
        if not folder.is_dir():
            return []
        return sorted(p for p in folder.iterdir() if p.suffix.lower() in PHOTO_TYPES)

    def _create(self, spec, item, slug, sku, photos):
        category_name = item.get("category") or spec.get("category")
        category = None
        if category_name:
            category = Category.objects.filter(name__iexact=category_name).first() or Category.objects.create(
                name=category_name, slug=slugify(category_name))
        care = spec.get("care", {})
        product = Product.objects.create(
            category=category,
            name=item["name"],
            slug=slug,
            sku=sku,
            short_description=item["short"][:255],
            description=item["description"],
            price=Decimal(str(item.get("price", spec.get("price")))),
            stock_quantity=int(item.get("stock", spec.get("stock", 0))),
            is_new_arrival=bool(item.get("new_arrival", spec.get("new_arrival", False))),
            color_options=item.get("colour", ""),
            fabric=item.get("fabric", "")[:80],
            care_instructions=care.get(item.get("care"), item.get("care", "")) if item.get("care") else "",
        )
        for name in item.get("occasions", []):
            occasion = Occasion.objects.filter(name__iexact=name).first() or Occasion.objects.create(
                name=name, slug=slugify(name))
            product.occasions.add(occasion)
        for i, path in enumerate(photos):
            view = VIEW_NAMES[i] if i < len(VIEW_NAMES) else f"photo {i + 1}"
            img = ProductImage(product=product, alt_text=f"{item['name']} ({view})"[:160], is_primary=(i == 0), sort_order=i)
            with path.open("rb") as fh:
                img.image.save(f"{slug}-{i + 1}{path.suffix.lower()}", File(fh), save=False)
            img.save()
        return product
