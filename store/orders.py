"""After-purchase order actions: timeline, cancel, exchange/alteration/problem requests, buy again.

Rules follow the online-order terms (store/terms.py):
- cancel before the order moves to processing (before dispatch / stitching);
- ready-made pieces: exchange within 7 days of delivery;
- made-to-measure pieces: free alteration (we allow 30 days to ask);
- damaged / missing / wrong item: report within 48 hours of delivery.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from store.models import Order, OrderRequest, Product

logger = logging.getLogger(__name__)

EXCHANGE_DAYS = 7
ALTERATION_DAYS = 30
PROBLEM_HOURS = 48

CANCEL_REASONS = [
    ("changed_mind", "I changed my mind"),
    ("ordered_by_mistake", "Ordered by mistake"),
    ("better_price", "Found a better price"),
    ("delivery_too_late", "Delivery date is too late"),
    ("wrong_details", "Wrong size, measurements or address"),
    ("other", "Other"),
]

STEP_LABELS = [
    ("pending", "Order placed"),
    ("confirmed", "Confirmed"),
    ("processing", "Being prepared"),
    ("shipped", "Shipped"),
    ("delivered", "Delivered"),
]
_RANK = {s: i for i, (s, _) in enumerate(STEP_LABELS)}
_RANK["completed"] = _RANK["delivered"]


def timeline(order):
    """Steps for the tracking view: label, date (first time reached), done/current flags."""
    reached = {}
    for ev in order.events.all():
        reached.setdefault(ev.status, ev.created_at)
    reached.setdefault("pending", order.created_at)
    if order.status == "cancelled":
        steps = [{"status": "pending", "label": "Order placed", "at": reached.get("pending"), "done": True}]
        for s, label in STEP_LABELS[1:]:
            if s in reached:
                steps.append({"status": s, "label": label, "at": reached[s], "done": True})
        steps.append({"status": "cancelled", "label": "Cancelled", "at": order.cancelled_at or reached.get("cancelled"),
                      "done": True, "current": True, "cancelled": True})
        return steps
    current = _RANK.get(order.status, 0)
    steps = []
    for i, (s, label) in enumerate(STEP_LABELS):
        if s == "processing" and order.items.filter(customization__isnull=False).exists():
            label = "Being stitched"
        at = reached.get(s) or (order.delivered_at if s == "delivered" else order.shipped_at if s == "shipped" else None)
        steps.append({"status": s, "label": label, "at": at if i <= current else None, "done": i <= current, "current": i == current})
    return steps


# ── Cancel ──────────────────────────────────────────────────────────────
def can_cancel(order):
    return order.status in Order.CANCELLABLE_STATUSES and order.payment_status != "refunded"


def restock(order):
    for item in order.items.all():
        if item.product_id and not item.customization:
            Product.objects.filter(pk=item.product_id).update(stock_quantity=F("stock_quantity") + item.quantity)


def cancel_order(order_pk, reason="", by="customer", note=""):
    """Cancel and give ready-made stock back. Returns the order, or None if it can't be cancelled."""
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order_pk)
        if order.status == "cancelled" or (by == "customer" and not can_cancel(order)):
            return None
        restock(order)
        order.status = "cancelled"
        order.cancel_reason = (reason or "")[:200]
        order.cancelled_by = by
        order._event_note = note or (f"Cancelled by {by}" + (f": {reason}" if reason else ""))
        if order.payment_status == "paid":
            order.payment_notes = (order.payment_notes + "\n" if order.payment_notes else "") + \
                f"REFUND DUE: order cancelled by {by} after online payment ({order.total})."
        order.save()
    transaction.on_commit(lambda: _notify_cancelled(order))
    return order


