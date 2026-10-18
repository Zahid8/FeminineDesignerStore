"""Promo codes: validation and discount maths.

The applied code lives in the session (``SESSION_KEY``). It is re-checked every
time totals are worked out and again when the order is placed, so an expired
or used-up code can never slip through.
"""
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Q
from django.utils import timezone

from store.models import Coupon, Order

SESSION_KEY = "coupon_code"
CENT = Decimal("0.01")


class CouponError(ValueError):
    pass


def _uses(coupon, extra=None):
    qs = Order.objects.filter(coupon_code__iexact=coupon.code).exclude(status="cancelled")
    return qs.filter(extra) if extra is not None else qs


def check(code, merchandise, user=None, email=""):
    """Return (coupon, discount) for ``code`` on ``merchandise`` (after sale prices), or raise CouponError."""
    code = (code or "").strip().upper()
    if not code:
        raise CouponError("Enter a coupon code.")
    coupon = Coupon.objects.filter(code__iexact=code, is_active=True).first()
    now = timezone.now()
    if coupon is None or (coupon.starts_at and coupon.starts_at > now):
        raise CouponError(f"{code} is not a valid coupon.")
    if coupon.ends_at and coupon.ends_at < now:
        raise CouponError(f"{code} has expired.")
    if merchandise < coupon.min_order_amount:
        short = (coupon.min_order_amount - merchandise).quantize(CENT)
        raise CouponError(f"Add ₹{short} more to use {code} (minimum order ₹{coupon.min_order_amount}).")
    if coupon.usage_limit is not None and _uses(coupon).count() >= coupon.usage_limit:
        raise CouponError(f"{code} has been fully used.")
    who = Q()
    if user is not None and getattr(user, "is_authenticated", False):
        who |= Q(customer_user=user)
        email = email or user.email
    if email:
        who |= Q(customer_email__iexact=email)
    if who:
        if coupon.per_customer_limit and _uses(coupon, who).count() >= coupon.per_customer_limit:
            raise CouponError(f"You have already used {code}.")
        if coupon.first_order_only and Order.objects.filter(who).exclude(status="cancelled").exists():
            raise CouponError(f"{code} is for your first order only.")
    elif coupon.first_order_only:
        pass  # checked again at checkout once we know the email
    return coupon, discount_for(coupon, merchandise)


def discount_for(coupon, merchandise):
    if coupon.discount_type == "percent":
        amount = merchandise * coupon.value / Decimal("100")
        if coupon.max_discount:
            amount = min(amount, coupon.max_discount)
    else:
        amount = coupon.value
    return min(amount, merchandise).quantize(CENT, rounding=ROUND_HALF_UP)


def visible_offers(merchandise=None):
    now = timezone.now()
    qs = Coupon.objects.filter(is_active=True, show_in_bag=True).filter(
        Q(starts_at__isnull=True) | Q(starts_at__lte=now), Q(ends_at__isnull=True) | Q(ends_at__gte=now))
    offers = []
    for c in qs[:6]:
        if c.usage_limit is not None and _uses(c).count() >= c.usage_limit:
            continue
        offers.append(c)
    return offers
