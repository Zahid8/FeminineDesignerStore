from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction

from store import measurements as mspec
from store.models import NewsletterSubscriber, Order, OrderItem, Product, SiteSettings

CART_SESSION_KEY = "femdes_cart"
CENT = Decimal("0.01")


def _q(value):
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def compute_totals(gross_subtotal, discount_total, site_settings=None):
    """Order money maths shared by the cart and order creation.

    subtotal (list prices) - discount (per-item sale prices) + shipping = total.
    Shipping is SiteSettings.shipping_fee unless the discounted merchandise
    value reaches free_shipping_threshold.
    """
    if site_settings is None:
        site_settings = SiteSettings.objects.first()
    gross_subtotal = _q(gross_subtotal)
    discount_total = _q(discount_total)
    merchandise = gross_subtotal - discount_total
    fee = getattr(site_settings, "shipping_fee", None) or Decimal("0.00")
    threshold = getattr(site_settings, "free_shipping_threshold", None)
    shipping = Decimal("0.00")
    remaining = None
    if fee > 0 and merchandise > 0:
        if threshold is not None and merchandise >= threshold:
            shipping = Decimal("0.00")
        else:
            shipping = _q(fee)
    if threshold is not None and threshold > 0:
        remaining = _q(max(threshold - merchandise, Decimal("0.00")))
    progress = None
    if threshold:
        progress = int(min(merchandise / threshold, Decimal("1")) * 100)
    return {
        "subtotal": gross_subtotal,
        "discount_total": discount_total,
        "shipping": shipping,
        "total": _q(merchandise + shipping),
        "free_shipping_threshold": threshold,
        "free_shipping_remaining": remaining,
        "free_shipping_progress": progress,
    }


def _cart_key(product_id, color="", size="", custom=None):
    """Stable key per product/variant (and measurement set) combination."""
    key = f"{product_id}_{color.strip().lower()}_{size.strip().lower()}"
    if custom:
        key += "_c" + mspec.fingerprint(custom)
    return key


def custom_fee_for(product, site_settings=None):
    if site_settings is None:
        site_settings = SiteSettings.objects.first()
    return product.custom_fee(site_settings)


def get_cart(request):
    return request.session.get(CART_SESSION_KEY, {})


def _save_cart(request, cart):
    request.session[CART_SESSION_KEY] = cart
    request.session.modified = True


def add_to_cart(request, product, quantity=1, color="", size="", custom=None):
    # Made-to-measure pieces are stitched to order: they skip stock checks
    # and do not consume stock (see create_order_from_cart).
    if not product.is_active:
        raise ValueError("Product is not active.")
    if not custom and product.stock_quantity <= 0:
        raise ValueError("Product is out of stock.")
    if quantity <= 0:
        raise ValueError("Quantity must be positive.")
    if custom and not product.allow_customization:
        raise ValueError("This piece is not available made to measure.")
    if custom:
        size = "Made to measure"

    cart = get_cart(request)
    key = _cart_key(product.pk, color, size, custom)
    current_qty = cart.get(key, {}).get("quantity", 0)
    new_qty = current_qty + quantity
    if not custom and new_qty > product.stock_quantity:
        raise ValueError("Requested quantity exceeds available stock.")

    cart[key] = {
        "product_id": product.pk,
        "product_name": product.name,
        "slug": product.slug,
        "color": color,
        "size": size,
        "quantity": new_qty,
        "custom": custom or None,
    }
    _save_cart(request, cart)


def update_cart_item(request, cart_key, quantity):
    cart = get_cart(request)
    if cart_key not in cart:
        return
    if quantity == 0:
        del cart[cart_key]
        _save_cart(request, cart)
        return

    item = cart[cart_key]
    try:
        product = Product.objects.get(pk=item["product_id"], is_active=True)
    except Product.DoesNotExist:
        del cart[cart_key]
        _save_cart(request, cart)
        return

    if not item.get("custom") and quantity > product.stock_quantity:
        raise ValueError("Requested quantity exceeds available stock.")
    if quantity <= 0:
        del cart[cart_key]
    else:
        item["quantity"] = quantity
    _save_cart(request, cart)