def _notify_cancelled(order):
    from django.core.mail import send_mail

    lines = [f"Order {order.order_number} has been cancelled."]
    if order.cancel_reason:
        lines.append(f"Reason: {order.cancel_reason}")
    if order.payment_status == "paid":
        lines.append(f"A refund of {order.total} will be made to the original payment method within 5–7 working days.")
    try:
        send_mail(f"Order {order.order_number} cancelled", "\n".join(lines), settings.DEFAULT_FROM_EMAIL, [order.customer_email])
        if settings.STORE_NOTIFY_EMAIL:
            send_mail(f"Cancelled ({order.cancelled_by}): {order.order_number} — {order.customer_name}",
                      "\n".join(lines + ([f"Paid online — refund due ({order.gateway_payment_id})."] if order.payment_status == "paid" else [])),
                      settings.DEFAULT_FROM_EMAIL, [settings.STORE_NOTIFY_EMAIL])
    except Exception:
        logger.exception("Cancel email failed for %s", order.order_number)


# ── Exchange / alteration / problem ─────────────────────────────────────
def request_options(order, now=None):
    """Which after-sales requests are open for this order, with their deadline."""
    now = now or timezone.now()
    if order.status not in ("delivered", "completed"):
        return []
    from store import policies

    EXCHANGE_DAYS, ALTERATION_DAYS, PROBLEM_HOURS = policies.exchange_days(), policies.alteration_days(), policies.problem_hours()
    delivered = order.delivered_at or order.updated_at
    items = list(order.items.all())
    open_kinds = []
    if any(not i.customization for i in items) and now <= delivered + timedelta(days=EXCHANGE_DAYS):
        open_kinds.append(("exchange", delivered + timedelta(days=EXCHANGE_DAYS)))
    if any(i.customization for i in items) and now <= delivered + timedelta(days=ALTERATION_DAYS):
        open_kinds.append(("alteration", delivered + timedelta(days=ALTERATION_DAYS)))
    if now <= delivered + timedelta(hours=PROBLEM_HOURS):
        open_kinds.append(("problem", delivered + timedelta(hours=PROBLEM_HOURS)))
    return open_kinds


def eligible_items(order, kind):
    items = order.items.all()
    if kind == "exchange":
        return [i for i in items if not i.customization]
    if kind == "alteration":
        return [i for i in items if i.customization]
    return list(items)


def create_request(order, kind, reason, item_ids, details="", preferred_size=""):
    if kind not in dict(request_options(order)):
        raise ValueError("This request is no longer available for this order.")
    allowed = {i.pk: i for i in eligible_items(order, kind)}
    chosen = [allowed[i] for i in item_ids if i in allowed]
    if not chosen:
        raise ValueError("Choose at least one item.")
    if reason not in dict(OrderRequest.REASONS):
        raise ValueError("Choose a reason.")
    if order.requests.filter(kind=kind, status__in=["requested", "approved", "pickup"]).exists():
        raise ValueError("You already have an open request of this kind for this order.")
    req = OrderRequest.objects.create(order=order, kind=kind, reason=reason, details=details[:2000], preferred_size=preferred_size[:40])
    req.items.set(chosen)
    try:
        from django.core.mail import send_mail
        if settings.STORE_NOTIFY_EMAIL:
            send_mail(f"{req.get_kind_display()} request: {order.order_number}",
                      f"{order.customer_name} ({order.customer_phone or order.customer_email})\n"
                      f"Items: {', '.join(i.product_name for i in chosen)}\nReason: {req.get_reason_display()}\n"
                      f"Size wanted: {preferred_size or '-'}\n\n{details}",
                      settings.DEFAULT_FROM_EMAIL, [settings.STORE_NOTIFY_EMAIL])
    except Exception:
        logger.exception("Request email failed for %s", order.order_number)
    return req


# ── Buy again ───────────────────────────────────────────────────────────
def buy_again(request, order):
    """Put the order's pieces back in the bag. Returns (added, skipped_names)."""
    from store import services

    added, skipped = 0, []
    for item in order.items.select_related("product"):
        product = item.product
        if product is None or not product.is_active:
            skipped.append(item.product_name)
            continue
        try:
            custom = None
            if item.customization:
                custom = dict(item.customization)
            services.add_to_cart(request, product, quantity=item.quantity if not custom else 1,
                                 color=item.color, size=item.size, custom=custom)
            added += 1
        except ValueError:
            skipped.append(item.product_name)
    return added, skipped
