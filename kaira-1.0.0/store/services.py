from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction

from store.models import NewsletterSubscriber, Order, OrderItem, Product

CART_SESSION_KEY = "femdes_cart"


def _cart_key(product_id, color="", size=""):
    """Stable key per product/variant combination."""
    return f"{product_id}_{color.strip().lower()}_{size.strip().lower()}"


def get_cart(request):
    return request.session.get(CART_SESSION_KEY, {})


def _save_cart(request, cart):
    request.session[CART_SESSION_KEY] = cart
    request.session.modified = True


def add_to_cart(request, product, quantity=1, color="", size=""):
    if not product.is_active:
        raise ValueError("Product is not active.")
    if product.stock_quantity <= 0:
        raise ValueError("Product is out of stock.")
    if quantity <= 0:
        raise ValueError("Quantity must be positive.")

    cart = get_cart(request)
    key = _cart_key(product.pk, color, size)
    current_qty = cart.get(key, {}).get("quantity", 0)
    new_qty = current_qty + quantity
    if new_qty > product.stock_quantity:
        raise ValueError("Requested quantity exceeds available stock.")

    cart[key] = {
        "product_id": product.pk,
        "product_name": product.name,
        "slug": product.slug,
        "color": color,
        "size": size,
        "quantity": new_qty,
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

    if quantity > product.stock_quantity:
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
    subtotal = Decimal("0.00")

    for key, item in list(cart.items()):
        try:
            product = Product.objects.select_related("category").get(
                pk=item["product_id"], is_active=True
            )
        except Product.DoesNotExist:
            # Stale cart line; skip it.
            continue

        qty = item["quantity"]
        unit_price = product.get_effective_price()
        line_total = unit_price * qty
        line_total = line_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

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
            }
        )
        item_count += qty
        subtotal += line_total

    subtotal = subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = subtotal  # Discounts applied per-item; overall discount total is 0 for now.
    # discount_total can be computed later if needed.
    discount_total = Decimal("0.00")

    return {
        "lines": lines,
        "item_count": item_count,
        "subtotal": subtotal,
        "discount_total": discount_total,
        "total": total,
    }


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

        # Aggregate quantities per product across all cart lines.
        aggregate_qty = {}
        for item in cart.values():
            pid = item["product_id"]
            aggregate_qty[pid] = aggregate_qty.get(pid, 0) + item["quantity"]

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

        subtotal = Decimal("0.00")
        discount_total = Decimal("0.00")
        order_items_data = []

        for key, item in cart.items():
            product = product_map.get(item["product_id"])
            if product is None:
                raise ValueError(f"Product {item['product_id']} no longer exists.")

            qty = item["quantity"]
            unit_price = product.price
            effective_price = product.get_effective_price()
            line_discount = (unit_price - effective_price) * qty
            line_total = effective_price * qty
            line_total = line_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            line_discount = line_discount.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            subtotal += line_total
            discount_total += line_discount
            order_items_data.append(
                {
                    "product": product,
                    "product_name": product.name,
                    "sku": product.sku,
                    "unit_price": unit_price,
                    "discount_amount": line_discount,
                    "line_total": line_total,
                    "quantity": qty,
                    "color": item.get("color", ""),
                    "size": item.get("size", ""),
                }
            )

        discount_total = discount_total.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        total = subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        order = Order.objects.create(
            customer_name=checkout_data["customer_name"],
            customer_email=checkout_data["customer_email"],
            customer_phone=checkout_data.get("customer_phone", ""),
            shipping_address=checkout_data["shipping_address"],
            notes=checkout_data.get("notes", ""),
            subtotal=subtotal,
            discount_total=discount_total,
            total=total,
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
            )
            # Decrement stock.
            item_data["product"].stock_quantity -= item_data["quantity"]
            item_data["product"].save(update_fields=["stock_quantity"])

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