def remove_cart_item(request, cart_key):
    cart = get_cart(request)
    if cart_key in cart:
        del cart[cart_key]
        _save_cart(request, cart)


def get_cart_summary(request):
    cart = get_cart(request)
    lines = []
    item_count = 0
    gross = Decimal("0.00")
    discount = Decimal("0.00")
    site = SiteSettings.objects.first()

    for key, item in list(cart.items()):
        try:
            product = Product.objects.select_related("category").get(
                pk=item["product_id"], is_active=True
            )
        except Product.DoesNotExist:
            # Stale cart line; skip it.
            continue

        qty = item["quantity"]
        custom = item.get("custom") or None
        fee = product.custom_fee(site) if custom else Decimal("0.00")
        unit_price = _q(product.get_effective_price() + fee)
        line_total = _q(unit_price * qty)

        lines.append(
            {
                "key": key,
                "product": product,
                "product_id": product.pk,
                "product_name": product.name,
                "slug": product.slug,
                "color": item.get("color", ""),
                "size": item.get("size", ""),
                "quantity": qty,
                "unit_price": unit_price,
                "line_total": line_total,
                "custom": custom,
                "custom_summary": mspec.summary(custom),
                "custom_fee": fee,
                "lead_time": product.custom_lead_time(site) if custom else "",
            }
        )
        item_count += qty
        gross += (product.price + fee) * qty
        discount += (product.price - product.get_effective_price()) * qty

    summary = {"lines": lines, "item_count": item_count, "has_custom": any(line.get("custom") for line in lines)}
    summary.update(compute_totals(gross, discount))
    return summary


def create_order_from_cart(request, checkout_data):
    with transaction.atomic():
        cart = get_cart(request)
        if not cart:
            raise ValueError("Cart is empty.")

        # Validate all cart products exist and are active with sufficient stock.
        product_ids = [item["product_id"] for item in cart.values()]
        products = list(
            Product.objects.select_for_update()
            .filter(pk__in=product_ids)
            .select_related("category")
        )
        product_map = {p.pk: p for p in products}

        # Aggregate ready-made quantities per product across all cart lines
        # (made-to-measure lines are stitched to order and need no stock).
        aggregate_qty = {}
        for item in cart.values():
            pid = item["product_id"]
            ready = 0 if item.get("custom") else item["quantity"]
            aggregate_qty[pid] = aggregate_qty.get(pid, 0) + ready

        # Validate aggregate stock before creating order.
        for pid, aggr in aggregate_qty.items():
            product = product_map.get(pid)
            if product is None:
                raise ValueError(f"Product {pid} no longer exists.")
            if not product.is_active:
                raise ValueError(f"Product {product.name} is no longer available.")
            if aggr > product.stock_quantity:
                raise ValueError(
                    f"Insufficient stock for {product.name} "
                    f"(requested {aggr}, available {product.stock_quantity})."
                )

        gross_subtotal = Decimal("0.00")
        discount_total = Decimal("0.00")
        order_items_data = []
        site = SiteSettings.objects.first()
        last_custom = None

        for key, item in cart.items():
            product = product_map.get(item["product_id"])
            if product is None:
                raise ValueError(f"Product {item['product_id']} no longer exists.")

            qty = item["quantity"]
            custom = item.get("custom") or None
            fee = product.custom_fee(site) if custom else Decimal("0.00")
            if custom:
                last_custom = custom
            unit_price = product.price + fee
            effective_price = product.get_effective_price() + fee
            line_discount = (unit_price - effective_price) * qty
            line_total = effective_price * qty
            line_total = line_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            line_discount = line_discount.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            gross_subtotal += unit_price * qty
            discount_total += line_discount
            order_items_data.append(
                {
                    "product": product,
                    "product_name": product.name,
                    "sku": product.sku or "",
                    "unit_price": unit_price,
                    "discount_amount": line_discount,
                    "line_total": line_total,
                    "quantity": qty,
                    "color": item.get("color", ""),
                    "size": item.get("size", ""),
                    "customization": custom,
                }
            )

        totals = compute_totals(gross_subtotal, discount_total)
        payment_method = checkout_data.get("payment_method") or "manual_upi"

        order = Order.objects.create(
            customer_name=checkout_data["customer_name"],
            customer_email=checkout_data["customer_email"],
            customer_phone=checkout_data.get("customer_phone", ""),
            shipping_address=checkout_data["shipping_address"],
            notes=checkout_data.get("notes", ""),
            customer_user=(
                request.user if getattr(request, "user", None) and request.user.is_authenticated
                else None
            ),
            subtotal=totals["subtotal"],
            discount_total=totals["discount_total"],
            shipping_total=totals["shipping"],
            total=totals["total"],
            payment_method=payment_method,
        )

        for item_data in order_items_data:
            OrderItem.objects.create(
                order=order,
                product=item_data["product"],
                product_name=item_data["product_name"],
                sku=item_data["sku"],
                unit_price=item_data["unit_price"],
                discount_amount=item_data["discount_amount"],
                line_total=item_data["line_total"],
                quantity=item_data["quantity"],
                color=item_data["color"],
                size=item_data["size"],
                customization=item_data["customization"],
            )
            # Decrement stock for ready-made lines only.
            if not item_data["customization"]:
                item_data["product"].stock_quantity -= item_data["quantity"]
                item_data["product"].save(update_fields=["stock_quantity"])

        # Remember measurements for next time.
        user = getattr(request, "user", None)
        if last_custom and user is not None and user.is_authenticated:
            from store.models import CustomerProfile

            profile, _ = CustomerProfile.objects.get_or_create(user=user)
            profile.saved_measurements = last_custom.get("measurements")
            profile.save(update_fields=["saved_measurements"])

        # Clear cart.
        request.session[CART_SESSION_KEY] = {}
        request.session.modified = True
        return order


