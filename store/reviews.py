"""Ratings & reviews. Only customers whose order with the piece was delivered can review it."""
from django.db.models import Avg, Count

from store.models import OrderItem, ProductReview

REVIEWABLE_STATUSES = ("delivered", "completed")


def summary(product):
    qs = ProductReview.objects.filter(product=product, is_published=True)
    agg = qs.aggregate(avg=Avg("rating"), n=Count("id"))
    count = agg["n"] or 0
    if not count:
        return {"count": 0, "average": None, "bars": []}
    by_star = dict(qs.values_list("rating").annotate(c=Count("id")))
    bars = [{"stars": s, "count": by_star.get(s, 0), "pct": round(by_star.get(s, 0) * 100 / count)} for s in range(5, 0, -1)]
    fits = dict(qs.exclude(fit="").values_list("fit").annotate(c=Count("id")))
    fit_total = sum(fits.values())
    fit_line = ""
    if fit_total >= 2:
        top = max(fits, key=fits.get)
        fit_line = {"small": "Most say it runs small", "true": "Most say it's true to size", "large": "Most say it runs large"}[top] + f" ({round(fits[top] * 100 / fit_total)}%)"
    return {"count": count, "average": round(agg["avg"], 1), "bars": bars, "fit_line": fit_line}


def purchased_item(user, product):
    """The customer's delivered order line for this product, if any."""
    if not getattr(user, "is_authenticated", False):
        return None
    return (OrderItem.objects.filter(order__customer_user=user, product=product, order__status__in=REVIEWABLE_STATUSES)
            .order_by("-order__created_at").first())


def can_review(user, product):
    return purchased_item(user, product) is not None
