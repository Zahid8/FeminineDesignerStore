from django import template

register = template.Library()


@register.filter
def size_values(row, columns):
    """Measurement values of a SizeChartRow in column order."""
    return row.values(columns)
