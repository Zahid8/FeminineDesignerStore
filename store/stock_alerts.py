"""Back-in-stock email alerts.

Product.pre_save remembers the stored stock; post_save schedules emails
(after commit) to everyone waiting when stock goes from 0 to positive.
"""
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


def subscribe(product, email):
    """Create a pending alert; returns False if one already exists."""
    from store.models import StockAlert

    email = email.strip().lower()
    _, created = StockAlert.objects.get_or_create(product=product, email=email, notified_at=None)
    return created


def remember_stock(sender, instance, **kwargs):
    if instance.pk:
        old = sender.objects.filter(pk=instance.pk).values_list("stock_quantity", flat=True).first()
        instance._fd_old_stock = old
    else:
        instance._fd_old_stock = None


def notify_if_restocked(sender, instance, created, **kwargs):
    old = getattr(instance, "_fd_old_stock", None)
    if created or old is None or old > 0 or instance.stock_quantity <= 0 or not instance.is_active:
        return
    product_pk = instance.pk
    transaction.on_commit(lambda: send_restock_emails(product_pk))


def send_restock_emails(product_pk, base_url=""):
    from store.models import Product, SiteSettings, StockAlert

    product = Product.objects.filter(pk=product_pk).first()
    if product is None:
        return 0
    site = SiteSettings.objects.first()
    base_url = base_url or getattr(settings, "SITE_URL", "")
    sent = 0
    for alert in StockAlert.objects.filter(product=product, notified_at__isnull=True):
        body = render_to_string("store/emails/back_in_stock.txt", {
            "product": product, "site_settings": site,
            "product_url": f"{base_url}{product.get_absolute_url()}",
        })
        try:
            send_mail(f"Back in stock: {product.name}", body, settings.DEFAULT_FROM_EMAIL, [alert.email])
        except Exception:
            logger.exception("Back-in-stock email failed for %s", alert.email)
            continue
        alert.notified_at = timezone.now()
        alert.save(update_fields=["notified_at"])
        sent += 1
    return sent
