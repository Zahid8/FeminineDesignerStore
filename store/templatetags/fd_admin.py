"""Admin-only template helpers: grouped sidebar navigation and dashboard stats.

The admin look mirrors the Feminine Designer billing app (wine sidebar with a
coloured icon tile per section, raised cards, pill badges).
"""
from datetime import timedelta
from decimal import Decimal

from django import template
from django.db.models import Sum
from django.utils import timezone
from django.utils.html import format_html_join
from django.utils.safestring import mark_safe

register = template.Library()


def _circle(cx, cy, r):
    return f"M{cx - r} {cy}a{r} {r} 0 1 0 {2 * r} 0a{r} {r} 0 1 0 {-2 * r} 0"


def _rect(x, y, w, h, rx=2):
    return (f"M{x + rx} {y}h{w - 2 * rx}a{rx} {rx} 0 0 1 {rx} {rx}v{h - 2 * rx}a{rx} {rx} 0 0 1 {-rx} {rx}"
            f"h{-(w - 2 * rx)}a{rx} {rx} 0 0 1 {-rx} {-rx}v{-(h - 2 * rx)}a{rx} {rx} 0 0 1 {rx} {-rx}z")


# Lucide-style 24px stroke icons.
ICONS = {
    "home": ["M3 10.5 12 3l9 7.5", "M5 9.5V21h14V9.5", "M9.5 21v-6h5v6"],
    "receipt": ["M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z",
                "M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8", "M12 17.5v-11"],
    "list": ["M8 6h13", "M8 12h13", "M8 18h13", "M3 6h.01", "M3 12h.01", "M3 18h.01"],
    "scissors": [_circle(6, 6, 3), _circle(6, 18, 3), "M20 4 8.12 15.88", "M14.47 14.48 20 20", "M8.12 8.12 12 12"],
    "calendar": [_rect(3, 4, 18, 18), "M16 2v4", "M8 2v4", "M3 10h18"],
    "percent": ["M19 5 5 19", _circle(6.5, 6.5, 2.5), _circle(17.5, 17.5, 2.5)],
    "package": ["m7.5 4.27 9 5.15",
                "M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z",
                "m3.3 7 8.7 5 8.7-5", "M12 22V12"],
    "image": [_rect(3, 3, 18, 18), _circle(9, 9, 2), "m21 15-3.09-3.09a2 2 0 0 0-2.82 0L6 21"],
    "layers": ["M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z",
               "m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65", "m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"],
    "tag": ["M12.59 2.59A2 2 0 0 0 11.17 2H4a2 2 0 0 0-2 2v7.17a2 2 0 0 0 .59 1.42l8.7 8.7a2.43 2.43 0 0 0 3.42 0l6.58-6.58a2.43 2.43 0 0 0 0-3.42z",
            _circle(7.5, 7.5, 0.5)],
    "star": ["M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01z"],
    "ruler": ["M21.3 15.3a2.4 2.4 0 0 1 0 3.4l-2.6 2.6a2.4 2.4 0 0 1-3.4 0L2.7 8.7a2.41 2.41 0 0 1 0-3.4l2.6-2.6a2.41 2.41 0 0 1 3.4 0Z",
              "m14.5 12.5 2-2", "m11.5 9.5 2-2", "m8.5 6.5 2-2", "m17.5 15.5 2-2"],
    "bell": ["M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9", "M10.3 21a1.94 1.94 0 0 0 3.4 0"],
    "user": ["M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2", _circle(12, 7, 4)],
    "users": ["M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2", _circle(9, 7, 4), "M22 21v-2a4 4 0 0 0-3-3.87",
              "M16 3.13a4 4 0 0 1 0 7.75"],
    "shield": ["M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"],
    "mail": [_rect(2, 4, 20, 16), "m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"],
    "message": ["M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"],
    "key": [_circle(7.5, 15.5, 5.5), "m21 2-9.6 9.6", "m15.5 7.5 3 3L22 7l-3-3"],
    "file": ["M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z", "M14 2v4a2 2 0 0 0 2 2h4", "M16 13H8", "M16 17H8", "M10 9H8"],
    "help": [_circle(12, 12, 10), "M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3", "M12 17h.01"],
    "book": ["M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z", "M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"],
    "sliders": ["M4 21v-7", "M4 10V3", "M12 21v-9", "M12 8V3", "M20 21v-5", "M20 12V3", "M2 14h4", "M10 8h4", "M18 16h4"],
    "globe": [_circle(12, 12, 10), "M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20", "M2 12h20"],
    "dot": [_circle(12, 12, 3)],
}

