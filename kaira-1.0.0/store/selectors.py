from django.db import models
from django.shortcuts import get_object_or_404

from store.models import Category, Product, ProductTag


def get_active_categories():
    return Category.objects.filter(is_active=True).order_by("sort_order", "name")


def get_active_products():
    return (
        Product.objects.filter(is_active=True)
        .filter(
            models.Q(category__isnull=True) | models.Q(category__is_active=True)
        )
        .select_related("category")
        .prefetch_related("images")
    )


def get_product_by_slug(slug):
    return get_object_or_404(
        Product.objects.select_related("category").prefetch_related("images"),
        slug=slug,
        is_active=True,
    )


def get_active_tags():
    return ProductTag.objects.filter(is_active=True).order_by("sort_order", "name")


def get_homepage_products():
    base = (
        Product.objects.filter(
            is_active=True, category__is_active=True, stock_quantity__gt=0
        )
        .select_related("category")
        .prefetch_related("images")
    )
    return {
        "featured": base.filter(is_featured=True),
        "new_arrivals": base.filter(is_new_arrival=True),
        "best_sellers": base.filter(is_best_seller=True),
        "recommended": base.filter(is_recommended=True),
    }


def filter_products(category_slug=None, tag_slug=None, query=None):
    qs = get_active_products()
    if category_slug:
        qs = qs.filter(category__slug=category_slug)
    if tag_slug:
        qs = qs.filter(tags__slug=tag_slug, tags__is_active=True)
    if query:
        qs = qs.filter(
            models.Q(name__icontains=query)
            | models.Q(sku__icontains=query)
            | models.Q(short_description__icontains=query)
        )
    return qs.distinct()
