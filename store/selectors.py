from django.db import models
from django.shortcuts import get_object_or_404

from store.models import Category, HomeBanner, Product, ProductTag


def get_active_categories():
    return Category.objects.filter(is_active=True).order_by("sort_order", "name")


def get_active_products():
    from store.models import ProductReview

    published = ProductReview.objects.filter(product=models.OuterRef("pk"), is_published=True).values("product")
    return (
        Product.objects.filter(is_active=True)
        .filter(
            models.Q(category__isnull=True) | models.Q(category__is_active=True)
        )
        .select_related("category")
        .prefetch_related("images")
        .annotate(
            review_avg=models.Subquery(published.annotate(a=models.Avg("rating")).values("a")[:1]),
            review_count=models.Subquery(published.annotate(c=models.Count("id")).values("c")[:1]),
        )
    )


def get_product_by_slug(slug):
    return get_object_or_404(
        Product.objects.filter(is_active=True)
        .filter(
            models.Q(category__isnull=True) | models.Q(category__is_active=True)
        )
        .select_related("category")
        .prefetch_related("images"),
        slug=slug,
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


PRODUCT_SORTS = {
    "newest": ("-created_at", "-id"),
    "price_asc": ("price", "id"),
    "price_desc": ("-price", "id"),
    "name": ("name", "id"),
}


def sort_products(qs, sort_key):
    """Apply a whitelisted sort; unknown keys keep the default order."""
    ordering = PRODUCT_SORTS.get(sort_key)
    return qs.order_by(*ordering) if ordering else qs


def get_home_banners(placement="hero"):
    return HomeBanner.objects.filter(is_active=True, placement=placement).order_by("sort_order", "id")


# ── Shop facets ────────────────────────────────────────────────
import re as _re
from decimal import Decimal, InvalidOperation

from django.http import QueryDict

from store.models import Occasion

FACET_LIST_PARAMS = ("size", "color", "fabric", "occasion")
FACET_FLAG_PARAMS = {"in_stock": "In stock", "ready": "Ready to ship", "sale": "On sale"}


def _split(raw):
    return [p.strip() for p in _re.split(r"[,\n]", raw or "") if p.strip()]


def _option_regex(value):
    # Matches one entry in a comma/newline separated option list.
    return r"(^|[,\n])\s*" + _re.escape(value) + r"\s*($|[,\r\n])"


def _decimal(raw):
    try:
        value = Decimal(str(raw).strip())
    except (InvalidOperation, ValueError):
        return None
    return value if value >= 0 else None


def parse_facets(params):
    """Normalise shop filter query params into a dict."""
    facets = {key: [v for v in params.getlist(key) if v.strip()] for key in FACET_LIST_PARAMS}
    facets["price_min"] = _decimal(params.get("price_min", "")) if params.get("price_min") else None
    facets["price_max"] = _decimal(params.get("price_max", "")) if params.get("price_max") else None
    for flag in FACET_FLAG_PARAMS:
        facets[flag] = params.get(flag) == "1"
    return facets


def apply_facets(qs, facets):
    for key, field in (("size", "size_options"), ("color", "color_options")):
        if facets[key]:
            q = models.Q()
            for value in facets[key]:
                q |= models.Q(**{f"{field}__iregex": _option_regex(value)})
            qs = qs.filter(q)
    if facets["fabric"]:
        q = models.Q()
        for value in facets["fabric"]:
            q |= models.Q(fabric__iexact=value)
        qs = qs.filter(q)
    if facets["occasion"]:
        qs = qs.filter(occasions__slug__in=facets["occasion"], occasions__is_active=True)
    if facets["price_min"] is not None:
        qs = qs.filter(price__gte=facets["price_min"])
    if facets["price_max"] is not None:
        qs = qs.filter(price__lte=facets["price_max"])
    if facets["in_stock"]:
        qs = qs.filter(stock_quantity__gt=0)
    if facets["ready"]:
        qs = qs.filter(fulfilment="ready_to_ship")
    if facets["sale"]:
        qs = qs.filter(compare_at_price__gt=models.F("price"))
    return qs.distinct()


def facet_options(base_qs):
    """Values available for filtering within `base_qs` (category/tag/search scope)."""
    sizes, colors, fabrics = {}, {}, {}
    rows = base_qs.values_list("size_options", "color_options", "fabric")
    for size_raw, color_raw, fabric in rows:
        for v in _split(size_raw):
            sizes.setdefault(v.lower(), v)
        for v in _split(color_raw):
            colors.setdefault(v.lower(), v)
        if fabric and fabric.strip():
            fabrics.setdefault(fabric.strip().lower(), fabric.strip())
    size_order = ["xxs", "xs", "s", "m", "l", "xl", "xxl", "2xl", "3xl", "4xl", "5xl", "6xl"]

    def size_key(v):
        low = v.lower()
        return (0, size_order.index(low)) if low in size_order else (1, low)

    bounds = base_qs.aggregate(lo=models.Min("price"), hi=models.Max("price"))
    occasions = Occasion.objects.filter(is_active=True, products__in=base_qs).distinct()
    return {
        "sizes": sorted(sizes.values(), key=size_key),
        "colors": sorted(colors.values(), key=str.lower),
        "fabrics": sorted(fabrics.values(), key=str.lower),
        "occasions": list(occasions),
        "price_lo": bounds["lo"],
        "price_hi": bounds["hi"],
    }


def active_filter_chips(params, facets, occasion_names):
    """(label, url-without-this-filter) pairs for the active-filter bar."""
    chips = []

    def without(key, value=None):
        q = QueryDict(mutable=True)
        for k in params:
            if k == "page":
                continue
            for v in params.getlist(k):
                if k == key and (value is None or v == value):
                    continue
                q.appendlist(k, v)
        return "?" + q.urlencode() if q else "?"

    for key in FACET_LIST_PARAMS:
        for v in facets[key]:
            label = occasion_names.get(v, v) if key == "occasion" else v
            chips.append((label, without(key, v)))
    if facets["price_min"] is not None:
        chips.append((f"From {facets['price_min']}", without("price_min")))
    if facets["price_max"] is not None:
        chips.append((f"Up to {facets['price_max']}", without("price_max")))
    for flag, label in FACET_FLAG_PARAMS.items():
        if facets[flag]:
            chips.append((label, without(flag)))
    return chips


def get_shop_occasions():
    """Active occasions that have at least one product for sale."""
    return Occasion.objects.filter(is_active=True, products__in=get_active_products()).distinct()


def get_footer_pages():
    from store.models import Page

    return list(Page.objects.filter(is_published=True, show_in_footer=True).only("title", "slug"))


def has_faq():
    from store.models import FAQ

    return FAQ.objects.filter(is_published=True).exists()


def get_client_diaries(limit=8):
    from store.models import ClientDiary

    return ClientDiary.objects.filter(is_published=True).select_related("product")[:limit]
