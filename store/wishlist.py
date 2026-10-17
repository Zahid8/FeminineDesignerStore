"""Wishlist: DB rows for signed-in customers, a session list for guests.

Guest items are merged into the account on sign-in (see apps.StoreConfig.ready).
"""
from store.models import Product, WishlistItem

SESSION_KEY = "femdes_wishlist"


def _session_ids(request):
    return [int(pid) for pid in request.session.get(SESSION_KEY, [])]


def product_ids(request):
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        return set(WishlistItem.objects.filter(user=user).values_list("product_id", flat=True))
    return set(_session_ids(request))


def toggle(request, product):
    """Add or remove `product`; returns True if it is now saved."""
    user = request.user
    if user.is_authenticated:
        item = WishlistItem.objects.filter(user=user, product=product).first()
        if item:
            item.delete()
            return False
        WishlistItem.objects.create(user=user, product=product)
        return True
    ids = _session_ids(request)
    if product.pk in ids:
        ids.remove(product.pk)
        saved = False
    else:
        ids.insert(0, product.pk)
        saved = True
    request.session[SESSION_KEY] = ids[:100]
    request.session.modified = True
    return saved


def products(request):
    """Saved products that are still for sale, newest first."""
    from store import selectors

    ids = product_ids(request)
    if not ids:
        return []
    found = {p.pk: p for p in selectors.get_active_products().filter(pk__in=ids)}
    user = request.user
    if user.is_authenticated:
        order = list(WishlistItem.objects.filter(user=user).values_list("product_id", flat=True))
    else:
        order = _session_ids(request)
    return [found[pid] for pid in order if pid in found]


def merge_session_into_user(request, user):
    ids = _session_ids(request)
    if not ids:
        return
    existing = set(WishlistItem.objects.filter(user=user).values_list("product_id", flat=True))
    valid = set(Product.objects.filter(pk__in=ids).values_list("pk", flat=True))
    WishlistItem.objects.bulk_create(
        [WishlistItem(user=user, product_id=pid) for pid in ids if pid in valid and pid not in existing]
    )
    request.session[SESSION_KEY] = []
    request.session.modified = True
