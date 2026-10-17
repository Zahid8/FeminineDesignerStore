"""Customer order actions: cancel, exchange/alteration/problem request, buy again."""
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from store import orders as order_service
from store.models import OrderRequest
from store.payments import order_access_key
from store.views import _base_context, _viewable_order_or_404


def _back(request, order):
    """Account order page for the owner, otherwise the signed order page."""
    if request.user.is_authenticated and order.customer_user_id == request.user.pk:
        return reverse("account_order_detail", kwargs={"order_number": order.order_number})
    return reverse("order_success", kwargs={"order_number": order.order_number}) + f"?k={order_access_key(order.order_number)}"


def order_context(request, order):
    """Shared context for any page that shows an order to its customer."""
    from django.conf import settings

    from store.payments import can_pay_online

    key = order_access_key(order.order_number)
    pay_now = ""
    if can_pay_online(order) and settings.RAZORPAY_KEY_ID:
        pay_now = reverse("razorpay_payment", kwargs={"order_number": order.order_number}) + f"?k={key}"
    return {
        "order": order,
        "order_key": key,
        "steps": order_service.timeline(order),
        "can_cancel": order_service.can_cancel(order),
        "cancel_reasons": order_service.CANCEL_REASONS,
        "request_options": order_service.request_options(order),
        "order_requests": order.requests.prefetch_related("items"),
        "pay_now_url": pay_now,
    }


@require_POST
def order_cancel(request, order_number):
    order = _viewable_order_or_404(request, order_number)
    reasons = dict(order_service.CANCEL_REASONS)
    reason = request.POST.get("reason", "")
    if reason not in reasons:
        messages.error(request, "Please choose a reason for cancelling.")
        return redirect(_back(request, order))
    done = order_service.cancel_order(order.pk, reason=reasons[reason], by="customer")
    if done is None:
        messages.error(request, "This order can no longer be cancelled because it is already being prepared. Message us and we will help.")
    elif done.payment_status == "paid":
        messages.success(request, f"Order cancelled. Your refund of {done.total} will reach your original payment method in 5–7 working days.")
    else:
        messages.success(request, "Order cancelled.")
    return redirect(_back(request, order))


def order_request(request, order_number):
    order = _viewable_order_or_404(request, order_number)
    options = order_service.request_options(order)
    if not options:
        messages.info(request, "Exchanges and alterations open once your order is delivered, within the time allowed in our terms.")
        return redirect(_back(request, order))
    kinds = dict(OrderRequest.KINDS)
    kind = request.POST.get("kind") or request.GET.get("kind") or options[0][0]
    if kind not in dict(options):
        kind = options[0][0]
    error = ""
    if request.method == "POST":
        try:
            item_ids = [int(x) for x in request.POST.getlist("items") if x.isdigit()]
            order_service.create_request(order, kind, request.POST.get("reason", ""), item_ids,
                                         details=request.POST.get("details", "").strip(),
                                         preferred_size=request.POST.get("preferred_size", "").strip())
        except ValueError as exc:
            error = str(exc)
        else:
            messages.success(request, "Request received. We will reply within 24 hours on WhatsApp or email.")
            return redirect(_back(request, order))
    ctx = _base_context(request)
    ctx.update({
        "order": order,
        "order_key": order_access_key(order.order_number),
        "options": [(k, kinds[k], deadline) for k, deadline in options],
        "kind": kind,
        "items": order_service.eligible_items(order, kind),
        "reasons": OrderRequest.REASONS,
        "error": error,
        "back_url": _back(request, order),
        "posted": request.POST,
    })
    return render(request, "store/order_request.html", ctx)


@require_POST
def order_buy_again(request, order_number):
    order = _viewable_order_or_404(request, order_number)
    added, skipped = order_service.buy_again(request, order)
    if added:
        messages.success(request, f"Added {added} piece{'s' if added != 1 else ''} to your bag.")
    if skipped:
        messages.info(request, "Not available right now: " + ", ".join(skipped) + ".")
    return redirect("cart_detail" if added else _back(request, order))
