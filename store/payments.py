"""Online payment bookkeeping shared by the Razorpay callback, webhook and jobs.

- ``mark_paid``: idempotent; the browser callback and the webhook may both
  arrive, the order is updated (and the customer emailed) exactly once.
- ``release_unpaid_orders``: online orders never paid within the timeout give
  their ready-made stock back and are cancelled. Called lazily (throttled) from
  checkout/API traffic and by the ``release_unpaid_orders`` command.
- ``order_access_key`` / ``can_view_order``: order pages are visible to the
  browser that placed the order, the signed-in owner, staff, or anyone holding
  the signed link sent by email.
"""
import hashlib
import hmac
import logging
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import F
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import salted_hmac

from store.models import Order, Product

logger = logging.getLogger(__name__)

SESSION_ORDERS_KEY = "placed_orders"


# ── Who may see an order page ────────────────────────────────────────────
def order_access_key(order_number):
    return salted_hmac("femdes.order-access", order_number).hexdigest()[:24]


def remember_order(request, order):
    placed = request.session.get(SESSION_ORDERS_KEY, [])
    if order.order_number not in placed:
        request.session[SESSION_ORDERS_KEY] = (placed + [order.order_number])[-20:]


def can_view_order(request, order):
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated and (user.is_staff or order.customer_user_id == user.pk):
        return True
    if order.order_number in request.session.get(SESSION_ORDERS_KEY, []):
        return True
    key = request.GET.get("k") or request.POST.get("k") or ""
    return bool(key) and hmac.compare_digest(key, order_access_key(order.order_number))


def order_link(order, name="order_success", request=None):
    """Signed link to an order page, absolute when a request (or SITE_URL) is available."""
    path = reverse(name, kwargs={"order_number": order.order_number}) + f"?k={order_access_key(order.order_number)}"
    if request is not None:
        return request.build_absolute_uri(path)
    return (getattr(settings, "SITE_URL", "") or "") + path


# ── Paid ────────────────────────────────────────────────────────────────
def can_pay_online(order):
    return order.payment_method == "razorpay" and order.payment_status not in ("paid", "refunded") and order.status != "cancelled"


def mark_paid(order_pk, payment_id, signature="", source="checkout"):
    """Record a confirmed online payment. Returns True only for the first confirmation."""
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order_pk)
        if order.payment_status == "paid":
            return False
        revived = order.status == "cancelled"
        order.payment_status = "paid"
        order.payment_method = "razorpay"
        order.payment_reference = payment_id
        order.gateway_payment_id = payment_id
        if signature:
            order.gateway_signature = signature
        order.paid_at = timezone.now()
        if order.status in ("pending", "cancelled"):
            order.status = "confirmed"
        note = f"Paid online via Razorpay ({source}), payment {payment_id}."
        if revived:
            # Released by the timeout but paid afterwards: take the stock again.
            for item in order.items.select_related("product"):
                if item.product_id and not item.customization:
                    Product.objects.filter(pk=item.product_id).update(stock_quantity=F("stock_quantity") - item.quantity)
                    Product.objects.filter(pk=item.product_id, stock_quantity__lt=0).update(stock_quantity=0)
            note += " Payment arrived after the order had been auto-cancelled; stock re-reserved, please check availability."
        order.payment_notes = (order.payment_notes + "\n" if order.payment_notes else "") + note
        order.save()
    transaction.on_commit(lambda: send_payment_received_email(order))
    return True


def send_payment_received_email(order):
    from django.core.mail import send_mail
    from django.template.loader import render_to_string

    from store.models import SiteSettings

    site = SiteSettings.objects.first()
    ctx = {"order": order, "site_settings": site, "order_url": order_link(order) if getattr(settings, "SITE_URL", "") else ""}
    store_name = getattr(site, "store_name", "FemDes")
    try:
        send_mail(
            f"{store_name}: payment received for order {order.order_number}",
            render_to_string("store/emails/payment_received.txt", ctx),
            settings.DEFAULT_FROM_EMAIL,
            [order.customer_email],
        )
        if settings.STORE_NOTIFY_EMAIL:
            send_mail(
                f"Paid: order {order.order_number} — {order.customer_name} ({order.total})",
                render_to_string("store/emails/payment_received.txt", ctx),
                settings.DEFAULT_FROM_EMAIL,
                [settings.STORE_NOTIFY_EMAIL],
            )
    except Exception:
        logger.exception("Payment email failed for %s", order.order_number)


def mark_failed(order_pk, reason=""):
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order_pk)
        if order.payment_status in ("paid", "refunded"):
            return False
        order.payment_status = "failed"
        if reason:
            order.payment_notes = (order.payment_notes + "\n" if order.payment_notes else "") + f"Online payment failed: {reason}"[:500]
        order.save()
    return True


# ── Unpaid online orders give their stock back ───────────────────────────
def release_unpaid_orders(older_than_minutes=None, now=None):
    minutes = older_than_minutes if older_than_minutes is not None else getattr(settings, "UNPAID_ORDER_RELEASE_MINUTES", 60)
    cutoff = (now or timezone.now()) - timedelta(minutes=minutes)
    released = []
    candidates = Order.objects.filter(
        payment_method="razorpay", payment_status__in=["pending", "failed"], status="pending", created_at__lt=cutoff,
    ).values_list("pk", flat=True)
    for pk in list(candidates):
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=pk)
            if order.payment_status not in ("pending", "failed") or order.status != "pending":
                continue
            for item in order.items.all():
                if item.product_id and not item.customization:
                    Product.objects.filter(pk=item.product_id).update(stock_quantity=F("stock_quantity") + item.quantity)
            order.status = "cancelled"
            order.payment_notes = (order.payment_notes + "\n" if order.payment_notes else "") + (
                f"Auto-cancelled: online payment not completed within {minutes} minutes; stock released.")
            order.save()
            released.append(order.order_number)
    return released


def release_unpaid_orders_soon():
    """Throttled lazy run so the job happens without a scheduler."""
    if cache.add("femdes:release-unpaid", 1, timeout=300):
        try:
            release_unpaid_orders()
        except Exception:
            logger.exception("Releasing unpaid orders failed")


# ── Webhook signature ───────────────────────────────────────────────────
def webhook_signature_ok(body: bytes, signature: str) -> bool:
    secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "")
    if not (secret and signature):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
