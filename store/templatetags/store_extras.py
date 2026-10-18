from django import template

register = template.Library()


@register.filter
def size_values(row, columns):
    """Measurement values of a SizeChartRow in column order."""
    return row.values(columns)


@register.filter
def percent_off(product):
    """Whole-number percentage saved vs compare_at_price, or 0."""
    compare = getattr(product, "compare_at_price", None)
    price = getattr(product, "price", None)
    if not compare or not price or compare <= price:
        return 0
    return int((compare - price) * 100 / compare)


@register.filter
def custom_rows(customization):
    """[(label, value)] for an OrderItem.customization snapshot."""
    from store import measurements

    return measurements.summary(customization)


@register.filter
def wa_link(url, text):
    """WhatsApp link with a pre-filled message (wa.me / api.whatsapp.com URLs)."""
    from urllib.parse import quote

    if not url:
        return ""
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}text={quote(str(text))}"


@register.filter
def pct_off(mrp, price):
    """Whole-number percent saved going from ``mrp`` to ``price``."""
    from decimal import Decimal, ROUND_HALF_UP

    try:
        mrp, price = Decimal(str(mrp)), Decimal(str(price))
    except Exception:
        return 0
    if mrp <= 0 or price >= mrp:
        return 0
    return int(((mrp - price) / mrp * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
