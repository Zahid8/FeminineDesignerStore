"""Idempotent demo store seed command — blouse-only catalog."""

import shutil
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from store.models import (
    Category,
    Discount,
    Product,
    ProductImage,
    SiteSettings,
)

# Single blouse category
CATEGORIES = [
    ("Blouses", "blouses", 1),
]

# 10 available source images under static/store/images/
_SRC_IMAGES = [
    "product-item-1.jpg", "product-item-2.jpg", "product-item-3.jpg",
    "product-item-4.jpg", "product-item-5.jpg", "product-item-6.jpg",
    "product-item-7.jpg", "product-item-8.jpg", "product-item-9.jpg",
    "product-item-10.jpg",
]

# 15 blouse names → deterministic SKUs, slugs
_BLOUSE_NAMES = [
    "Silk Embroidered Blouse",
    "Cotton Linen Blouse",
    "Chiffon Party Blouse",
    "Georgette Designer Blouse",
    "Velvet Evening Blouse",
    "Jacquard Silk Blouse",
    "Organza Floral Blouse",
    "Crepe Satin Blouse",
    "Net Embellished Blouse",
    "Chanderi Handloom Blouse",
    "Banarasi Brocade Blouse",
    "Kanjeevaram Silk Blouse",
    "Raw Silk Printed Blouse",
    "Art Silk Wedding Blouse",
    "Tussar Heritage Blouse",
]

PRODUCTS = []
for i, name in enumerate(_BLOUSE_NAMES, 1):
    slug = name.lower().replace(" ", "-")
    sku = f"FD-BLOUSE-{i:02d}"
    img_start = ((i - 1) * 4) % 10
    images = [_SRC_IMAGES[(img_start + j) % 10] for j in range(4)]
    PRODUCTS.append({
        "name": name,
        "slug": slug,
        "sku": sku,
        "category_slug": "blouses",
        "price": str(Decimal(50 + (i * 5) % 50)),
        "images": images,
        "is_new_arrival": i <= 4,
        "is_best_seller": 5 <= i <= 8,
        "is_recommended": i >= 9,
        "is_featured": i == 1,
    })

DISCOUNT = {
    "name": "Launch Sale",
    "discount_type": "percent",
    "scope": "global",
    "value": "10.00",
    "priority": 10,
}

# SKU prefixes for old seed products to deactivate (non-blouse cleanup)
_OLD_SKU_PREFIXES = ("FD-DRESS-", "FD-SHIRT-", "FD-SWEAT-", "FD-JACK-", "FD-ACC-")


class Command(BaseCommand):
    help = "Seed the database with idempotent FemDes blouse demo data."

    def handle(self, *args, **options):
        static_images = settings.BASE_DIR / "static" / "store" / "images"
        media_dir = Path(settings.MEDIA_ROOT) / "products" / "demo"
        media_dir.mkdir(parents=True, exist_ok=True)

        created = 0
        updated = 0

        with transaction.atomic():
            # Deactivate old non-blouse seed products (explicit per-prefix Q)
            old_q = Q()
            for prefix in _OLD_SKU_PREFIXES:
                old_q |= Q(sku__startswith=prefix)
            Product.objects.filter(old_q, is_active=True).update(is_active=False)

            # SiteSettings
            ss, ss_created = SiteSettings.objects.update_or_create(
                pk=SiteSettings.objects.first().pk if SiteSettings.objects.exists() else None,
                defaults={
                    "store_name": "FemDes",
                    "tagline": "Custom Blouse Boutique",
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
                        "default_length": Decimal("10.00"),
                        "default_chest": Decimal("10.00"),
                        "default_waist": Decimal("10.00"),
                        "default_armhole": Decimal("10.00"),
                        "default_opening": Decimal("10.00"),
                        "default_bicep": Decimal("10.00"),
                    },
                )
                if prod_created:
                    created += 1
                else:
                    updated += 1

                # Remove existing demo images for idempotency
                ProductImage.objects.filter(product=product).delete()

                # Create 4 images per blouse
                for j, img_name in enumerate(prod_data["images"]):
                    src_path = static_images / img_name
                    if not src_path.exists():
                        raise CommandError(
                            f"Required source image not found: {src_path}"
                        )

                    dest_name = f"fd-blouse-{product.sku.split('-')[-1]}-{j + 1}.jpg"
                    dest_path = media_dir / dest_name
                    shutil.copy2(str(src_path), str(dest_path))

                    relative_path = f"products/demo/{dest_name}"
                    img = ProductImage(
                        product=product,
                        alt_text=f"{prod_data['name']} - {j + 1}",
                        sort_order=j,
                        is_primary=(j == 0),
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
