"""JSON API for the Feminine Designer billing app ("Online Orders").

Authentication: `Authorization: Bearer <WEBSTORE_API_TOKEN>`. The API is
disabled (503) until the token is configured. Responses are plain JSON; the
billing app fetches them server-side, so no CORS is needed.
"""
import hmac
import json
from functools import wraps

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from store import policies
from store import measurements as mspec
from store.models import Order, SiteSettings, OrderRequest

MAX_LIMIT = 200


def _error(message, status):
    return JsonResponse({"error": message}, status=status)


def api_token_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        token = getattr(settings, "WEBSTORE_API_TOKEN", "")
        if not token:
            return _error("Webstore API is not configured (WEBSTORE_API_TOKEN).", 503)
        header = request.headers.get("Authorization", "")
        supplied = header[7:].strip() if header.startswith("Bearer ") else ""
        if not supplied or not hmac.compare_digest(supplied, token):
            return _error("Invalid or missing API token.", 401)
        return view(request, *args, **kwargs)
    return wrapper


def _absolute(request, url):
    return request.build_absolute_uri(url) if (request is not None and url) else url


def serialize_item(item, request=None):
    custom = item.customization or None
    product = item.product if item.product_id else None
    image = product.primary_image if product else None
    return {
        "product_name": item.product_name,
        "sku": item.sku,
        "quantity": item.quantity,
        "unit_price": str(item.unit_price),
        "discount_amount": str(item.discount_amount),
        "line_total": str(item.line_total),
        "color": item.color,
        "size": item.size,
        "made_to_measure": bool(custom),
        "customization": custom,
        "customization_summary": [{"label": l, "value": v} for l, v in mspec.summary(custom)] if custom else [],
        "sleeve_style": (custom or {}).get("sleeve_style") or "",
        "sleeve_style_label": mspec.SLEEVE_LABELS.get((custom or {}).get("sleeve_style") or "", "") if custom else "",
        "tailor_notes": (custom or {}).get("notes") or "",
        "category": product.category.name if product and product.category_id else "",
        "image_url": _absolute(request, image.image.url) if image and image.image else None,
        "product_url": _absolute(request, product.get_absolute_url()) if product else None,
    }


ORDER_TYPES = [
    ("ready_made", "Ready-made"),
    ("made_to_measure", "Custom size"),
    ("mixed", "Ready-made + custom size"),
]


def order_type(order):
    """ready_made, made_to_measure (every piece custom) or mixed."""
    custom = [bool(i.customization) for i in order.items.all()]
    if custom and all(custom):
        return "made_to_measure"
    return "mixed" if any(custom) else "ready_made"


def _customer_order_counts(orders):
    """Orders placed per customer email (case-insensitive), for 'returning customer' badges."""
    from django.db.models import Count
    from django.db.models.functions import Lower

    emails = {o.customer_email.lower() for o in orders if o.customer_email}
    if not emails:
        return {}
    rows = (Order.objects.annotate(e=Lower("customer_email")).filter(e__in=emails)
            .values("e").annotate(n=Count("id")))
    return {r["e"]: r["n"] for r in rows}