# (group label, colour, [(model object_name lower, icon)])
SECTIONS = [
    ("Sales", "#b45309", [("order", "receipt"), ("orderitem", "list"), ("customizationrequest", "scissors"),
                          ("appointment", "calendar"), ("discount", "percent")]),
    ("Catalogue", "#7d1f36", [("product", "package"), ("productimage", "image"), ("category", "layers"),
                              ("producttag", "tag"), ("occasion", "star"), ("sizechart", "ruler"),
                              ("stockalert", "bell")]),
    ("Customers", "#0f766e", [("customerprofile", "user"), ("user", "users"), ("group", "shield"),
                              ("newslettersubscriber", "mail"), ("feedback", "message"), ("phoneotp", "key")]),
    ("Content", "#4f46e5", [("homebanner", "image"), ("page", "file"), ("faq", "help"), ("clientdiary", "book")]),
    ("Settings", "#475569", [("sitesettings", "sliders")]),
]
_LOOKUP = {model: (label, colour, icon) for label, colour, models in SECTIONS for model, icon in models}
OTHER = ("Other", "#0f6e8c", "globe")


@register.simple_tag
def fd_icon(name, size=16):
    paths = ICONS.get(name, ICONS["dot"])
    inner = format_html_join("", '<path d="{}"/>', ((d,) for d in paths))
    return mark_safe(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(size)}" height="{int(size)}" viewBox="0 0 24 24" '
        f'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true">{inner}</svg>'
    )


@register.simple_tag
def fd_nav_groups(available_apps, path=""):
    """Regroup the admin's permitted models into billing-style sections."""
    order = [label for label, _c, _m in SECTIONS] + [OTHER[0]]
    rank = {model: i for _l, _c, models in SECTIONS for i, (model, _ic) in enumerate(models)}
    groups = {}
    for app in available_apps or []:
        for model in app.get("models", []):
            key = model["object_name"].lower()
            label, colour, icon = _LOOKUP.get(key, OTHER)
            url = model.get("admin_url") or ""
            groups.setdefault(label, []).append({
                "key": key,
                "name": model["name"],
                "url": url,
                "add_url": model.get("add_url") or "",
                "icon": icon,
                "colour": colour,
                "current": bool(url) and path.startswith(url),
                "rank": rank.get(key, 99),
            })
    return [
        {"label": label, "items": sorted(groups[label], key=lambda m: (m["rank"], m["name"]))}
        for label in order if label in groups
    ]


@register.simple_tag
def fd_dashboard():
    """Headline numbers and recent activity for the admin home page."""
    from store.models import Appointment, CustomizationRequest, Order, Product, SiteSettings

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    site = SiteSettings.objects.first()
    open_statuses = ("pending", "confirmed", "processing")
    revenue = (Order.objects.filter(payment_status="paid", created_at__gte=month_start)
               .exclude(status="cancelled").aggregate(s=Sum("total"))["s"]) or Decimal("0.00")
    return {
        "currency": getattr(site, "currency_symbol", "") or "₹",
        "open_orders": Order.objects.filter(status__in=open_statuses).count(),
        "payments_to_review": Order.objects.filter(payment_status="awaiting_review").count(),
        "revenue_month": revenue,
        "orders_month": Order.objects.filter(created_at__gte=month_start).exclude(status="cancelled").count(),
        "fitting_requests_week": CustomizationRequest.objects.filter(created_at__gte=now - timedelta(days=7)).count(),
        "appointments_new": Appointment.objects.filter(status="new").count(),
        "low_stock": Product.objects.filter(is_active=True, stock_quantity__lte=2).count(),
        "recent_orders": list(Order.objects.order_by("-created_at")[:8]),
        "recent_requests": list(CustomizationRequest.objects.select_related("product").order_by("-created_at")[:5]),
    }
