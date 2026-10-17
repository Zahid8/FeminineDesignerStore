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