def serialize_order(request, order, site=None, order_counts=None):
    kind = order_type(order)
    if order_counts is None:
        order_counts = _customer_order_counts([order])
    account = order.customer_user
    profile = getattr(account, "profile", None) if account else None
    return {
        "order_number": order.order_number,
        "status": order.status,
        "status_label": order.get_status_display(),
        "payment_status": order.payment_status,
        "payment_status_label": order.get_payment_status_display(),
        "payment_method": order.payment_method,
        "payment_method_label": order.get_payment_method_display(),
        "payment_reference": order.payment_reference,
        "payment_notes": order.payment_notes,
        "gateway": {
            "order_id": order.gateway_order_id,
            "payment_id": order.gateway_payment_id,
        } if (order.gateway_order_id or order.gateway_payment_id) else None,
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        "created_at": order.created_at.isoformat(),
        "updated_at": order.updated_at.isoformat(),
        "customer": {
            "name": order.customer_name,
            "email": order.customer_email,
            "phone": order.customer_phone,
            "account_id": order.customer_user_id,
            "has_account": bool(account),
            "account_username": account.get_username() if account else "",
            "verified_phone": (profile.phone_e164 or "") if profile else "",
            "orders_count": order_counts.get((order.customer_email or "").lower(), 1),
        },
        "shipping_address": order.shipping_address,
        "shipping": {
            "line1": order.address_line1, "line2": order.address_line2, "city": order.city,
            "state": order.state, "pincode": order.pincode, "country": order.country or "India",
        },
        "location_url": order.location_url or None,
        "notes": order.notes,
        "currency": getattr(site, "currency_code", None) or "INR",
        "subtotal": str(order.subtotal),
        "discount_total": str(order.discount_total),
        "coupon": {"code": order.coupon_code, "discount": str(order.coupon_discount)} if order.coupon_code else None,
        "gift_message": order.gift_message,
        "bill_terms": policies.online_terms(),
        "shipping_total": str(order.shipping_total),
        "total": str(order.total),
        "item_count": sum(i.quantity for i in order.items.all()),
        "has_made_to_measure": kind != "ready_made",
        "order_type": kind,
        "order_type_label": dict(ORDER_TYPES)[kind],
        "items": [serialize_item(i, request) for i in order.items.all()],
        "tracking": {
            "courier": order.courier_name, "number": order.tracking_number, "url": order.tracking_url or None,
            "expected_delivery": order.expected_delivery.isoformat() if order.expected_delivery else None,
            "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
            "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
        },
        "cancellation": {
            "at": order.cancelled_at.isoformat(), "by": order.cancelled_by, "reason": order.cancel_reason,
            "refund_due": order.payment_status == "paid",
        } if order.status == "cancelled" and order.cancelled_at else None,
        "timeline": [{"status": e.status, "label": e.get_status_display(), "note": e.note, "at": e.created_at.isoformat()}
                     for e in order.events.all()],
        "requests": [{
            "id": r.pk, "kind": r.kind, "kind_label": r.get_kind_display(), "reason": r.get_reason_display(),
            "details": r.details, "preferred_size": r.preferred_size, "status": r.status, "status_label": r.get_status_display(),
            "items": [i.product_name for i in r.items.all()], "created_at": r.created_at.isoformat(),
        } for r in order.requests.all()],
        "links": {
            "admin": request.build_absolute_uri(reverse("admin:store_order_change", args=[order.pk])),
            "staff": request.build_absolute_uri(reverse("staff_order_update", args=[order.order_number])),
        },
    }


def _orders_queryset():
    return (Order.objects.select_related("customer_user", "customer_user__profile")
            .prefetch_related("items__product__images", "items__product__category", "events", "requests__items")
            .order_by("-created_at"))


@csrf_exempt
@require_http_methods(["GET"])
@api_token_required
def online_orders(request):
    from store.payments import release_unpaid_orders_soon

    release_unpaid_orders_soon()
    qs = _orders_queryset()
    status = request.GET.get("status")
    if status:
        valid = {s for s, _ in Order.STATUS_CHOICES}
        wanted = [s for s in status.split(",") if s in valid]
        qs = qs.filter(status__in=wanted) if wanted else qs.none()
    kind = request.GET.get("type")
    if kind == "ready_made":
        qs = qs.exclude(items__customization__isnull=False)
    elif kind == "made_to_measure":  # any custom piece, including mixed orders
        qs = qs.filter(items__customization__isnull=False).distinct()
    elif kind:
        return _error("Unknown type; use ready_made or made_to_measure.", 400)
    payment = request.GET.get("payment_status")
    if payment:
        qs = qs.filter(payment_status=payment)
    since = request.GET.get("since")
    if since:
        dt = parse_datetime(since)
        if dt is None:
            return _error("Invalid 'since' timestamp; use ISO 8601.", 400)
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt)
        qs = qs.filter(updated_at__gte=dt)
    q = (request.GET.get("q") or "").strip()
    if q:
        from django.db.models import Q

        qs = qs.filter(Q(order_number__icontains=q) | Q(customer_name__icontains=q)
                       | Q(customer_phone__icontains=q) | Q(customer_email__icontains=q))
    try:
        limit = min(max(int(request.GET.get("limit", 100)), 1), MAX_LIMIT)
    except ValueError:
        limit = 100
    site = SiteSettings.objects.first()
    orders = list(qs[:limit + 1])
    has_more = len(orders) > limit
    counts = _customer_order_counts(orders[:limit])
    return JsonResponse({
        "orders": [serialize_order(request, o, site, counts) for o in orders[:limit]],
        "has_more": has_more,
        "statuses": [{"value": v, "label": l} for v, l in Order.STATUS_CHOICES],
        "payment_statuses": [{"value": v, "label": l} for v, l in Order._meta.get_field("payment_status").choices],
        "order_types": [{"value": v, "label": l} for v, l in ORDER_TYPES],
        "request_statuses": [{"value": v, "label": l} for v, l in OrderRequest.STATUSES],
        "generated_at": timezone.now().isoformat(),
    })


