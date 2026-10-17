"""Customer features added in T30: wishlist, and related helpers."""
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from store import wishlist
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
