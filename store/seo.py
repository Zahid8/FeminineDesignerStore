"""Structured data (schema.org JSON-LD) helpers."""
import json

from django.utils.safestring import mark_safe

_JSON_ESCAPES = {ord(">"): "\\u003E", ord("<"): "\\u003C", ord("&"): "\\u0026"}


def to_jsonld(data):
    """Serialize for an inline <script type="application/ld+json"> block."""
    return mark_safe(json.dumps(data, ensure_ascii=False).translate(_JSON_ESCAPES))


def product_jsonld(request, product, site_settings=None, rating=None):
    url = request.build_absolute_uri(product.get_absolute_url())
    data = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": product.name,
        "url": url,
        "description": product.short_description or product.description[:500],
        "offers": {
            "@type": "Offer",
            "url": url,
            "price": str(product.get_effective_price()),
            "priceCurrency": getattr(site_settings, "currency_code", None) or "INR",
            "availability": (
                "https://schema.org/InStock" if product.is_in_stock
                else "https://schema.org/OutOfStock"
            ),
        },
    }
    if product.sku:
        data["sku"] = product.sku
    if product.category:
        data["category"] = product.category.name
    images = [request.build_absolute_uri(i.image.url) for i in product.images.all()]
    if images:
        data["image"] = images
    if site_settings and site_settings.store_name:
        data["brand"] = {"@type": "Brand", "name": site_settings.store_name}
    if rating and rating.get("count"):
        data["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": str(rating["average"]),
            "reviewCount": rating["count"],
        }
    return to_jsonld(data)
