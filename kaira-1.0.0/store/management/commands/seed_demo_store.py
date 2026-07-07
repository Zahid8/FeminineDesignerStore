"""Idempotent demo store seed command."""

import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from store.models import (
    Category,
    Discount,
    Product,
    ProductImage,
    SiteSettings,
)

CATEGORIES = [
    ("Dresses", "dresses", 1),
    ("Shirts", "shirts", 2),
    ("Jackets", "jackets", 3),
    ("Sweaters", "sweaters", 4),
    ("Accessories", "accessories", 5),
]

PRODUCTS = [
    {
        "name": "Dark Florish Onepiece",
        "slug": "dark-florish-onepiece",
        "sku": "FD-DRESS-01",
        "category_slug": "dresses",
        "price": "95.00",
        "image": "product-item-1.jpg",
        "is_new_arrival": True,
        "is_best_seller": True,
        "is_recommended": True,
        "is_featured": True,
    },
    {
        "name": "Baggy Shirt",
        "slug": "baggy-shirt",
        "sku": "FD-SHIRT-01",
        "category_slug": "shirts",
        "price": "55.00",
        "image": "product-item-2.jpg",
        "is_new_arrival": True,
        "is_best_seller": False,
        "is_recommended": True,
    },
    {
        "name": "Cotton Off-White Shirt",
        "slug": "cotton-off-white-shirt",
        "sku": "FD-SHIRT-02",
        "category_slug": "shirts",
        "price": "65.00",
        "image": "product-item-3.jpg",
        "is_new_arrival": True,
        "is_best_seller": True,
        "is_recommended": False,
    },
    {
        "name": "Crop Sweater",
        "slug": "crop-sweater",
        "sku": "FD-SWEAT-01",
        "category_slug": "sweaters",
        "price": "50.00",
        "image": "product-item-4.jpg",
        "is_new_arrival": False,
        "is_best_seller": True,
        "is_recommended": True,
    },
    {
        "name": "Handmade Crop Sweater",
        "slug": "handmade-crop-sweater",
        "sku": "FD-SWEAT-02",
        "category_slug": "sweaters",
        "price": "50.00",
        "image": "product-item-6.jpg",
        "is_new_arrival": True,
        "is_best_seller": False,
        "is_recommended": False,
    },
    {
        "name": "Florish Jacket",
        "slug": "florish-jacket",
        "sku": "FD-JACK-01",
        "category_slug": "jackets",
        "price": "70.00",
        "image": "product-item-9.jpg",
        "is_new_arrival": False,
        "is_best_seller": False,
        "is_recommended": True,
    },
    {
        "name": "Classic Accessory Bag",
        "slug": "classic-accessory-bag",
        "sku": "FD-ACC-01",
        "category_slug": "accessories",
        "price": "70.00",
        "image": "product-item-10.jpg",
        "is_new_arrival": False,
        "is_best_seller": False,
        "is_recommended": False,
    },
]

DISCOUNT = {
    "name": "Launch Sale",
    "discount_type": "percent",
    "scope": "global",
    "value": "10.00",
    "priority": 10,
}


class Command(BaseCommand):
    help = "Seed the database with idempotent FemDes demo data."

    def handle(self, *args, **options):
        static_images = settings.BASE_DIR / "static" / "store" / "images"
        media_dir = Path(settings.MEDIA_ROOT) / "products" / "demo"
        media_dir.mkdir(parents=True, exist_ok=True)

        created = 0
        updated = 0

        with transaction.atomic():
            # SiteSettings
            ss, ss_created = SiteSettings.objects.update_or_create(
                pk=SiteSettings.objects.first().pk if SiteSettings.objects.exists() else None,
                defaults={
                    "store_name": "FemDes",
                    "tagline": "Modern Fashion for Every Occasion",
                    "contact_email": "hello@femdes.example.com",
                    "currency_code": "USD",
                    "currency_symbol": "$",
                },
            )
            if ss_created:
                created += 1
            else:
                updated += 1

            # Categories
            cat_map = {}
            for name, slug, sort_order in CATEGORIES:
                cat, cat_created = Category.objects.update_or_create(
                    slug=slug,
                    defaults={
                        "name": name,
                        "sort_order": sort_order,
                        "is_active": True,
                    },
                )
                cat_map[slug] = cat
                if cat_created:
                    created += 1
                else:
                    updated += 1

            # Products
            for prod_data in PRODUCTS:
                category = cat_map[prod_data["category_slug"]]
                product, prod_created = Product.objects.update_or_create(
                    sku=prod_data["sku"],
                    defaults={
                        "name": prod_data["name"],
                        "slug": prod_data["slug"],
                        "category": category,
                        "price": prod_data["price"],
                        "stock_quantity": 20,
                        "is_active": True,
                        "is_featured": prod_data.get("is_featured", False),
                        "is_new_arrival": prod_data.get("is_new_arrival", False),
                        "is_best_seller": prod_data.get("is_best_seller", False),
                        "is_recommended": prod_data.get("is_recommended", False),
                    },
                )
                if prod_created:
                    created += 1
                else:
                    updated += 1

                # ProductImage: copy from static to media
                src_path = static_images / prod_data["image"]
                if not src_path.exists():
                    raise CommandError(
                        f"Required source image not found: {src_path}"
                    )

                dest_path = media_dir / prod_data["image"]
                shutil.copy2(str(src_path), str(dest_path))

                # Remove existing demo images for idempotency
                ProductImage.objects.filter(product=product).delete()

                # Store image directly at products/demo/<filename> to avoid
                # Django's upload_to generating suffixed paths on repeat runs.
                relative_path = f"products/demo/{prod_data['image']}"
                img = ProductImage(
                    product=product,
                    alt_text=prod_data["name"],
                    sort_order=0,
                    is_primary=True,
                )
                img.image.name = relative_path
                img.save()

            # Discount
            disc, disc_created = Discount.objects.update_or_create(
                name=DISCOUNT["name"],
                defaults={
                    "discount_type": DISCOUNT["discount_type"],
                    "scope": DISCOUNT["scope"],
                    "value": DISCOUNT["value"],
                    "priority": DISCOUNT["priority"],
                    "is_active": True,
                },
            )
            if disc_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: {created} created, {updated} updated."
            )
        )
