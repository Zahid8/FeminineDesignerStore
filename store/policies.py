"""Store policies editable in Admin → Site settings (with safe defaults)."""
from django.conf import settings

from store.models import SiteSettings
from store.terms import ONLINE_ORDER_TERMS


def _site():
    return SiteSettings.objects.first()


def get(name, default):
    value = getattr(_site(), name, None)
    return default if value in (None, "") else value


def delivery_days():
    lo = get("delivery_days_min", getattr(settings, "DELIVERY_DAYS_MIN", 4))
    hi = get("delivery_days_max", getattr(settings, "DELIVERY_DAYS_MAX", 8))
    return min(lo, hi), max(lo, hi)


def unpaid_release_minutes():
    return get("unpaid_order_release_minutes", getattr(settings, "UNPAID_ORDER_RELEASE_MINUTES", 60))


def exchange_days():
    return get("exchange_days", 7)


def alteration_days():
    return get("alteration_days", 30)


def problem_hours():
    return get("problem_report_hours", 48)


def online_terms():
    """Terms printed on online bills: the admin's lines, or the standard set (with the admin's windows)."""
    custom = (get("online_order_terms", "") or "").strip()
    if custom:
        return [line.strip() for line in custom.splitlines() if line.strip()]
    return [t.replace("within 48 hours", f"within {problem_hours()} hours").replace("within 7 days", f"within {exchange_days()} days")
            for t in ONLINE_ORDER_TERMS]