@csrf_exempt
@require_http_methods(["GET", "POST"])
@api_token_required
def online_order_detail(request, order_number):
    order = _orders_queryset().filter(order_number__iexact=order_number).first()
    if order is None:
        return _error("Order not found.", 404)
    if request.method == "POST":
        try:
            payload = json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            return _error("Body must be JSON.", 400)
        changes = []
        status = payload.get("status")
        if status is not None:
            if status not in dict(Order.STATUS_CHOICES):
                return _error(f"Unknown status '{status}'.", 400)
            if status == "cancelled" and order.status != "cancelled":
                from store.orders import restock

                restock(order)  # ready-made stock goes back on the shelf
                order.cancelled_by = "staff"
                order.cancel_reason = str(payload.get("cancel_reason") or "")[:200]
                order._event_note = "Cancelled from the billing app"
            order.status = status
            changes.append("status")
        for key, field, size in (("courier", "courier_name", 80), ("tracking_number", "tracking_number", 80), ("tracking_url", "tracking_url", 500)):
            if key in payload:
                value = str(payload[key] or "").strip()[:size]
                if field == "tracking_url" and value and not value.startswith(("https://", "http://")):
                    return _error("Tracking link must start with https://", 400)
                setattr(order, field, value)
                changes.append(field)
        if "expected_delivery" in payload:
            from datetime import date

            raw = payload["expected_delivery"]
            try:
                order.expected_delivery = date.fromisoformat(raw) if raw else None
            except (TypeError, ValueError):
                return _error("expected_delivery must be YYYY-MM-DD.", 400)
            changes.append("expected_delivery")
        payment_status = payload.get("payment_status")
        if payment_status is not None:
            if payment_status not in dict(Order._meta.get_field("payment_status").choices):
                return _error(f"Unknown payment status '{payment_status}'.", 400)
            order.payment_status = payment_status
            if payment_status == "paid" and not order.paid_at:
                order.paid_at = timezone.now()
            changes.append("payment_status")
        if "payment_notes" in payload:
            order.payment_notes = str(payload["payment_notes"] or "")[:2000]
            changes.append("payment_notes")
        if not changes:
            return _error("Nothing to update.", 400)
        with transaction.atomic():
            order.save()
        order = _orders_queryset().get(pk=order.pk)
    return JsonResponse({"order": serialize_order(request, order, SiteSettings.objects.first())})


@csrf_exempt
@require_http_methods(["POST"])
@api_token_required
def online_order_request_update(request, order_number, request_id):
    """Billing app: move an exchange/alteration/problem request along and reply to the customer."""
    from store.models import OrderRequest

    order = _orders_queryset().filter(order_number__iexact=order_number).first()
    if order is None:
        return _error("Order not found.", 404)
    req = OrderRequest.objects.filter(order=order, pk=request_id).first()
    if req is None:
        return _error("Request not found.", 404)
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return _error("Body must be JSON.", 400)
    fields = []
    if "status" in payload:
        if payload["status"] not in dict(OrderRequest.STATUSES):
            return _error(f"Unknown request status '{payload['status']}'.", 400)
        req.status = payload["status"]
        fields.append("status")
    if "staff_note" in payload:
        req.staff_note = str(payload["staff_note"] or "")[:2000]
        fields.append("staff_note")
    if not fields:
        return _error("Nothing to update.", 400)
    req.save(update_fields=fields + ["updated_at"])
    order = _orders_queryset().get(pk=order.pk)
    return JsonResponse({"order": serialize_order(request, order, SiteSettings.objects.first())})
