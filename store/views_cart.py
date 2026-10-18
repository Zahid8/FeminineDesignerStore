"""Bag extras: coupons, save for later, move to wishlist."""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from store import coupons, services, wishlist
from store.models import Product

SAVED_KEY = "saved_for_later"


def _next(request, default="cart_detail"):
    target = request.POST.get("next", "")
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return target
    return default


@require_POST
def cart_coupon(request):
    if request.POST.get("action") == "remove":
        request.session.pop(coupons.SESSION_KEY, None)
        messages.info(request, "Coupon removed.")
        return redirect(_next(request))
    code = request.POST.get("code", "").strip().upper()
    summary = services.get_cart_summary(request)
    try:
        _, amount = coupons.check(code, summary["subtotal"] - summary["sale_discount"], request.user)
    except coupons.CouponError as exc:
        messages.error(request, str(exc))
    else:
        request.session[coupons.SESSION_KEY] = code
        messages.success(request, f"{code} applied — you save ₹{amount}.")
    return redirect(_next(request))


@require_POST
def cart_move_to_wishlist(request, cart_key):
    cart = services.get_cart(request)
    item = cart.get(cart_key)
    if item:
        product = get_object_or_404(Product, pk=item["product_id"])
        wishlist.add(request, product)
        services.remove_cart_item(request, cart_key)
        messages.success(request, f"{product.name} moved to your wishlist.")
    return redirect(_next(request))


@require_POST
def cart_save_for_later(request, cart_key):
    cart = services.get_cart(request)
    item = cart.get(cart_key)
    if item:
        saved = [s for s in request.session.get(SAVED_KEY, []) if s.get("key") != cart_key]
        saved.insert(0, {**item, "key": cart_key})
        request.session[SAVED_KEY] = saved[:30]
        services.remove_cart_item(request, cart_key)
        messages.success(request, f"{item.get('product_name', 'Item')} saved for later.")
    return redirect(_next(request))


def _pop_saved(request, key):
    saved = request.session.get(SAVED_KEY, [])
    item = next((s for s in saved if s.get("key") == key), None)
    request.session[SAVED_KEY] = [s for s in saved if s.get("key") != key]
    return item


@require_POST
def saved_move_to_bag(request, saved_key):
    item = _pop_saved(request, saved_key)
    if item:
        product = Product.objects.filter(pk=item["product_id"]).first()
        try:
            if product is None:
                raise ValueError("This piece is no longer available.")
            services.add_to_cart(request, product, quantity=item.get("quantity", 1), color=item.get("color", ""),
                                 size="" if item.get("custom") else item.get("size", ""), custom=item.get("custom"))
        except ValueError as exc:
            # Keep it saved so nothing is lost.
            request.session[SAVED_KEY] = [item] + request.session.get(SAVED_KEY, [])
            messages.error(request, str(exc))
        else:
            messages.success(request, f"{product.name} moved to your bag.")
    return redirect(_next(request))


@require_POST
def saved_remove(request, saved_key):
    item = _pop_saved(request, saved_key)
    if item:
        messages.info(request, f"{item.get('product_name', 'Item')} removed from saved items.")
    return redirect(_next(request))


def saved_items(request):
    """Saved-for-later lines with their current product (missing products dropped)."""
    saved = request.session.get(SAVED_KEY, [])
    products = {p.pk: p for p in Product.objects.filter(pk__in=[s["product_id"] for s in saved])}
    lines = []
    for s in saved:
        product = products.get(s["product_id"])
        if product is None:
            continue
        lines.append({**s, "product": product, "product_name": product.name, "slug": product.slug,
                      "unit_price": product.get_effective_price(), "in_stock": bool(s.get("custom")) or product.stock_quantity > 0,
                      "active": product.is_active})
    return lines
