"""One-click admin handoff from the Feminine Designer billing app.

The billing app (behind its own staff login) builds a short-lived, single-use
token signed with the shared WEBSTORE_API_TOKEN and sends the manager to
``/admin/handoff/?t=<token>``. We verify it, sign the manager in as the
designated superuser and open the admin. No password is ever typed here.

Token: base64url(JSON{"u": username, "exp": unix_ts, "n": nonce, "next": path})
       + "." + base64url(HMAC-SHA256(key, payload))
key:   HMAC-SHA256(WEBSTORE_API_TOKEN, "feminine-designer/storefront-admin/v1")
"""
import base64
import hashlib
import hmac
import json
import time

from django.conf import settings
from django.contrib.auth import get_user_model, login as auth_login
from django.core.cache import cache
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache

CONTEXT = b"feminine-designer/storefront-admin/v1"
MAX_AGE = 300  # seconds a token stays valid


def _key(secret):
    return hmac.new(secret.encode(), CONTEXT, hashlib.sha256).digest()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def make_token(username, secret=None, next_path="/admin/", ttl=120, nonce=None, now=None):
    """Build a handoff token (used by tests; the billing app does the same in TypeScript)."""
    secret = secret if secret is not None else settings.WEBSTORE_API_TOKEN
    payload = {"u": username, "exp": int((now or time.time()) + ttl), "n": nonce or _b64(hashlib.sha256(str(time.time_ns()).encode()).digest()[:12]), "next": next_path}
    body = _b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    return body + "." + _b64(hmac.new(_key(secret), body.encode(), hashlib.sha256).digest())


def verify_token(token, secret=None):
    """Return the payload for a valid, unexpired, unused token; otherwise None."""
    secret = secret if secret is not None else getattr(settings, "WEBSTORE_API_TOKEN", "")
    if not secret or not token or "." not in token:
        return None
    body, sig = token.rsplit(".", 1)
    expected = _b64(hmac.new(_key(secret), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        payload = json.loads(_unb64(body))
    except (ValueError, UnicodeDecodeError):
        return None
    exp = int(payload.get("exp", 0))
    now = int(time.time())
    if exp < now or exp > now + MAX_AGE or not payload.get("u") or not payload.get("n"):
        return None
    # Single use: remember the nonce until the token would have expired anyway.
    if not cache.add(f"admin-handoff:{payload['n']}", 1, timeout=exp - now + 5):
        return None
    return payload


@never_cache
def admin_handoff(request):
    payload = verify_token(request.GET.get("t", ""))
    if payload is None:
        return HttpResponseForbidden("This sign-in link is invalid or has expired. Open the admin again from the billing app.")
    allowed = getattr(settings, "STOREFRONT_MANAGER_USERNAME", "manager")
    if payload["u"] != allowed:
        return HttpResponseForbidden("This sign-in link is not for a manager account.")
    User = get_user_model()
    user, created = User.objects.get_or_create(username=allowed, defaults={"is_staff": True, "is_superuser": True, "first_name": "Manager"})
    if created:
        user.set_unusable_password()
        user.save()
    elif not (user.is_staff and user.is_superuser and user.is_active):
        user.is_staff = user.is_superuser = user.is_active = True
        user.save(update_fields=["is_staff", "is_superuser", "is_active"])
    auth_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    next_path = payload.get("next") or "/admin/"
    if not url_has_allowed_host_and_scheme(next_path, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        next_path = "/admin/"
    return redirect(next_path)
