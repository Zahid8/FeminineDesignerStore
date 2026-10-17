"""Restate pre-T30 order subtotals as list-price subtotals.

Before T30, checkout stored the already-discounted amount as `subtotal` and
`total == subtotal`, while order pages show Subtotal - Discount = Total. Such
legacy rows are exactly: discount_total > 0, shipping_total == 0 and
total == subtotal (impossible under the new formula). Their subtotal gains the
discount back; totals are unchanged.
"""
from django.db import migrations
from django.db.models import F


def forwards(apps, schema_editor):
    Order = apps.get_model("store", "Order")
    Order.objects.filter(
        discount_total__gt=0, shipping_total=0, total=F("subtotal")
    ).update(subtotal=F("subtotal") + F("discount_total"))


def backwards(apps, schema_editor):
    Order = apps.get_model("store", "Order")
    Order.objects.filter(
        discount_total__gt=0, shipping_total=0, total=F("subtotal") - F("discount_total")
    ).update(subtotal=F("subtotal") - F("discount_total"))


class Migration(migrations.Migration):
    dependencies = [("store", "0020_content_and_appointments")]
    operations = [migrations.RunPython(forwards, backwards)]
