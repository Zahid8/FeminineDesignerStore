"""Delivery date estimates for a PIN code (shown on the bag, product page and checkout).

Ready-made: today + DELIVERY_DAYS_MIN..DELIVERY_DAYS_MAX calendar days.
Made to measure: the stitching lead time (e.g. "3–4 weeks") + DELIVERY_DAYS_MAX.
"""
import re
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from store.pincode import lookup


def _lead_days(text):
    """'3–4 weeks' → 28, '10 days' → 10, '' → 28."""
    numbers = [int(n) for n in re.findall(r"\d+", text or "")]
    if not numbers:
        return 28
    n = max(numbers)
    return n * 7 if "week" in (text or "").lower() else n


def _fmt(d):
    return d.strftime("%a, %-d %b")


def estimate(pin, custom_lead_text="", today=None):
    place = lookup(pin)
    if not place:
        return None
    today = today or timezone.localdate()
    from store.policies import delivery_days

    lo, hi = delivery_days()
    ready_from, ready_by = today + timedelta(days=lo), today + timedelta(days=hi)
    custom_by = today + timedelta(days=_lead_days(custom_lead_text) + hi)
    return {
        "city": place.get("city", ""), "state": place.get("state", ""),
        "ready": f"Delivery by {_fmt(ready_by)}", "ready_from": ready_from.isoformat(), "ready_by": ready_by.isoformat(),
        "custom": f"Made to measure · delivery by {_fmt(custom_by)}", "custom_by": custom_by.isoformat(),
    }
