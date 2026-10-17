"""Sign in with Google (Google Identity Services ID token, verified server-side).

The button (templates/store/partials/google_signin.html) hands the signed ID
token to ``google_signin`` in a normal CSRF-protected form POST. We verify the
token's signature, audience (GOOGLE_CLIENT_ID), issuer and expiry with
google-auth, then:
- a signed-in customer: link the Google account to them;
- a known Google account: sign that customer in;
- a verified email matching one customer account: link it and sign in
  (never auto-links staff accounts);
- otherwise: create a passwordless customer account.
"""
import logging
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from store.models import CustomerProfile
from store.views_phone import _safe_next

logger = logging.getLogger(__name__)
ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


class GoogleSignInError(Exception):
    pass


def verify_credential(credential):
    """Return the verified token claims, or raise GoogleSignInError."""
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
    if not client_id or not credential:
        raise GoogleSignInError("Google sign-in is not available.")
    try:
        claims = id_token.verify_oauth2_token(credential, google_requests.Request(), client_id, clock_skew_in_seconds=10)
    except Exception as exc:  # bad signature, expired, wrong audience, network
        logger.warning("Google ID token rejected: %s", exc)
        raise GoogleSignInError("Google sign-in did not complete. Please try again.") from exc
    if claims.get("iss") not in ISSUERS or not claims.get("sub"):
        raise GoogleSignInError("Google sign-in did not complete. Please try again.")
    return claims


def _unique_username(base):
    base = re.sub(r"[^\w.@+-]", "", base)[:120] or "customer"
    name, n = base, 1
    while User.objects.filter(username=name).exists():
        n += 1
        name = f"{base}{n}"
    return name


def user_for_google(claims, current_user=None):
    sub = claims["sub"]
    email = (claims.get("email") or "").strip()
    verified = bool(claims.get("email_verified")) and bool(email)
    owner = CustomerProfile.objects.select_related("user").filter(google_sub=sub).first()

    if current_user is not None and current_user.is_authenticated:
        if owner and owner.user_id != current_user.pk:
            raise GoogleSignInError("This Google account is already linked to another account.")
        profile, _ = CustomerProfile.objects.get_or_create(user=current_user)
        profile.google_sub = sub
        profile.save(update_fields=["google_sub"])
        if verified and not current_user.email:
            current_user.email = email
            current_user.save(update_fields=["email"])
        return current_user, False

    if owner:
        if not owner.user.is_active:
            raise GoogleSignInError("This account is disabled.")
        return owner.user, False

    if verified:
        matches = list(User.objects.filter(email__iexact=email, is_active=True)[:2])
        if len(matches) == 1 and not (matches[0].is_staff or matches[0].is_superuser):
            user = matches[0]
            profile, _ = CustomerProfile.objects.get_or_create(user=user)
            if profile.google_sub and profile.google_sub != sub:
                raise GoogleSignInError("This email is linked to a different Google account.")
            profile.google_sub = sub
            profile.save(update_fields=["google_sub"])
            return user, False
        if matches:
            raise GoogleSignInError("Please sign in with your password first, then connect Google from your account.")

    try:
        with transaction.atomic():
            user = User(
                username=_unique_username(email.split("@")[0] if email else f"google_{sub[-10:]}"),
                email=email if verified else "",
                first_name=(claims.get("given_name") or "")[:150],
                last_name=(claims.get("family_name") or "")[:150],
            )
            user.set_unusable_password()
            user.save()
            CustomerProfile.objects.create(user=user, google_sub=sub)
    except IntegrityError as exc:  # same Google account racing itself
        owner = CustomerProfile.objects.select_related("user").filter(google_sub=sub).first()
        if owner:
            return owner.user, False
        raise GoogleSignInError("Google sign-in did not complete. Please try again.") from exc
    return user, True


@require_POST
def google_signin(request):
    next_url = _safe_next(request, request.POST.get("next", ""))
    try:
        claims = verify_credential(request.POST.get("credential", ""))
        linking = request.user.is_authenticated
        user, created = user_for_google(claims, current_user=request.user)
    except GoogleSignInError as exc:
        messages.error(request, str(exc))
        return redirect(next_url or "account_login")
    if linking:
        messages.success(request, "Your Google account is connected.")
        return redirect(next_url or "account_profile")
    auth_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    if created:
        messages.success(request, "Welcome! Your account is ready.")
    else:
        messages.success(request, "You are signed in.")
    return redirect(next_url or "home")
