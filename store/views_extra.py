"""Customer features added in T30: wishlist, and related helpers."""
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from store import stock_alerts, wishlist
from store.models import Product
from store.views import _base_context


def _wants_json(request):
    return request.headers.get("X-Requested-With") == "fetch" or "application/json" in request.headers.get("Accept", "")


def _back(request, fallback="wishlist"):
    target = request.POST.get("next") or request.META.get("HTTP_REFERER", "")
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(target)
    return redirect(fallback)


def wishlist_toggle(request, product_id):
    if request.method != "POST":
        return redirect("wishlist")
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    saved = wishlist.toggle(request, product)
    if _wants_json(request):
        return JsonResponse({"saved": saved, "count": len(wishlist.product_ids(request))})
    messages.success(request, f"{product.name} {'saved to' if saved else 'removed from'} your wishlist.")
    return _back(request)


def wishlist_page(request):
    ctx = _base_context(request)
    ctx["products"] = wishlist.products(request)
    return render(request, "store/wishlist.html", ctx)


def stock_alert_subscribe(request, product_id):
    """Out-of-stock product page: email me when it is back."""
    from django import forms

    product = get_object_or_404(Product, pk=product_id, is_active=True)
    if request.method != "POST":
        return redirect(product.get_absolute_url())
    field = forms.EmailField()
    try:
        email = field.clean(request.POST.get("email", ""))
    except forms.ValidationError:
        messages.error(request, "Please enter a valid email address.")
        return redirect(product.get_absolute_url() + "#notify")
    if product.is_in_stock:
        messages.info(request, f"Good news — {product.name} is in stock now.")
    elif stock_alerts.subscribe(product, email):
        messages.success(request, f"We'll email {email} when {product.name} is back.")
    else:
        messages.info(request, "You're already on the list for this piece.")
    return redirect(product.get_absolute_url())