def subscribe_newsletter(email):
    sub, created = NewsletterSubscriber.objects.get_or_create(
        email=email,
        defaults={"is_active": True},
    )
    if not created and not sub.is_active:
        sub.is_active = True
        sub.save(update_fields=["is_active"])
    return sub


def payment_methods(site_settings=None):
    """Payment options offered at checkout, in display order."""
    from django.conf import settings

    if site_settings is None:
        site_settings = SiteSettings.objects.first()
    methods = []
    if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
        methods.append({"value": "razorpay", "label": "Pay online",
                        "help": "UPI, cards, net banking and wallets via Razorpay."})
    upi = getattr(site_settings, "upi_id", "") or "+919898989898"
    methods.append({"value": "manual_upi", "label": "UPI transfer",
                    "help": f"Pay to {upi} after placing the order and share the screenshot on WhatsApp."})
    if getattr(site_settings, "cod_enabled", False):
        methods.append({"value": "cash_on_delivery", "label": "Cash on delivery",
                        "help": "Pay in cash when your order arrives."})
    return methods


def send_order_emails(order, request=None):
    """Confirmation to the customer and a notification to the store inbox.

    Called after the order transaction has committed; failures are logged and
    never block the customer.
    """
    import logging

    from django.conf import settings
    from django.core.mail import send_mail
    from django.template.loader import render_to_string

    site = SiteSettings.objects.first()
    ctx = {"order": order, "site_settings": site,
           "order_url": request.build_absolute_uri(f"/orders/{order.order_number}/success/") if request else ""}
    store_name = getattr(site, "store_name", "FemDes")
    try:
        send_mail(
            f"{store_name}: order {order.order_number} received",
            render_to_string("store/emails/order_confirmation.txt", ctx),
            settings.DEFAULT_FROM_EMAIL,
            [order.customer_email],
        )
        if settings.STORE_NOTIFY_EMAIL:
            send_mail(
                f"New order {order.order_number} — {order.customer_name}",
                render_to_string("store/emails/order_notify_staff.txt", ctx),
                settings.DEFAULT_FROM_EMAIL,
                [settings.STORE_NOTIFY_EMAIL],
            )
    except Exception:
        logging.getLogger(__name__).exception("Order email failed for %s", order.order_number)
