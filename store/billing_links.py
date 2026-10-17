"""Links into the Feminine Designer billing app.

The billing app signs public bill links as HMAC-SHA256(key, ORDER_NUMBER) where
key = HMAC-SHA256(BILL_LINK_SECRET, "feminine-designer/online-bill-link/v1"),
base64url, first 22 characters (see its src/lib/receipts/bill-link.ts). With
the same secret configured here, the shop can hand customers the very same PDF.
"""
import base64
import hashlib
import hmac
from urllib.parse import quote

from django.conf import settings

CONTEXT = b"feminine-designer/online-bill-link/v1"
SIGNATURE_LENGTH = 22


def online_bill_signature(order_number, secret=None):
    secret = secret if secret is not None else getattr(settings, "BILL_LINK_SECRET", "")
    if not secret or not order_number:
        return ""
    key = hmac.new(secret.encode(), CONTEXT, hashlib.sha256).digest()
    digest = hmac.new(key, order_number.upper().encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")[:SIGNATURE_LENGTH]


def online_bill_url(order_number):
    """Absolute URL of the billing app's PDF bill for this order, or '' when not configured."""
    base = (getattr(settings, "BILLING_APP_URL", "") or "").rstrip("/")
    signature = online_bill_signature(order_number)
    if not base or not signature:
        return ""
    return f"{base}/bill/online/{quote(order_number.upper())}/{signature}"
